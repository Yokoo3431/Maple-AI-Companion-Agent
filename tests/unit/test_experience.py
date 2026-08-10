"""Experience 单测:经验库查询 / 检索 / 评估 / 决策加分 / Replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.decision.engine import DecisionEngine
from maple_agent.decision.models import DecisionContext, DecisionOption
from maple_agent.events import EventBus
from maple_agent.experience import (
    ExperienceEvaluator,
    ExperienceRecord,
    ExperienceRetriever,
    ExperienceStore,
)
from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal, GoalStatus, GoalType
from maple_agent.knowledge.models import MapInfo
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _record(
    experience_id: str,
    *,
    action: str,
    success: bool,
    failure_type: str = "",
    map_name: str = "射手村",
) -> ExperienceRecord:
    return ExperienceRecord(
        experience_id=experience_id,
        context_snapshot={"map_name": map_name},
        goal="新手教学",
        action=action,
        result="mock result",
        reflection="mock reflection",
        success=success,
        failure_type=failure_type,
        resolution="mock resolution",
    )


def _world() -> WorldState:
    return WorldState(
        current_map=MapInfo(map_id=1, name="射手村"),
        confidence=0.875,
    )


def _goal() -> Goal:
    return Goal(
        goal_id="goal-1",
        goal_type=GoalType.QUEST,
        title="新手教学",
        priority=10,
        status=GoalStatus.ACTIVE,
    )


def _option(action: str = "TALK") -> DecisionOption:
    return DecisionOption(
        decision_id="d1",
        action=action,
        target="赫丽娜",
        confidence=0.9,
        risk=0.2,
        reason="test",
    )


def _store() -> ExperienceStore:
    return ExperienceStore(
        [
            _record("e1", action="TALK", success=True),
            _record("e2", action="DEFEAT", success=False, failure_type="EXECUTION_FAILED"),
            _record("e3", action="TALK", success=True, map_name="魔法密林"),
            _record("e4", action="COLLECT", success=True),
        ]
    )


def test_store_similar_situation():
    store = _store()
    results = store.similar_situation(map_name="射手村")
    ids = {record.experience_id for record in results}
    assert "e1" in ids
    assert "e2" in ids
    assert "e3" not in ids  # 魔法密林,不匹配
    assert "e4" in ids


def test_store_similar_failure():
    store = _store()
    results = store.similar_failure(failure_type="EXECUTION_FAILED")
    assert len(results) == 1
    assert results[0].experience_id == "e2"
    assert results[0].success is False


def test_store_successful_recovery():
    store = _store()
    results = store.successful_recovery(action="TALK")
    assert len(results) == 2
    assert all(record.success for record in results)
    assert all(record.action == "TALK" for record in results)


def test_retriever_returns_historical_experiences():
    retriever = ExperienceRetriever(store=_store())
    results = retriever.retrieve(
        world_state=_world(),
        knowledge_state=None,
        goal=_goal(),
    )
    assert results
    assert all(
        record.context_snapshot.get("map_name") == "射手村"
        for record in results
    )
    assert retriever.last_query["map_name"] == "射手村"
    assert retriever.last_query["goal"] == "新手教学"


def test_evaluator_scores():
    evaluator = ExperienceEvaluator()
    score = evaluator.evaluate(
        _record("e1", action="TALK", success=True),
        map_name="射手村",
        goal="新手教学",
        action="TALK",
    )
    assert score.score == 1.0
    assert "地图匹配" in score.reason
    assert "动作匹配" in score.reason
    assert "成功经验" in score.reason


def test_decision_experience_bonus():
    context = DecisionContext(goal=_goal(), options=[_option("TALK")])
    plain = DecisionEngine().decide(context, trace_id="trace-plain")
    retriever = ExperienceRetriever(
        store=ExperienceStore([_record("e1", action="TALK", success=True)])
    )
    boosted = DecisionEngine(experience=retriever).decide(
        context,
        trace_id="trace-boost",
    )
    assert boosted.score > plain.score
    assert boosted.selected_option is not None
    assert boosted.selected_option.decision_id == "d1"


def test_failure_experience_penalizes():
    context = DecisionContext(goal=_goal(), options=[_option("TALK")])
    plain = DecisionEngine().decide(context, trace_id="trace-plain")
    retriever = ExperienceRetriever(
        store=ExperienceStore(
            [_record("e1", action="TALK", success=False, failure_type="EXECUTION_FAILED")]
        )
    )
    penalized = DecisionEngine(experience=retriever).decide(
        context,
        trace_id="trace-penalty",
    )
    assert penalized.score == plain.score  # 只有失败经验,bonus 为 0,不额外加分


def test_no_experience_replay_none():
    engine = DecisionEngine()
    assert engine._experience_replay() is None


def test_replay_with_experience(tmp_path):
    retriever = ExperienceRetriever(
        store=ExperienceStore([_record("e1", action="TALK", success=True)])
    )
    engine = DecisionEngine(experience=retriever, sessions_dir=tmp_path)
    engine.decide(
        DecisionContext(goal=_goal(), options=[_option("TALK")]),
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "decision_trace.json").read_text(
            encoding="utf-8"
        )
    )
    experience = replay["experience"]
    assert experience is not None
    assert experience["query"]["goal"] == "新手教学"
    assert experience["retrieved"]
    assert experience["retrieved"][0]["action"] == "TALK"
    assert experience["retrieved"][0]["success"] is True


def test_webui_experience_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    store = _store()
    retriever = ExperienceRetriever(store=store)
    retriever.retrieve(world_state=_world(), goal=_goal())
    payload = {
        "total": store.count(),
        "success_count": len(store.successful_recovery()),
        "failure_count": len(store.similar_failure()),
        "last_query": retriever.last_query,
        "last_results": [
            {
                "experience_id": record.experience_id,
                "action": record.action,
                "success": record.success,
            }
            for record in retriever.last_results
        ],
    }
    app = create_app(runtime=runtime, bus=bus, experience=payload)
    with TestClient(app) as client:
        resp = client.get("/api/experience/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["total"] == 4
    assert data["success_count"] == 3
    assert data["last_query"]["map_name"] == "射手村"
    assert data["last_results"]


def test_webui_experience_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/experience/state")
    assert resp.json()["enabled"] is False
