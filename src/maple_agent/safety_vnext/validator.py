"""SafetyVNext 校验与门评估(确定性,仅契约,不执行)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.logging_setup import new_id
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_vnext.models import (
    ControlledExecutionGateReference,
    ControlledExecutionPolicyReference,
    ControlledExecutionReadinessReference,
    ExecutionSessionReference,
    GameWindowBindingReference,
    GateVerdict,
    KillSwitchReference,
    KillSwitchState,
    KnowledgeReadinessReference,
    ReadinessStatus,
    RealVisionReadinessReference,
)


class ControlledExecutionGateEvaluator:
    """按强制 gate 顺序评估受控执行资格。"""

    def evaluate(
        self,
        *,
        action_reference: str = "",
        safety_evaluation: SafetyEvaluationReference | None = None,
        confirmation_status: str = "",
        permission: object | None = None,
        window_binding: GameWindowBindingReference | None = None,
        session: ExecutionSessionReference | None = None,
        policy: ControlledExecutionPolicyReference | None = None,
        kill_switches: list[KillSwitchReference] | None = None,
        expected_outcome_id: str = "",
    ) -> ControlledExecutionGateReference:
        blocked: list[str] = []
        warnings: list[str] = []
        if policy is None:
            blocked.append("policy missing")
        else:
            if not policy.enabled:
                blocked.append("policy disabled")
            if (
                safety_evaluation is None
                or safety_evaluation.decision
                is not SafetyDecisionType.ALLOW
            ):
                blocked.append("safety gate not ALLOW")
            if confirmation_status != "APPROVED":
                blocked.append("confirmation not approved")
            if permission is None or not getattr(
                permission, "approved", False
            ):
                blocked.append("permission missing or not approved")
            elif self._permission_expired(permission):
                blocked.append("stale permission")
            if window_binding is None:
                blocked.append("window binding missing")
            elif (
                window_binding.validation_status
                is not ReadinessStatus.PASSED
            ):
                blocked.append("window binding not valid")
            if session is None:
                blocked.append("execution session missing")
            elif session.status != "ACTIVE":
                blocked.append("execution session not active")
            elif (
                session.window_binding_id
                and window_binding is not None
                and session.window_binding_id
                != window_binding.binding_id
            ):
                blocked.append("wrong window")
            if any(
                switch.state is KillSwitchState.ACTIVE
                for switch in kill_switches or []
            ):
                blocked.append("kill switch active")
            if (
                policy.requires_outcome_verification
                and not expected_outcome_id
            ):
                blocked.append("outcome verification required")
            elif (
                not policy.requires_outcome_verification
                and not expected_outcome_id
            ):
                warnings.append("outcome verification recommended")
        verdict = (
            GateVerdict.ELIGIBLE_REFERENCE
            if not blocked
            else GateVerdict.BLOCKED_REFERENCE
        )
        if blocked and not warnings:
            verdict = GateVerdict.BLOCKED_REFERENCE
        elif not blocked and warnings:
            verdict = GateVerdict.WARNING_REFERENCE
        return ControlledExecutionGateReference(
            gate_id=new_id(),
            verdict=verdict,
            blocked_reasons=blocked,
            warnings=warnings,
            action_reference=action_reference,
            policy_id=policy.policy_id if policy is not None else "",
            session_id=session.session_id if session is not None else "",
            window_binding_id=(
                window_binding.binding_id
                if window_binding is not None
                else ""
            ),
            expected_outcome_id=expected_outcome_id,
        )

    @staticmethod
    def _permission_expired(permission: object) -> bool:
        expires_at = getattr(permission, "expires_at", None)
        if expires_at is None:
            return False
        return expires_at < datetime.now(UTC)


def aggregate_readiness(
    *,
    real_vision: RealVisionReadinessReference | None = None,
    knowledge: KnowledgeReadinessReference | None = None,
    safety_contract_ready: bool = False,
    permission_ready: bool = False,
    window_binding_ready: bool = False,
    kill_switch_ready: bool = False,
    rate_limit_ready: bool = False,
    outcome_verification_ready: bool = False,
) -> ControlledExecutionReadinessReference:
    """聚合受控执行整体就绪度(当前必须 NOT_READY)。"""
    vision_ready = (
        real_vision is not None
        and real_vision.validation_status is ReadinessStatus.PASSED
    )
    knowledge_ready = (
        knowledge is not None
        and knowledge.status is ReadinessStatus.READY
    )
    flags = {
        "safety_contract_ready": safety_contract_ready,
        "real_vision_ready": vision_ready,
        "knowledge_ready": knowledge_ready,
        "permission_ready": permission_ready,
        "window_binding_ready": window_binding_ready,
        "kill_switch_ready": kill_switch_ready,
        "rate_limit_ready": rate_limit_ready,
        "outcome_verification_ready": outcome_verification_ready,
    }
    reasons: list[str] = []
    if not vision_ready:
        reasons.append("Real Vision Gate not passed")
    if not knowledge_ready:
        reasons.append("Knowledge Quality Gate not passed")
    for name, ready in flags.items():
        if not ready:
            reasons.append(f"{name} not ready")
    overall = (
        ReadinessStatus.READY
        if all(flags.values())
        else ReadinessStatus.NOT_READY
    )
    return ControlledExecutionReadinessReference(
        safety_contract_ready=flags["safety_contract_ready"],
        real_vision_ready=flags["real_vision_ready"],
        knowledge_ready=flags["knowledge_ready"],
        permission_ready=flags["permission_ready"],
        window_binding_ready=flags["window_binding_ready"],
        kill_switch_ready=flags["kill_switch_ready"],
        rate_limit_ready=flags["rate_limit_ready"],
        outcome_verification_ready=flags["outcome_verification_ready"],
        overall_status=overall,
        reasons=reasons,
    )
