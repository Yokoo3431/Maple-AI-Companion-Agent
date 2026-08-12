"""Action Proposal 单测:行为映射/动作生成/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.action_proposal import (
    ActionProposalMapper,
    ActionProposalReference,
    ActionProposalValidator,
    ActionProposalVerdict,
    ActionType,
    save_action_proposal_trace,
)
from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.behavior import BehaviorPlanner
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
    combat: bool = False,
) -> QuestGoalReference:
    goal_type = (
        GoalType.QUEST_PROGRESS if combat else GoalType.NPC_INTERACTION_REFERENCE
    )
    description = "击杀绿水灵" if combat else "与赫丽娜交互"
    related = "绿水灵任务" if combat else "新手任务"
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


def _reflex() -> ReflexReference:
    return ReflexReference(
        reflex_id="reflex-normal",
        state=ReflexStateType.NORMAL,
        confidence=0.9,
    )


def _behavior(combat: bool = False):
    return BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(combat),
        navigation_reference=_navigation(
            "绿水灵" if combat else "赫丽娜"
        ),
        reflex_reference=_reflex(),
        target_hint="绿水灵" if combat else "",
    )


def _map(combat: bool = False):
    return ActionProposalMapper().map(
        _behavior(combat),
        navigation_reference=_navigation(
            "绿水灵" if combat else "赫丽娜"
        ),
        reflex_reference=_reflex(),
    )


def test_action_type_enum():
    assert ActionType.NAVIGATE.value == "NAVIGATE"
    assert ActionType.COMBAT.value == "COMBAT"
    assert ActionType.WAIT.value == "WAIT"


def test_action_proposal_creation():
    reference = ActionProposalReference(
        action_id="action-1",
        action_type=ActionType.INTERACT,
        source_behavior="INTERACT_REFERENCE",
        target_reference="赫丽娜",
        confidence=0.9,
    )
    assert reference.action_type is ActionType.INTERACT
    assert reference.target_reference == "赫丽娜"


def test_behavior_mapping_npc():
    actions = _map()
    assert [action.action_type for action in actions] == [
        ActionType.NAVIGATE,
        ActionType.INTERACT,
        ActionType.VERIFY,
    ]
    assert actions[0].source_behavior == "NAVIGATE_REFERENCE"
    assert actions[1].target_reference == "赫丽娜"
    assert actions[1].parameters_reference["npc_reference"] == "赫丽娜"


def test_behavior_mapping_combat():
    actions = _map(combat=True)
    assert [action.action_type for action in actions] == [
        ActionType.NAVIGATE,
        ActionType.COMBAT,
        ActionType.VERIFY,
    ]
    combat = actions[1]
    assert combat.parameters_reference["monster_reference"] == "绿水灵"
    assert combat.parameters_reference["note"] == "not attack command"


def test_target_resolution_navigation():
    actions = _map()
    navigate = actions[0]
    assert navigate.target_reference == "赫丽娜"
    assert navigate.parameters_reference["route_reference"]
    assert navigate.parameters_reference["cost"] == 1.0


def test_target_resolution_wait():
    danger_reflex = ReflexReference(
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
    behavior = BehaviorPlanner().plan(
        quest_goal_reference=_quest_goal(),
        navigation_reference=_navigation(),
        reflex_reference=danger_reflex,
    )
    actions = ActionProposalMapper().map(
        behavior,
        navigation_reference=_navigation(),
        reflex_reference=danger_reflex,
    )
    assert any(
        action.action_type is ActionType.WAIT for action in actions
    )


def test_validator_valid_many():
    actions = _map()
    result = ActionProposalValidator().validate_many(actions)
    assert result.verdict is ActionProposalVerdict.VALID
    assert result.issues == []


def test_validator_warning_missing_target():
    reference = ActionProposalReference(
        action_id="action-warn",
        action_type=ActionType.OBSERVE,
        confidence=0.9,
    )
    result = ActionProposalValidator().validate(reference)
    assert result.verdict is ActionProposalVerdict.WARNING
    assert any("missing target" in issue for issue in result.issues)


def test_validator_blocked():
    reference = ActionProposalReference.model_construct(
        action_id="action-bad",
        action_type=ActionType.NAVIGATE,
        confidence=1.5,
    )
    result = ActionProposalValidator().validate(reference)
    assert result.verdict is ActionProposalVerdict.BLOCKED
    assert "confidence out of range" in result.issues


def test_replay_generation(tmp_path):
    actions = _map()
    validation = ActionProposalValidator().validate_many(actions)
    save_action_proposal_trace(
        tmp_path,
        "trace-replay",
        actions=actions,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "action_proposal_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert [action["type"] for action in replay["actions"]] == [
        "NAVIGATE",
        "INTERACT",
        "VERIFY",
    ]
    assert replay["actions"][1]["target"] == "赫丽娜"
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    actions = _map()
    context = AgentLoopContext(
        trace_id="trace-action",
        status=AgentLoopStatus.PLANNING,
        action_proposal_reference=actions[0],
    )
    assert context.action_proposal_reference is not None
    assert context.action_proposal_reference.action_type is ActionType.NAVIGATE


def test_webui_action_proposal_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    actions = _map()
    validation = ActionProposalValidator().validate_many(actions)
    payload = {
        "actions": [
            action.model_dump(mode="json") for action in actions
        ],
        "confidence": actions[0].confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, action_proposal=payload)
    with TestClient(app) as client:
        resp = client.get("/api/action-proposal/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert [action["action_type"] for action in data["actions"]] == [
        "NAVIGATE",
        "INTERACT",
        "VERIFY",
    ]
    assert data["actions"][1]["target_reference"] == "赫丽娜"
    assert data["validation"] == "VALID"


def test_webui_action_proposal_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/action-proposal/state")
    assert resp.json()["enabled"] is False
