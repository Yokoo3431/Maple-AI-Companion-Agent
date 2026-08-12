"""Safety vNext 单测:默认模式/禁用/门评估/就绪聚合/序列化兼容。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from maple_agent.confirmation.models import PermissionToken
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_vnext import (
    ControlledExecutionGateEvaluator,
    ExecutionMode,
    ExecutionSessionReference,
    GameWindowBindingReference,
    GateVerdict,
    KillSwitchReference,
    KillSwitchState,
    KillSwitchType,
    KnowledgeReadinessReference,
    ReadinessStatus,
    RealVisionReadinessReference,
    SafetyVNextPolicyService,
    aggregate_readiness,
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
