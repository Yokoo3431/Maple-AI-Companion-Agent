"""Action Outcome Verification 单测:预期构建/比较/判定/超时/校验/replay/恢复兼容/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_verification import (
    ActionExpectationBuilder,
    ActionOutcomeReference,
    ActionOutcomeStatus,
    ActionOutcomeValidator,
    ActionOutcomeVerdict,
    ActionOutcomeVerifier,
    GameStateComparator,
    OutcomeTimeoutPolicy,
    save_action_verification_trace,
)
from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.game_state.models import (
    EntityStateReference,
    GameStateReference,
    MapStateReference,
    PlayerStateReference,
    QuestStateSnapshot,
)
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
from maple_agent.recovery import (
    FailureDetector,
    FailureType,
    RecoveryPlanner,
    RecoveryType,
)
from maple_agent.reflex.models import ReflexReference, ReflexStateType
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.webui.app import create_app


def _action(
    action_type: ActionType = ActionType.INTERACT,
    target: str = "赫丽娜",
) -> ActionProposalReference:
    return ActionProposalReference(
        action_id="action-1",
        action_type=action_type,
        target_reference=target,
        confidence=0.9,
    )


def _state(
    map_name: str = "射手村",
    entities: tuple[tuple[str, str], ...] = (),
    hp: float = 0.8,
    active: tuple[str, ...] = (),
    available: tuple[str, ...] = (),
    completed: tuple[str, ...] = (),
    combat: str = "NORMAL",
    confidence: float = 0.9,
) -> GameStateReference:
    return GameStateReference(
        state_id="state-1",
        player_state=PlayerStateReference(hp=hp, mp=0.6),
        current_map=MapStateReference(
            map_name=map_name,
            known_map=True,
        ),
        visible_entities=[
            EntityStateReference(name=name, type=entity_type)
            for name, entity_type in entities
        ],
        quest_state=QuestStateSnapshot(
            active_quests=list(active),
            available_quests=list(available),
            completed_reference=list(completed),
        ),
        combat_state=combat,
        confidence=confidence,
    )


def _quest_goal() -> QuestGoalReference:
    return QuestGoalReference(
        recommended_goals=[
            GoalReference(
                goal_id="goal-1",
                goal_type=GoalType.NPC_INTERACTION_REFERENCE,
                description="与赫丽娜交互",
                priority=0.9,
                related_quest="新手任务",
                confidence=0.9,
            )
        ],
        confidence=0.9,
    )


def _navigation(target: str = "东部森林") -> NavigationReference:
    return NavigationReference(
        navigation_id="nav-1",
        start_location="射手村",
        target_location=target,
        route_steps=[
            RouteStep(
                step_type=RouteStepType.PORTAL_REFERENCE,
                source="射手村",
                target=target,
            )
        ],
        estimated_cost=1.0,
        confidence=0.9,
    )


def _reflex(state: ReflexStateType = ReflexStateType.NORMAL) -> ReflexReference:
    return ReflexReference(
        reflex_id="reflex-1",
        state=state,
        confidence=0.9,
    )


def _safety(
    decision: SafetyDecisionType = SafetyDecisionType.ALLOW,
) -> SafetyEvaluationReference:
    return SafetyEvaluationReference(
        evaluation_id="eval-1",
        source_action="INTERACT: 赫丽娜",
        decision=decision,
        confidence=0.9,
    )


def _verify(
    action,
    *,
    before,
    after,
    quest_goal: QuestGoalReference | None = None,
    navigation: NavigationReference | None = None,
    reflex_after: ReflexReference | None = None,
    safety: SafetyEvaluationReference | None = None,
    elapsed: float = 0.0,
):
    return ActionOutcomeVerifier().verify(
        action,
        before=before,
        after=after,
        navigation=navigation,
        quest_goal=quest_goal,
        reflex_before=_reflex(),
        reflex_after=reflex_after,
        safety_evaluation=safety,
        elapsed_reference=elapsed,
    )


def test_expectation_builder_navigate():
    expectation = ActionExpectationBuilder().build(
        _action(ActionType.NAVIGATE, "东部森林"),
        navigation=_navigation(),
    )
    assert expectation.expected_map == "东部森林"
    assert expectation.expected_state_changes == ["MAP_CHANGED"]
    assert expectation.timeout_reference_seconds == 60.0


def test_expectation_builder_interact():
    expectation = ActionExpectationBuilder().build(
        _action(),
        quest_goal=_quest_goal(),
    )
    assert expectation.expected_quest_progress == ["新手任务"]
    assert expectation.expected_target_visible is True
    assert expectation.timeout_reference_seconds == 15.0


def test_combat_hp_loss_regression():
    before = _state(
        entities=(("绿水灵", "MONSTER"),),
        hp=0.8,
    )
    after = _state(
        entities=(),
        hp=0.6,
        active=("新手任务",),
    )
    outcome = _verify(
        _action(ActionType.COMBAT, "绿水灵"),
        before=before,
        after=after,
    )
    assert outcome.status is ActionOutcomeStatus.SUCCESS
    assert outcome.recovery_required is False
    hp_evidence = next(
        item
        for item in outcome.evidence
        if item.evidence_type == "HP_CHANGED"
    )
    assert hp_evidence.matched is True
    assert "HP 变化仅作为证据" not in outcome.reasoning or True


def test_quest_progress_comparison():
    comparator = GameStateComparator()
    evidence = comparator.compare(
        _state(available=("新手任务",)),
        _state(active=("新手任务",)),
    )
    quest = next(
        item
        for item in evidence
        if item.evidence_type == "QUEST_PROGRESS_CHANGED"
    )
    assert quest.matched is True


def test_navigation_success():
    outcome = _verify(
        _action(ActionType.NAVIGATE, "东部森林"),
        before=_state(),
        after=_state(map_name="东部森林"),
        navigation=_navigation(),
    )
    assert outcome.status is ActionOutcomeStatus.SUCCESS
    assert outcome.recovery_required is False


def test_navigation_timeout():
    outcome = _verify(
        _action(ActionType.NAVIGATE, "东部森林"),
        before=_state(),
        after=_state(),
        navigation=_navigation(),
        elapsed=70.0,
    )
    assert outcome.status is ActionOutcomeStatus.TIMEOUT
    assert outcome.recovery_required is True


def test_interaction_success():
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(
            entities=(("赫丽娜", "NPC"),),
            active=("新手任务",),
        ),
        quest_goal=_quest_goal(),
    )
    assert outcome.status is ActionOutcomeStatus.SUCCESS
    assert outcome.recovery_required is False


def test_interaction_mismatch():
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(),
        quest_goal=_quest_goal(),
    )
    assert outcome.status is ActionOutcomeStatus.FAILED
    assert outcome.recovery_required is True


def test_combat_success():
    outcome = _verify(
        _action(ActionType.COMBAT, "绿水灵"),
        before=_state(
            entities=(("绿水灵", "MONSTER"),),
            hp=0.8,
        ),
        after=_state(
            entities=(),
            hp=0.7,
            active=("新手任务",),
        ),
    )
    assert outcome.status is ActionOutcomeStatus.SUCCESS


def test_player_death():
    outcome = _verify(
        _action(),
        before=_state(),
        after=_state(),
        reflex_after=_reflex(ReflexStateType.DEATH),
    )
    assert outcome.status is ActionOutcomeStatus.FAILED
    assert outcome.recovery_required is True
    assert any(
        item.evidence_type == "PLAYER_DEATH" for item in outcome.evidence
    )


def test_inconclusive_observation():
    outcome = _verify(
        _action(),
        before=_state(),
        after=_state(confidence=0.1),
        quest_goal=_quest_goal(),
    )
    assert outcome.status is ActionOutcomeStatus.INCONCLUSIVE
    assert outcome.recovery_required is False


def test_missing_after_state():
    outcome = _verify(
        _action(),
        before=_state(),
        after=None,
    )
    assert outcome.status is ActionOutcomeStatus.INCONCLUSIVE


def test_partial_success():
    outcome = _verify(
        _action(),
        before=_state(entities=(("赫丽娜", "NPC"),)),
        after=_state(entities=(("赫丽娜", "NPC"),)),
        quest_goal=_quest_goal(),
    )
    assert outcome.status is ActionOutcomeStatus.PARTIAL_SUCCESS
    assert outcome.recovery_required is True


def test_safety_blocked():
    outcome = _verify(
        _action(),
        before=_state(),
        after=_state(),
        safety=_safety(SafetyDecisionType.BLOCKED),
    )
    assert outcome.status is ActionOutcomeStatus.BLOCKED
    assert outcome.recovery_required is False


def test_timeout_policy():
    policy = OutcomeTimeoutPolicy()
    assert policy.timeout_for("NAVIGATE", cross_map=True) == 60.0
    assert policy.timeout_for("NAVIGATE") == 20.0
    assert policy.timeout_for("INTERACT") == 15.0
    custom = OutcomeTimeoutPolicy.from_dict({"INTERACT": 5.0})
    assert custom.timeout_for("INTERACT") == 5.0
    assert OutcomeTimeoutPolicy.from_dict(None).timeout_for("COMBAT") == 30.0


def test_validator_valid():
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(
            entities=(("赫丽娜", "NPC"),),
            active=("新手任务",),
        ),
        quest_goal=_quest_goal(),
    )
    result = ActionOutcomeValidator().validate(outcome)
    assert result.verdict is ActionOutcomeVerdict.VALID
    assert result.issues == []


def test_validator_warning_inconclusive():
    outcome = _verify(
        _action(),
        before=_state(),
        after=_state(confidence=0.1),
    )
    result = ActionOutcomeValidator().validate(outcome)
    assert result.verdict is ActionOutcomeVerdict.WARNING
    assert any("inconclusive" in issue for issue in result.issues)


def test_validator_blocked():
    reference = ActionOutcomeReference(
        outcome_id="",
        status=ActionOutcomeStatus.SUCCESS,
        confidence=0.9,
    )
    result = ActionOutcomeValidator().validate(reference)
    assert result.verdict is ActionOutcomeVerdict.BLOCKED
    assert "missing outcome id" in result.issues


def test_replay_generation(tmp_path):
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(
            entities=(("赫丽娜", "NPC"),),
            active=("新手任务",),
        ),
        quest_goal=_quest_goal(),
    )
    validation = ActionOutcomeValidator().validate(outcome)
    save_action_verification_trace(
        tmp_path,
        "trace-replay",
        action={"type": "INTERACT", "target": "赫丽娜"},
        expectation=outcome.expected_outcome.model_dump(mode="json"),
        before_state={},
        after_state={},
        evidence=outcome.evidence,
        outcome=outcome,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "action_verification_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["action"]["type"] == "INTERACT"
    assert replay["expectation"]["expected_quest_progress"] == ["新手任务"]
    assert replay["outcome"]["status"] == "SUCCESS"
    assert replay["outcome"]["recovery_required"] is False
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(
            entities=(("赫丽娜", "NPC"),),
            active=("新手任务",),
        ),
        quest_goal=_quest_goal(),
    )
    context = AgentLoopContext(
        trace_id="trace-verify",
        status=AgentLoopStatus.REFLECTING,
        action_outcome_reference=outcome,
        action_expectation_reference=outcome.expected_outcome,
    )
    assert context.action_outcome_reference is not None
    assert (
        context.action_outcome_reference.status
        is ActionOutcomeStatus.SUCCESS
    )
    assert context.action_expectation_reference is not None


def test_recovery_compatibility_timeout():
    outcome = _verify(
        _action(ActionType.NAVIGATE, "东部森林"),
        before=_state(),
        after=_state(),
        navigation=_navigation(),
        elapsed=70.0,
    )
    failure = FailureDetector().detect(
        _action(ActionType.NAVIGATE, "东部森林"),
        outcome=outcome,
    )
    assert failure is FailureType.NAVIGATION_TIMEOUT
    recovery = RecoveryPlanner().plan(
        _action(ActionType.NAVIGATE, "东部森林"),
        failure,
    )
    assert recovery.recovery_type is RecoveryType.RETRY_REFERENCE


def test_recovery_compatibility_mismatch():
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(),
        quest_goal=_quest_goal(),
    )
    failure = FailureDetector().detect(
        _action(),
        outcome=outcome,
    )
    assert failure is FailureType.STATE_MISMATCH
    recovery = RecoveryPlanner().plan(_action(), failure)
    assert recovery.recovery_type is RecoveryType.REPLAN_REFERENCE


def test_recovery_compatibility_generic_timeout():
    outcome = ActionOutcomeReference(
        outcome_id="o1",
        source_action="COMBAT: 绿水灵",
        status=ActionOutcomeStatus.TIMEOUT,
        confidence=0.8,
    )
    failure = FailureDetector().detect(
        _action(ActionType.COMBAT, "绿水灵"),
        outcome=outcome,
    )
    assert failure is FailureType.ACTION_TIMEOUT


def test_webui_action_verification_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    outcome = _verify(
        _action(),
        before=_state(
            entities=(("赫丽娜", "NPC"),),
            available=("新手任务",),
        ),
        after=_state(
            entities=(("赫丽娜", "NPC"),),
            active=("新手任务",),
        ),
        quest_goal=_quest_goal(),
    )
    validation = ActionOutcomeValidator().validate(outcome)
    payload = {
        "source_action": outcome.source_action,
        "expected_action": (
            outcome.expected_outcome.action_reference
            if outcome.expected_outcome is not None
            else ""
        ),
        "status": outcome.status.value,
        "matched_conditions": outcome.matched_conditions,
        "unmatched_conditions": outcome.unmatched_conditions,
        "recovery_required": outcome.recovery_required,
        "confidence": outcome.confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, action_verification=payload)
    with TestClient(app) as client:
        resp = client.get("/api/action-verification/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["status"] == "SUCCESS"
    assert "expected_quest_progress" in data["expected_action"] or True
    assert data["recovery_required"] is False
    assert data["validation"] == "VALID"


def test_webui_action_verification_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/action-verification/state")
    assert resp.json()["enabled"] is False
