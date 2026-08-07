"""Action Plan 单测:决策展开 / 校验 / 阻断 / Replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.action_plan.models import ActionPlanStatus
from maple_agent.action_plan.planner import ActionPlanner
from maple_agent.context.models import KnowledgeState, MatchedEntity
from maple_agent.decision.models import DecisionOption, DecisionResult
from maple_agent.events import EventBus
from maple_agent.fusion.models import WorldState
from maple_agent.knowledge.models import MapInfo
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _world_state() -> WorldState:
    return WorldState(
        current_map=MapInfo(map_id=1, name="射手村"),
        confidence=0.875,
    )


def _knowledge_state() -> KnowledgeState:
    return KnowledgeState(
        matched_entities=[
            MatchedEntity(
                entity_type="map",
                entity_id=1,
                name="射手村",
                confidence=0.875,
            )
        ],
        confidence=0.875,
        source="knowledge_graph",
        selection_reason="best=射手村",
    )


def _decision(confidence: float = 0.9) -> DecisionResult:
    return DecisionResult(
        selected_option=DecisionOption(
            decision_id="d1",
            action="TALK",
            target="赫丽娜",
            expected_result="任务已接受(语义)",
            confidence=confidence,
            risk=0.2,
            reason="与 NPC 对话",
        ),
        alternatives=[],
        score=0.46,
        trace_id="trace-action",
    )


def test_decision_expansion():
    planner = ActionPlanner()
    plan = planner.plan(
        _decision(),
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        goal_id="goal-quest-1",
        trace_id="trace-expand",
    )
    assert plan.action == "TALK"
    assert plan.target == "赫丽娜"
    assert plan.decision_id == "d1"
    assert plan.goal_id == "goal-quest-1"
    assert len(plan.steps) == 3
    assert plan.steps[0].step_id.startswith(plan.plan_id)
    assert all(step.description for step in plan.steps)
    assert all(step.required_observation for step in plan.steps)
    assert all(step.success_condition for step in plan.steps)
    assert plan.status is ActionPlanStatus.READY
    assert plan.prerequisites
    assert plan.validation_conditions


def test_validation_ready():
    planner = ActionPlanner()
    plan = planner.plan(
        _decision(),
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-ok",
    )
    assert plan.status is ActionPlanStatus.READY
    assert planner.last_validation is not None
    assert planner.last_validation.valid is True
    assert planner.last_validation.errors == []


def test_missing_target_blocked():
    selected = _decision().selected_option
    assert selected is not None
    decision = _decision().model_copy(
        update={
            "selected_option": selected.model_copy(update={"target": ""})
        }
    )
    planner = ActionPlanner()
    plan = planner.plan(
        decision,
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-notarget",
    )
    assert plan.status is ActionPlanStatus.BLOCKED
    assert planner.last_validation is not None
    assert "缺少 target" in planner.last_validation.errors


def test_unknown_action_blocked():
    selected = _decision().selected_option
    assert selected is not None
    decision = _decision().model_copy(
        update={
            "selected_option": selected.model_copy(
                update={"action": "ATTACK"}
            )
        }
    )
    planner = ActionPlanner()
    plan = planner.plan(
        decision,
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-unknown",
    )
    assert plan.status is ActionPlanStatus.BLOCKED
    assert planner.last_validation is not None
    assert any("未知 action" in error for error in planner.last_validation.errors)


def test_impossible_prerequisite_blocked():
    planner = ActionPlanner()
    plan = planner.plan(
        _decision(),
        world_state=None,
        knowledge_state=None,
        trace_id="trace-nostate",
    )
    assert plan.status is ActionPlanStatus.BLOCKED
    assert planner.last_validation is not None
    assert any(
        "前置条件不可满足" in error
        for error in planner.last_validation.errors
    )
    assert any(
        prerequisite.startswith("缺失:")
        for prerequisite in plan.prerequisites
    )


def test_low_confidence_blocked():
    planner = ActionPlanner()
    plan = planner.plan(
        _decision(confidence=0.2),
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-lowconf",
    )
    assert plan.status is ActionPlanStatus.BLOCKED
    assert planner.last_validation is not None
    assert any(
        "置信度过低" in error for error in planner.last_validation.errors
    )


def test_no_selected_option_blocked():
    decision = DecisionResult(
        selected_option=None,
        alternatives=[],
        score=0.0,
        trace_id="trace-none",
    )
    planner = ActionPlanner()
    plan = planner.plan(
        decision,
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-none",
    )
    assert plan.status is ActionPlanStatus.BLOCKED
    assert planner.last_validation is not None
    assert "action 为空" in planner.last_validation.errors


def test_replay_generation(tmp_path):
    planner = ActionPlanner(sessions_dir=tmp_path)
    planner.plan(
        _decision(),
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        goal_id="goal-quest-1",
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "action_plan_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["decision_input"]["selected_option"]["decision_id"] == "d1"
    assert len(replay["generated_steps"]) == 3
    assert replay["validation_result"]["valid"] is True
    assert replay["plan"]["status"] == "READY"
    assert replay["plan"]["action"] == "TALK"
    assert "goal-quest-1" in replay["plan"]["goal_id"]


def test_webui_action_plan_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    planner = ActionPlanner()
    plan = planner.plan(
        _decision(),
        world_state=_world_state(),
        knowledge_state=_knowledge_state(),
        trace_id="trace-webui",
    )
    action_plan_data = {"plan": plan.model_dump(mode="json")}
    app = create_app(
        runtime=runtime,
        bus=bus,
        action_plan=action_plan_data,
    )
    with TestClient(app) as client:
        resp = client.get("/api/action-plan/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["plan"]["action"] == "TALK"
    assert data["plan"]["status"] == "READY"
    assert len(data["plan"]["steps"]) == 3


def test_webui_action_plan_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/action-plan/state")
    assert resp.json()["enabled"] is False
