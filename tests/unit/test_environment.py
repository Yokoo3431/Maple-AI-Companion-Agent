"""Environment State 单测:创建 / 实体解析 / 快照 / 校验 / replay / context / WebUI。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.environment import (
    EnvironmentCollector,
    EnvironmentSnapshotManager,
    EnvironmentState,
    EnvironmentValidator,
    EnvironmentVerdict,
    save_environment_trace,
)
from maple_agent.events import EventBus
from maple_agent.observation.models import ObservationState
from maple_agent.providers import MockKnowledgeProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _observation(
    *,
    map_name: str = "射手村",
    entities: list[str] | None = None,
    confidence: float = 0.95,
    observations: list[str] | None = None,
) -> ObservationState:
    return ObservationState(
        map_name=map_name,
        visible_entities=entities or ["赫丽娜", "绿水灵"],
        confidence=confidence,
        observations=observations or ["射手村"],
    )


def _knowledge() -> MockKnowledgeProvider:
    provider = MockKnowledgeProvider()
    provider.initialize()
    provider.load_dataset()
    return provider


def test_state_creation():
    state = EnvironmentState(
        environment_id="env-1",
        location="射手村",
        visible_entities=["赫丽娜"],
        confidence=0.9,
    )
    assert state.environment_id == "env-1"
    assert state.location == "射手村"
    assert state.visible_entities == ["赫丽娜"]
    assert state.confidence == 0.9
    assert state.timestamp


def test_collector_entity_parsing():
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(
        observation_state=_observation(),
    )
    assert state.location == "射手村"
    assert "赫丽娜" in state.visible_entities
    assert state.conditions["entity_count"] == 2
    assert "射手村" in state.world_context
    assert state.confidence == 0.95
    assert collector.last_state is state


def test_collector_resources():
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(
        observation_state=_observation(
            observations=["射手村", "发现树液"],
        ),
    )
    assert "树液" in state.resources


def test_snapshot_changes():
    snapshot_manager = EnvironmentSnapshotManager()
    before = EnvironmentState(
        environment_id="env-before",
        location="射手村",
        visible_entities=["赫丽娜"],
        confidence=0.9,
    )
    after = EnvironmentState(
        environment_id="env-after",
        location="魔法密林",
        visible_entities=["赫丽娜", "爱丽丝"],
        confidence=0.8,
    )
    snapshot = snapshot_manager.capture(
        before=before,
        after=after,
        trace_id="trace-snap",
    )
    assert snapshot.trace_id == "trace-snap"
    assert any("location" in change for change in snapshot.changes)
    assert any("实体新增" in change for change in snapshot.changes)
    assert snapshot.before_state is before
    assert snapshot.after_state is after


def test_validation_valid():
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(observation_state=_observation())
    result = EnvironmentValidator().validate(state)
    assert result.verdict is EnvironmentVerdict.VALID
    assert result.issues == []


def test_validation_empty_blocked():
    state = EnvironmentState(
        environment_id="env-empty",
        location="",
        visible_entities=[],
    )
    result = EnvironmentValidator().validate(state)
    assert result.verdict is EnvironmentVerdict.BLOCKED
    assert any("空环境" in issue for issue in result.issues)


def test_validation_time_anomaly():
    state = EnvironmentState(
        environment_id="env-future",
        location="射手村",
        visible_entities=["赫丽娜"],
        timestamp=datetime.now(UTC) + timedelta(hours=2),
    )
    result = EnvironmentValidator().validate(state)
    assert result.verdict is EnvironmentVerdict.BLOCKED
    assert any("时间异常" in issue for issue in result.issues)


def test_validation_low_confidence_warning():
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(
        observation_state=_observation(confidence=0.3),
    )
    result = EnvironmentValidator().validate(state)
    assert result.verdict is EnvironmentVerdict.WARNING
    assert any("低置信" in issue for issue in result.issues)


def test_replay_generation(tmp_path):
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(
        observation_state=_observation(),
    )
    snapshot = EnvironmentSnapshotManager().capture(
        before=None,
        after=state,
        trace_id="trace-replay",
    )
    validation = EnvironmentValidator().validate(state)
    save_environment_trace(
        tmp_path,
        "trace-replay",
        environment_state=state,
        snapshot=snapshot,
        validation=validation,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "environment_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["environment_state"]["location"] == "射手村"
    assert replay["snapshot"]["changes"] == ["首次环境观察"]
    assert replay["validation"] == "VALID"


def test_context_integration():
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(observation_state=_observation())
    snapshot = EnvironmentSnapshotManager().capture(
        before=None,
        after=state,
        trace_id="trace-context",
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        environment_state=state,
        environment_snapshot=snapshot,
    )
    assert context.environment_state is not None
    assert context.environment_state.location == "射手村"
    assert context.environment_snapshot is not None
    assert context.environment_snapshot.changes


def test_webui_environment_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    collector = EnvironmentCollector(knowledge=_knowledge())
    state = collector.collect(observation_state=_observation())
    snapshot = EnvironmentSnapshotManager().capture(
        before=None,
        after=state,
        trace_id="trace-webui",
    )
    validation = EnvironmentValidator().validate(state)
    payload = {
        "state": state.model_dump(mode="json"),
        "snapshot": snapshot.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, environment=payload)
    with TestClient(app) as client:
        resp = client.get("/api/environment/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["state"]["location"] == "射手村"
    assert data["validation"]["verdict"] == "VALID"


def test_webui_environment_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/environment/state")
    assert resp.json()["enabled"] is False
