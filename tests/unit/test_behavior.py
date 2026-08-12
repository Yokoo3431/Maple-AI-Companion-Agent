"""Behavior 单测:目标映射/行为生成/序列排序/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.behavior import (
    BehaviorPlanner,
    BehaviorReference,
    BehaviorStep,
    BehaviorStepType,
    BehaviorValidator,
    BehaviorVerdict,
    GoalMapper,
    save_behavior_trace,
)
from maple_agent.events import EventBus
from maple_agent.navigation.models import (
    NavigationReference,
    RouteStep,
    RouteStepType,
)
from maple_agent.quest_reasoning.models import (
    GoalReference,
    GoalType,
    QuestGoalReference,
)
from maple_agent.reflex.models import (
    DangerEventReference,
    DangerEventType,
    ReflexReference,
    ReflexStateType,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _quest_goal(
    goal_type: GoalType = GoalType.NPC_INTERACTION_REFERENCE,
    description: str = "与赫丽娜交互",
    related: str = "新手任务",
) -> QuestGoalReference:
    return QuestGoalReference(
        recommended_goals=[
            GoalReference(
                goal_id="goal-1",
                goal_type=goal_type,
                description=description,
                priority=0.9,
                related_quest=related,
                confidence=0.9,
                reasoning="demo",
            )
        ],
        confidence=0.9,
    )


def _navigation(target: str = "赫丽娜") -> NavigationReference:
    return NavigationReference(
        navigation_id="nav-1",
        start_location="射手村",
        target_location=target,
        route_steps=[
            RouteStep(
                step_type=RouteStepType.LOCAL_MOVE_REFERENCE,
                source="射手村",
                target=target,
            )
        ],
        estimated_cost=1.0,
        confidence=0.9,
    )


def _reflex(danger: bool = False) -> ReflexReference:
    if not danger:
        return ReflexReference(
            reflex_id="reflex-normal",
            state=ReflexStateType.NORMAL,
            confidence=0.9,
        )
    return ReflexReference(
        reflex_id="reflex-danger",
        state=ReflexStateType.LOW_HP,
        danger_events=[
            DangerEventReference(
                event_id="event-1",
                event_type=DangerEventType.HP_LOW,
                severity=0.6,
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )


def test_behavior_step_creation():
    step = BehaviorStep(
        step_type=BehaviorStepType.INTERACT_REFERENCE,
        description="与目标交互",
    )
    assert step.step_type is BehaviorStepType.INTERACT_REFERENCE
    assert step.metadata == {}


def test_behavior_reference_creation():
    reference = BehaviorReference(
        behavior_id="behavior-1",
        goal_reference="NPC_INTERACTION_REFERENCE: 与赫丽娜交互",
        confidence=0.9,
    )
    assert reference.behavior_id == "behavior-1"
    assert reference.behavior_steps == []
    assert reference.confidence == 0.9


def test_goal_mapping_npc():
    types = GoalMapper().map(_quest_goal())
    assert types == [
        BehaviorStepType.NAVIGATE_REFERENCE,
        BehaviorStepType.INTERACT_REFERENCE,
        BehaviorStepType.VERIFY_REFERENCE,
    ]


def test_goal_mapping_combat():
    types = GoalMapper().map(
        _quest_goal(
            goal_type=GoalType.QUEST_PROGRESS,
            description="击杀绿水灵",
            related="绿水灵任务",
        ),
        target_hint="绿水灵",
    )
    assert types == [
        BehaviorStepType.NAVIGATE_REFERENCE,
        BehaviorStepType.COMBAT_REFERENCE,
        BehaviorStepType.VERIFY_REFERENCE,
    ]


def test_goal_mapping_collect():
    types = GoalMapper().map(
        _quest_goal(
            goal_type=GoalType.QUEST_PROGRESS,
            description="收集树液",
            related="收集任务",
        )
    )
    assert types == [
        BehaviorStepType.NAVIGATE_REFERENCE,
        BehaviorStepType.COLLECT_REFERENCE,
        BehaviorStepType.VERIFY_REFERENCE,
    ]


def test_planner_npc_behavior():
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(),
    )
    types = [step.step_type for step in reference.behavior_steps]
    assert types == [
        BehaviorStepType.NAVIGATE_REFERENCE,
        BehaviorStepType.INTERACT_REFERENCE,
        BehaviorStepType.VERIFY_REFERENCE,
    ]
    assert reference.goal_reference.startswith("NPC_INTERACTION_REFERENCE")
    assert reference.confidence == 0.9
    assert reference.behavior_steps[0].metadata["route_available"] is True


def test_planner_reflex_danger_inserts_wait():
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(danger=True),
    )
    assert (
        reference.behavior_steps[0].step_type
        is BehaviorStepType.WAIT_REFERENCE
    )
    assert reference.confidence == 0.8
    assert any("危险事件" in line for line in reference.reasoning)


def test_planner_no_navigation_lowers_confidence():
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=None,
        reflex_reference=_reflex(),
    )
    assert reference.confidence == 0.8
    navigate = next(
        step
        for step in reference.behavior_steps
        if step.step_type is BehaviorStepType.NAVIGATE_REFERENCE
    )
    assert navigate.metadata["route_available"] is False


def test_validator_valid():
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(),
    )
    result = BehaviorValidator().validate(reference)
    assert result.verdict is BehaviorVerdict.VALID
    assert result.issues == []


def test_validator_warning_empty_steps():
    reference = BehaviorReference(
        behavior_id="behavior-empty",
        goal_reference="GOAL",
        confidence=0.9,
    )
    result = BehaviorValidator().validate(reference)
    assert result.verdict is BehaviorVerdict.WARNING
    assert any("empty behavior steps" in issue for issue in result.issues)


def test_validator_blocked():
    reference = BehaviorReference(
        behavior_id="",
        confidence=0.9,
    )
    result = BehaviorValidator().validate(reference)
    assert result.verdict is BehaviorVerdict.BLOCKED
    assert "missing behavior id" in result.issues


def test_replay_generation(tmp_path):
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(),
    )
    validation = BehaviorValidator().validate(reference)
    save_behavior_trace(
        tmp_path,
        "trace-replay",
        goal=reference.goal_reference,
        steps=reference.behavior_steps,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "behavior_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["goal"].startswith("NPC_INTERACTION_REFERENCE")
    assert replay["steps"][0]["type"] == "NAVIGATE_REFERENCE"
    assert replay["steps"][-1]["type"] == "VERIFY_REFERENCE"
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(),
    )
    context = AgentLoopContext(
        trace_id="trace-behavior",
        status=AgentLoopStatus.PLANNING,
        behavior_reference=reference,
    )
    assert context.behavior_reference is not None
    assert context.behavior_reference.behavior_steps[0].step_type is (
        BehaviorStepType.NAVIGATE_REFERENCE
    )


def test_webui_behavior_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    reference = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=_reflex(),
    )
    validation = BehaviorValidator().validate(reference)
    payload = {
        "behavior_id": reference.behavior_id,
        "goal_reference": reference.goal_reference,
        "behavior_steps": [
            step.model_dump(mode="json")
            for step in reference.behavior_steps
        ],
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, behavior=payload)
    with TestClient(app) as client:
        resp = client.get("/api/behavior/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal_reference"].startswith("NPC_INTERACTION_REFERENCE")
    assert data["behavior_steps"][0]["step_type"] == "NAVIGATE_REFERENCE"
    assert data["confidence"] == 0.9
    assert data["validation"] == "VALID"


def test_webui_behavior_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/behavior/state")
    assert resp.json()["enabled"] is False
