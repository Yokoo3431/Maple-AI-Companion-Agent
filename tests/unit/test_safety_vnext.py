"""Safety vNext 单测:默认模式/禁用/门评估/就绪聚合/序列化兼容。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_verification.models import ExpectedOutcomeReference
from maple_agent.confirmation.models import ConfirmationStatus, PermissionToken
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_vnext import (
    ControlledExecutionGateEvaluator,
    ExecutionBudgetReference,
    ExecutionMode,
    ExecutionSessionReference,
    GameWindowBindingReference,
    GateInputReference,
    GateVerdict,
    KillSwitchReference,
    KillSwitchState,
    KillSwitchType,
    KnowledgeReadinessReference,
    PermissionPolicyV2,
    PermissionScopeV2,
    ReadinessStatus,
    RealVisionReadinessReference,
    SafetyVNextPolicyService,
    aggregate_readiness,
    save_controlled_execution_gate_trace,
)


def _policy(**overrides):
    return SafetyVNextPolicyService.controlled_test_policy(
        allowed_action_types=["OBSERVE", "INTERACT"]
    ).model_copy(update=overrides)


def _safety(decision: SafetyDecisionType = SafetyDecisionType.ALLOW):
    return SafetyEvaluationReference(
        evaluation_id="eval-1",
        source_action="INTERACT: 赫丽娜",
        decision=decision,
        confidence=0.9,
    )


def _permission(*, approved: bool = True, expired: bool = False):
    return PermissionToken(
        token_id="token-1",
        approved=approved,
        scope="INTERACT",
        expires_at=(
            datetime.now(UTC) - timedelta(seconds=10)
            if expired
            else datetime.now(UTC) + timedelta(minutes=5)
        ),
    )


def _binding(status: ReadinessStatus = ReadinessStatus.PASSED):
    return GameWindowBindingReference(
        binding_id="binding-1",
        process_reference="MapleStory.exe",
        window_reference="hwnd-1",
        title_reference="MapleStory",
        validation_status=status,
    )


def _session(window_binding_id: str = "binding-1"):
    return ExecutionSessionReference(
        session_id="session-1",
        window_binding_id=window_binding_id,
        execution_mode=ExecutionMode.CONTROLLED_TEST,
        status="ACTIVE",
    )


def _gate(**kwargs):
    defaults = {
        "action_reference": "INTERACT: 赫丽娜",
        "safety_evaluation": _safety(),
        "confirmation_status": "APPROVED",
        "permission": _permission(),
        "window_binding": _binding(),
        "session": _session(),
        "policy": _policy(enabled=True),
        "kill_switches": [
            KillSwitchReference(
                kill_switch_id="ks-1",
                kill_switch_type=KillSwitchType.SESSION,
                state=KillSwitchState.ARMED,
            )
        ],
        "expected_outcome_id": "expect-1",
    }
    defaults.update(kwargs)
    return ControlledExecutionGateEvaluator().evaluate(**defaults)


def test_default_execution_mode_mock_only():
    policy = SafetyVNextPolicyService.default_policy()
    assert policy.execution_mode is ExecutionMode.MOCK_ONLY


def test_unrestricted_mode_absent():
    members = set(ExecutionMode.__members__)
    assert "UNRESTRICTED" not in members
    assert "FULL_AUTO_NO_GUARD" not in members


def test_disabled_by_default():
    assert SafetyVNextPolicyService.default_policy().enabled is False
    assert (
        SafetyVNextPolicyService.controlled_test_policy().enabled is False
    )


def test_permission_requirements():
    policy = _policy().model_copy(
        update={"requires_permission_token": False}
    )
    issues = SafetyVNextPolicyService.validate_mode_invariant(policy)
    assert any("permission token" in issue for issue in issues)


def test_window_binding_requirement():
    gate = _gate(window_binding=None)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "window binding missing" in gate.blocked_reasons


def test_kill_switch_blocks():
    gate = _gate(
        kill_switches=[
            KillSwitchReference(
                kill_switch_id="ks-1",
                kill_switch_type=KillSwitchType.SESSION,
                state=KillSwitchState.ACTIVE,
            )
        ]
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "kill switch active" in gate.blocked_reasons


def test_missing_confirmation_blocks():
    gate = _gate(confirmation_status="PENDING")
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "confirmation not approved" in gate.blocked_reasons


def test_stale_permission_blocks():
    gate = _gate(permission=_permission(expired=True))
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "stale permission" in gate.blocked_reasons


def test_wrong_window_blocks():
    gate = _gate(
        session=_session(window_binding_id="binding-other"),
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "wrong window" in gate.blocked_reasons


def test_outcome_verification_required():
    gate = _gate(expected_outcome_id="")
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "outcome verification required" in gate.blocked_reasons


def test_recovery_cannot_bypass_gate():
    # Recovery 重新进入门控:缺少 confirmation / permission 即 BLOCKED
    gate = _gate(
        confirmation_status="",
        permission=None,
        expected_outcome_id="expect-1",
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "confirmation not approved" in gate.blocked_reasons
    assert any(
        "permission missing" in reason
        for reason in gate.blocked_reasons
    )


def test_gate_eligible_all_pass():
    gate = _gate()
    assert gate.verdict is GateVerdict.ELIGIBLE_REFERENCE
    assert gate.blocked_reasons == []


def test_real_vision_not_ready_blocks_readiness():
    readiness = aggregate_readiness(
        real_vision=RealVisionReadinessReference(),
        knowledge=KnowledgeReadinessReference(),
    )
    assert readiness.real_vision_ready is False
    assert "Real Vision Gate not passed" in readiness.reasons


def test_knowledge_not_ready_blocks_readiness():
    readiness = aggregate_readiness(
        real_vision=RealVisionReadinessReference(),
        knowledge=KnowledgeReadinessReference(),
    )
    assert readiness.knowledge_ready is False
    assert "Knowledge Quality Gate not passed" in readiness.reasons


def test_overall_readiness_not_ready():
    readiness = aggregate_readiness()
    assert readiness.overall_status is ReadinessStatus.NOT_READY
    assert "Real Vision Gate not passed" in readiness.reasons
    assert "Knowledge Quality Gate not passed" in readiness.reasons


def test_serialization_replay_compatibility():
    policy = SafetyVNextPolicyService.default_policy()
    payload = policy.model_dump(mode="json")
    restored = _policy().__class__.model_validate(json.loads(json.dumps(payload)))
    assert restored.execution_mode is ExecutionMode.MOCK_ONLY
    gate = _gate()
    gate_payload = gate.model_dump(mode="json")
    assert gate_payload["verdict"] == "ELIGIBLE_REFERENCE"
    assert gate_payload["validation"] == ""


# ---------------- Strongly-typed gate path ----------------


def _typed_action(
    action_type: ActionType = ActionType.INTERACT,
    target: str = "赫丽娜",
) -> ActionProposalReference:
    return ActionProposalReference(
        action_id="action-1",
        action_type=action_type,
        target_reference=target,
        confidence=0.9,
    )


def _typed_input(**overrides) -> GateInputReference:
    defaults = {
        "action": _typed_action(),
        "safety_evaluation": _safety(),
        "confirmation": ConfirmationStatus.APPROVED,
        "permission": _permission(),
        "permission_policy": PermissionPolicyV2(
            scope=PermissionScopeV2.INTERACT,
            target_restrictions=["赫丽娜"],
            window_restriction="binding-1",
            session_restriction="session-1",
            max_actions=0,
            allowed_action_types=["INTERACT"],
        ),
        "window_binding": _binding(),
        "session": _session(),
        "policy": _policy(enabled=True),
        "kill_switches": [
            KillSwitchReference(
                kill_switch_id="ks-1",
                kill_switch_type=KillSwitchType.SESSION,
                state=KillSwitchState.ARMED,
            )
        ],
        "expected_outcome": ExpectedOutcomeReference(
            expectation_id="expect-1",
            action_id="action-1",
            action_reference="INTERACT: 赫丽娜",
        ),
        "budget": ExecutionBudgetReference(),
        "runtime_mode": ExecutionMode.MOCK_ONLY,
    }
    defaults.update(overrides)
    return GateInputReference(**defaults)


def _typed_gate(**overrides):
    return ControlledExecutionGateEvaluator().evaluate_typed(
        _typed_input(**overrides)
    )


def test_typed_missing_action_blocked():
    gate = _typed_gate(action=None)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "action proposal invalid" in gate.blocked_reasons


def test_typed_invalid_action_blocked():
    invalid = ActionProposalReference.model_construct(
        action_id="bad",
        action_type="NOT_A_TYPE",
        target_reference="x",
        confidence=0.9,
    )
    gate = _typed_gate(action=invalid)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "action proposal invalid" in gate.blocked_reasons


def test_typed_safety_warning_blocked():
    gate = _typed_gate(
        safety_evaluation=_safety(SafetyDecisionType.WARNING)
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "safety gate not ALLOW" in gate.blocked_reasons


def test_typed_confirmation_pending_blocked():
    gate = _typed_gate(confirmation=ConfirmationStatus.PENDING)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "confirmation not approved" in gate.blocked_reasons


def test_typed_confirmation_expired_blocked():
    gate = _typed_gate(confirmation=ConfirmationStatus.EXPIRED)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "confirmation not approved" in gate.blocked_reasons


def test_typed_stale_permission_blocked():
    gate = _typed_gate(permission=_permission(expired=True))
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "stale permission" in gate.blocked_reasons


def test_typed_permission_scope_mismatch():
    policy = PermissionPolicyV2(
        scope=PermissionScopeV2.NAVIGATE,
        target_restrictions=["赫丽娜"],
        window_restriction="binding-1",
        session_restriction="session-1",
    )
    gate = _typed_gate(permission_policy=policy)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert any(
        "scope mismatch" in reason for reason in gate.blocked_reasons
    )


def test_typed_permission_target_mismatch():
    policy = PermissionPolicyV2(
        scope=PermissionScopeV2.INTERACT,
        target_restrictions=["魔法密林"],
    )
    gate = _typed_gate(permission_policy=policy)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "permission target mismatch" in gate.blocked_reasons


def test_typed_permission_window_mismatch():
    policy = PermissionPolicyV2(
        scope=PermissionScopeV2.INTERACT,
        window_restriction="binding-other",
    )
    gate = _typed_gate(permission_policy=policy)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "permission window mismatch" in gate.blocked_reasons


def test_typed_permission_session_mismatch():
    policy = PermissionPolicyV2(
        scope=PermissionScopeV2.INTERACT,
        session_restriction="session-other",
    )
    gate = _typed_gate(permission_policy=policy)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "permission session mismatch" in gate.blocked_reasons


def test_typed_policy_expired_blocked():
    gate = _typed_gate(
        policy=_policy(
            enabled=True,
            expires_at=datetime.now(UTC) - timedelta(seconds=10),
        )
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "policy expired" in gate.blocked_reasons


def test_typed_policy_action_type_mismatch():
    gate = _typed_gate(
        policy=_policy(enabled=True, allowed_action_types=["OBSERVE"])
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "policy action type mismatch" in gate.blocked_reasons


def test_typed_binding_expired_blocked():
    binding = _binding().model_copy(
        update={
            "expires_at": datetime.now(UTC) - timedelta(seconds=10)
        }
    )
    gate = _typed_gate(window_binding=binding)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "binding expired" in gate.blocked_reasons


def test_typed_binding_incomplete_blocked():
    binding = _binding().model_copy(update={"process_reference": ""})
    gate = _typed_gate(window_binding=binding)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "window binding incomplete" in gate.blocked_reasons


def test_typed_session_expired_blocked():
    session = _session().model_copy(
        update={"expires_at": datetime.now(UTC) - timedelta(seconds=10)}
    )
    gate = _typed_gate(session=session)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "session expired" in gate.blocked_reasons


def test_typed_session_wrong_policy_blocked():
    session = _session().model_copy(update={"policy_id": "policy-other"})
    gate = _typed_gate(session=session)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "session policy mismatch" in gate.blocked_reasons


def test_typed_session_wrong_binding_blocked():
    session = _session(window_binding_id="binding-other")
    gate = _typed_gate(session=session)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "wrong window" in gate.blocked_reasons


def test_typed_rate_per_second_exceeded():
    gate = _typed_gate(
        budget=ExecutionBudgetReference(actions_last_second=1)
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "rate per second exceeded" in gate.blocked_reasons


def test_typed_rate_per_minute_exceeded():
    gate = _typed_gate(
        budget=ExecutionBudgetReference(actions_last_minute=20)
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "rate per minute exceeded" in gate.blocked_reasons


def test_typed_retry_budget_exceeded():
    gate = _typed_gate(budget=ExecutionBudgetReference(retry_count=3))
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "retry budget exceeded" in gate.blocked_reasons


def test_typed_failure_budget_exceeded():
    gate = _typed_gate(budget=ExecutionBudgetReference(failure_count=5))
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "failure budget exceeded" in gate.blocked_reasons


def test_typed_continuous_budget_exceeded():
    gate = _typed_gate(
        budget=ExecutionBudgetReference(continuous_execution_seconds=300)
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "continuous execution budget exceeded" in gate.blocked_reasons


def test_typed_navigation_timeout_budget():
    gate = _typed_gate(
        action=_typed_action(ActionType.NAVIGATE, "东部森林"),
        permission_policy=PermissionPolicyV2(
            scope=PermissionScopeV2.NAVIGATE,
            target_restrictions=["东部森林"],
            window_restriction="binding-1",
            session_restriction="session-1",
            allowed_action_types=["NAVIGATE"],
        ),
        policy=_policy(
            enabled=True,
            allowed_action_types=["NAVIGATE"],
        ),
        expected_outcome=ExpectedOutcomeReference(
            expectation_id="expect-1",
            action_id="action-1",
            action_reference="NAVIGATE: 东部森林",
        ),
        budget=ExecutionBudgetReference(current_action_elapsed=60.0),
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "navigation timeout budget exceeded" in gate.blocked_reasons


def test_typed_combat_duration_budget():
    gate = _typed_gate(
        action=_typed_action(ActionType.COMBAT, "绿水灵"),
        permission_policy=PermissionPolicyV2(
            scope=PermissionScopeV2.COMBAT,
            target_restrictions=["绿水灵"],
            window_restriction="binding-1",
            session_restriction="session-1",
            allowed_action_types=["COMBAT"],
        ),
        policy=_policy(
            enabled=True,
            allowed_action_types=["COMBAT"],
        ),
        expected_outcome=ExpectedOutcomeReference(
            expectation_id="expect-1",
            action_id="action-1",
            action_reference="COMBAT: 绿水灵",
        ),
        budget=ExecutionBudgetReference(current_action_elapsed=30.0),
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "combat duration budget exceeded" in gate.blocked_reasons


def test_typed_kill_switch_missing():
    gate = _typed_gate(kill_switches=[])
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "kill switch missing" in gate.blocked_reasons


def test_typed_kill_switch_active():
    gate = _typed_gate(
        kill_switches=[
            KillSwitchReference(
                kill_switch_id="ks-1",
                kill_switch_type=KillSwitchType.SESSION,
                state=KillSwitchState.ACTIVE,
            )
        ]
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "kill switch active" in gate.blocked_reasons


def test_typed_user_emergency_highest_priority():
    gate = _typed_gate(
        kill_switches=[
            KillSwitchReference(
                kill_switch_id="ks-1",
                kill_switch_type=KillSwitchType.USER_EMERGENCY,
                state=KillSwitchState.ACTIVE,
            )
        ]
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "user emergency stop active" in gate.blocked_reasons


def test_typed_outcome_missing_blocked():
    gate = _typed_gate(expected_outcome=None)
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "outcome verification required" in gate.blocked_reasons


def test_typed_outcome_wrong_action_blocked():
    gate = _typed_gate(
        expected_outcome=ExpectedOutcomeReference(
            expectation_id="expect-1",
            action_id="action-other",
        )
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "outcome action mismatch" in gate.blocked_reasons


def test_typed_all_pass_eligible():
    gate = _typed_gate()
    assert gate.verdict is GateVerdict.ELIGIBLE_REFERENCE
    assert gate.contract_eligible is True
    assert gate.runtime_eligible is False  # runtime 仍 MOCK_ONLY


def test_warning_never_eligible():
    gate = _typed_gate(
        policy=_policy(
            enabled=True,
            requires_outcome_verification=False,
        ),
        expected_outcome=None,
    )
    assert gate.verdict is GateVerdict.WARNING_REFERENCE
    assert gate.contract_eligible is False
    assert gate.verdict is not GateVerdict.ELIGIBLE_REFERENCE


def test_mock_only_policy_never_future_eligible():
    gate = _typed_gate(
        policy=_policy(
            execution_mode=ExecutionMode.MOCK_ONLY,
            enabled=True,
        )
    )
    assert gate.verdict is GateVerdict.BLOCKED_REFERENCE
    assert "runtime mode MOCK_ONLY" in gate.blocked_reasons
    assert gate.runtime_eligible is False


def test_gate_trace_replay(tmp_path):
    gate = _typed_gate()
    save_controlled_execution_gate_trace(
        tmp_path,
        "trace-gate",
        action=gate.action_reference,
        checks=gate.checks,
        verdict=gate.verdict.value,
        blocked_reasons=gate.blocked_reasons,
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-gate"
            / "controlled_execution_gate_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["action"] == "INTERACT: 赫丽娜"
    assert replay["verdict"] == "ELIGIBLE_REFERENCE"
    gates = {check["gate"] for check in replay["checks"]}
    assert {
        "ACTION",
        "SAFETY",
        "CONFIRMATION",
        "PERMISSION",
        "WINDOW_BINDING",
        "SESSION",
        "POLICY",
        "RATE_BUDGET",
        "KILL_SWITCH",
        "EXPECTED_OUTCOME",
    } <= gates
