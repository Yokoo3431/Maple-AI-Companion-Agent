"""Dynamic World Model 单测:历史 / 转换 / 事件 / 预测 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.environment.models import EnvironmentState
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app
from maple_agent.world_model import (
    EnvironmentEventDetector,
    EnvironmentHistoryManager,
    EnvironmentTransitionDetector,
    WorldEventType,
    WorldStatePredictor,
    save_world_model_trace,
)


def _state(
    *,
    environment_id: str = "env-1",
    location: str = "射手村",
    entities: list[str] | None = None,
    resources: list[str] | None = None,
    confidence: float = 0.9,
    conditions: dict | None = None,
) -> EnvironmentState:
    return EnvironmentState(
        environment_id=environment_id,
        location=location,
        visible_entities=entities or ["赫丽娜"],
        resources=resources or [],
        conditions=conditions
        or {
            "observed_count": 1,
            "entity_count": len(entities or ["赫丽娜"]),
            "confidence": confidence,
        },
        world_context=f"当前位于 {location}",
        confidence=confidence,
    )


def test_history():
    manager = EnvironmentHistoryManager(history_id="hist-1")
    manager.append(_state(environment_id="env-1"))
    manager.append(
        _state(environment_id="env-2", location="魔法密林")
    )
    manager.add_event(
        EnvironmentEventDetector().detect(
            transition=EnvironmentTransitionDetector().detect(
                before=manager.history.snapshots[0],
                after=manager.history.snapshots[1],
            )
        )[0]
    )
    assert manager.history.history_id == "hist-1"
    assert len(manager.history.snapshots) == 2
    assert len(manager.history.timeline) == 1
    assert manager.last_state().location == "魔法密林"
    assert manager.previous_state().location == "射手村"


def test_transition_location():
    detector = EnvironmentTransitionDetector()
    transition = detector.detect(
        before=_state(location="射手村"),
        after=_state(location="魔法密林"),
    )
    assert transition.transition_type == "location"
    assert any("location" in change for change in transition.changes)
    assert transition.confidence == 0.9


def test_transition_entity():
    detector = EnvironmentTransitionDetector()
    transition = detector.detect(
        before=_state(entities=["赫丽娜"]),
        after=_state(entities=["赫丽娜", "爱丽丝"]),
    )
    assert transition.transition_type == "entity"
    assert any("实体新增" in change for change in transition.changes)


def test_event_detection():
    detector = EnvironmentEventDetector()
    transition = EnvironmentTransitionDetector().detect(
        before=_state(
            location="射手村",
            entities=["赫丽娜"],
            resources=[],
            conditions={"a": 1},
        ),
        after=_state(
            location="魔法密林",
            entities=["爱丽丝"],
            resources=["树液"],
            conditions={"a": 2},
        ),
    )
    events = detector.detect(transition=transition)
    event_types = {event.event_type for event in events}
    assert WorldEventType.ENTITY_APPEARED in event_types
    assert WorldEventType.ENTITY_DISAPPEARED in event_types
    assert WorldEventType.LOCATION_CHANGED in event_types
    assert WorldEventType.RESOURCE_CHANGED in event_types
    assert WorldEventType.CONDITION_CHANGED in event_types


def test_prediction():
    manager = EnvironmentHistoryManager()
    manager.append(_state(location="射手村", entities=["赫丽娜"]))
    manager.append(
        _state(location="魔法密林", entities=["爱丽丝"], resources=["树液"])
    )
    prediction = WorldStatePredictor().predict(
        history=manager.history,
    )
    assert prediction.predicted_location == "魔法密林"
    assert "赫丽娜" in prediction.predicted_entities
    assert "爱丽丝" in prediction.predicted_entities
    assert "树液" in prediction.predicted_resources
    assert prediction.confidence == 0.9
    assert prediction.summary


def test_prediction_pattern():
    manager = EnvironmentHistoryManager()
    for location in ("射手村", "魔法密林", "射手村"):
        manager.append(_state(location=location))
    prediction = WorldStatePredictor().predict(
        history=manager.history,
    )
    assert prediction.predicted_location == "魔法密林"
    assert prediction.reasoning


def test_replay_generation(tmp_path):
    manager = EnvironmentHistoryManager()
    before = _state(location="射手村", entities=["赫丽娜"])
    after = _state(
        location="魔法密林",
        entities=["爱丽丝"],
        resources=["树液"],
    )
    manager.append(before)
    manager.append(after)
    transition = EnvironmentTransitionDetector().detect(
        before=before,
        after=after,
    )
    events = EnvironmentEventDetector().detect(transition=transition)
    for event in events:
        manager.add_event(event)
    prediction = WorldStatePredictor().predict(history=manager.history)
    save_world_model_trace(
        tmp_path,
        "trace-replay",
        history=manager.history,
        transition=transition,
        events=events,
        prediction=prediction,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "world_model_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert len(replay["history"]["snapshots"]) == 2
    assert replay["transition"]["transition_type"] == "location"
    assert len(replay["events"]) >= 3
    assert replay["prediction"]["predicted_location"] == "魔法密林"


def test_context_integration():
    manager = EnvironmentHistoryManager()
    before = _state(location="射手村")
    after = _state(location="魔法密林")
    manager.append(before)
    manager.append(after)
    transition = EnvironmentTransitionDetector().detect(
        before=before,
        after=after,
    )
    prediction = WorldStatePredictor().predict(history=manager.history)
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        environment_history=manager.history,
        world_transition=transition,
        environment_prediction=prediction,
    )
    assert context.environment_history is not None
    assert len(context.environment_history.snapshots) == 2
    assert context.world_transition is not None
    assert context.world_transition.transition_type == "location"
    assert context.environment_prediction is not None
    assert context.environment_prediction.summary


def test_webui_world_model_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    manager = EnvironmentHistoryManager()
    before = _state(location="射手村")
    after = _state(location="魔法密林")
    manager.append(before)
    manager.append(after)
    transition = EnvironmentTransitionDetector().detect(
        before=before,
        after=after,
    )
    events = EnvironmentEventDetector().detect(transition=transition)
    prediction = WorldStatePredictor().predict(history=manager.history)
    payload = {
        "history_count": len(manager.history.snapshots),
        "events": [
            event.model_dump(mode="json") for event in events
        ],
        "transition": transition.model_dump(mode="json"),
        "prediction": prediction.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, world_model=payload)
    with TestClient(app) as client:
        resp = client.get("/api/world-model/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["history_count"] == 2
    assert data["events"]
    assert data["transition"]["transition_type"] == "location"
    assert data["prediction"]["predicted_location"] == "魔法密林"


def test_webui_world_model_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/world-model/state")
    assert resp.json()["enabled"] is False
