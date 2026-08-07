"""Decision Intelligence 单测:排序 / 低置信拒绝 / 风险惩罚 / Replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.decision.engine import DecisionEngine
from maple_agent.decision.evaluator import DecisionEvaluator
from maple_agent.decision.models import DecisionContext, DecisionOption
from maple_agent.events import EventBus
from maple_agent.goal.models import Goal, GoalStatus, GoalType
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _goal() -> Goal:
    return Goal(
        goal_id="goal-quest-1",
        goal_type=GoalType.QUEST,
        title="新手教学",
        priority=10,
        status=GoalStatus.ACTIVE,
    )


def _options() -> list[DecisionOption]:
    return [
        DecisionOption(
            decision_id="d1",
            action="TALK",
            target="赫丽娜",
            confidence=0.9,
            risk=0.2,
            reason="与 NPC 对话推进任务",
        ),
        DecisionOption(
            decision_id="d2",
            action="COLLECT",
            target="树液",
            confidence=0.8,
            risk=0.3,
            reason="收集任务道具",
        ),
        DecisionOption(
            decision_id="d3",
            action="DEFEAT",
            target="绿水灵",
            confidence=0.7,
            risk=0.5,
            reason="击败任务怪物",
        ),
    ]


def test_option_ranking():
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=_options()),
        trace_id="trace-rank",
    )
    assert result.selected_option is not None
    assert result.selected_option.decision_id == "d1"
    assert [option.decision_id for option in result.alternatives] == [
        "d1",
        "d2",
        "d3",
    ]
    assert result.score >= 0
    assert result.trace_id == "trace-rank"


def test_low_confidence_rejection():
    options = [
        DecisionOption(
            decision_id="d1",
            action="TALK",
            target="x",
            confidence=0.9,
            risk=0.1,
        ),
        DecisionOption(
            decision_id="d2",
            action="DEFEAT",
            target="y",
            confidence=0.2,
            risk=0.1,
        ),
    ]
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=options),
        trace_id="trace-lowconf",
    )
    assert result.selected_option is not None
    assert result.selected_option.decision_id == "d1"
    assert [option.decision_id for option in result.rejected] == ["d2"]


def test_risk_penalty():
    low_risk = DecisionOption(
        decision_id="low",
        action="TALK",
        target="a",
        confidence=0.8,
        risk=0.1,
    )
    high_risk = DecisionOption(
        decision_id="high",
        action="TALK",
        target="b",
        confidence=0.8,
        risk=0.7,
    )
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=[low_risk, high_risk]),
        trace_id="trace-risk",
    )
    assert result.selected_option is not None
    assert result.selected_option.decision_id == "low"
    assert result.score > 0


def test_high_risk_rejection():
    risky = DecisionOption(
        decision_id="risky",
        action="DEFEAT",
        target="boss",
        confidence=0.9,
        risk=0.95,
    )
    safe = DecisionOption(
        decision_id="safe",
        action="OBSERVE",
        target="window",
        confidence=0.8,
        risk=0.1,
    )
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=[risky, safe]),
        trace_id="trace-highrisk",
    )
    assert result.selected_option.decision_id == "safe"
    assert [option.decision_id for option in result.rejected] == ["risky"]


def test_invalid_action_rejected():
    invalid = DecisionOption(
        decision_id="bad",
        action="ATTACK",
        target="x",
        confidence=0.9,
        risk=0.1,
    )
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=[invalid]),
        trace_id="trace-invalid",
    )
    assert result.selected_option is None
    assert [option.decision_id for option in result.rejected] == ["bad"]
    assert "非法 action" in result.explanation


def test_evaluator_compare_and_explain():
    evaluator = DecisionEvaluator()
    d1, d2 = _options()[:2]
    comparison = evaluator.compare(d1, d2, scores={"d1": 0.8, "d2": 0.6})
    assert comparison.better_option_id == "d1"
    engine = DecisionEngine(evaluator=evaluator)
    result = engine.decide(
        DecisionContext(goal=_goal(), options=_options()),
        trace_id="trace-compare",
    )
    assert "新手教学" in result.explanation
    assert "d1" in result.explanation


def test_empty_context_no_crash():
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(options=[]),
        trace_id="trace-empty",
    )
    assert result.selected_option is None
    assert result.alternatives == []
    assert result.explanation


def test_replay_generation(tmp_path):
    engine = DecisionEngine(sessions_dir=tmp_path)
    result = engine.decide(
        DecisionContext(goal=_goal(), options=_options()),
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "decision_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["trace_id"] == "trace-replay"
    assert replay["goal"]["goal_id"] == "goal-quest-1"
    assert replay["selected"]["decision_id"] == "d1"
    assert len(replay["candidate_decisions"]) == 3
    assert replay["candidate_decisions"][0]["option"]["decision_id"] == "d1"
    assert replay["selected_score"] == result.score
    assert "selected_reason" in replay


def test_webui_decision_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    engine = DecisionEngine()
    result = engine.decide(
        DecisionContext(goal=_goal(), options=_options()),
        trace_id="trace-webui",
    )
    decision = {
        "goal": _goal().model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, decision=decision)
    with TestClient(app) as client:
        resp = client.get("/api/decision/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal"]["goal_id"] == "goal-quest-1"
    assert data["result"]["selected_option"]["decision_id"] == "d1"
    assert data["result"]["explanation"]


def test_webui_decision_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/decision/state")
    assert resp.json()["enabled"] is False
