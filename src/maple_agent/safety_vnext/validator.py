"""SafetyVNext 校验与门评估(确定性,仅契约,不执行)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_proposal.validator import (
    ActionProposalValidator,
    ActionProposalVerdict,
)
from maple_agent.confirmation.models import (
    ConfirmationStatus,
    PermissionToken,
)
from maple_agent.logging_setup import new_id
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_vnext.models import (
    ControlledExecutionGateReference,
    ControlledExecutionPolicyReference,
    ControlledExecutionReadinessReference,
    ExecutionBudgetReference,
    ExecutionMode,
    ExecutionSessionReference,
    GameWindowBindingReference,
    GateCheckReference,
    GateCheckStatus,
    GateInputReference,
    GateVerdict,
    KillSwitchReference,
    KillSwitchState,
    KnowledgeReadinessReference,
    ReadinessStatus,
    RealVisionReadinessReference,
)


class ControlledExecutionGateEvaluator:
    """按强制 gate 顺序评估受控执行资格。"""

    def evaluate_typed(
        self,
        gate_input: GateInputReference,
    ) -> ControlledExecutionGateReference:
        """强类型路径:完整 enforce 文档 Gate Order。"""
        checks: list[GateCheckReference] = []
        action = gate_input.action
        policy = gate_input.policy
        binding = gate_input.window_binding
        session = gate_input.session
        permission = gate_input.permission
        permission_policy = gate_input.permission_policy

        # 1. ACTION
        action_valid = self._check_action(
            action,
            gate_input.action_validation,
        )
        checks.append(
            self._check(
                "ACTION",
                action_valid,
                "action proposal invalid",
            )
        )
        # 2. SAFETY
        safety_allow = (
            gate_input.safety_evaluation is not None
            and gate_input.safety_evaluation.decision
            is SafetyDecisionType.ALLOW
        )
        checks.append(
            self._check(
                "SAFETY",
                safety_allow,
                "safety gate not ALLOW",
            )
        )
        # 3. CONFIRMATION
        confirmation_ok = (
            gate_input.confirmation is ConfirmationStatus.APPROVED
        )
        checks.append(
            self._check(
                "CONFIRMATION",
                confirmation_ok,
                "confirmation not approved",
            )
        )
        # 4. PERMISSION
        permission_ok, permission_reason = self._check_permission(
            permission,
            permission_policy,
            action,
            binding,
            session,
        )
        checks.append(
            self._check(
                "PERMISSION",
                permission_ok,
                permission_reason,
            )
        )
        # 5. WINDOW_BINDING
        binding_ok, binding_reason = self._check_binding(
            binding,
            policy,
            permission_policy,
        )
        checks.append(
            self._check(
                "WINDOW_BINDING",
                binding_ok,
                binding_reason,
            )
        )
        # 6. SESSION
        session_ok, session_reason = self._check_session(
            session,
            policy,
            binding,
        )
        checks.append(
            self._check(
                "SESSION",
                session_ok,
                session_reason,
            )
        )
        # 7. POLICY
        policy_ok, policy_reason = self._check_policy(
            policy,
            action,
            binding,
        )
        checks.append(
            self._check("POLICY", policy_ok, policy_reason)
        )
        # 8. RATE / BUDGET
        budget_ok, budget_reason = self._check_budget(
            policy,
            gate_input.budget,
            action,
        )
        checks.append(
            self._check("RATE_BUDGET", budget_ok, budget_reason)
        )
        # 9. KILL_SWITCH
        kill_ok, kill_reason = self._check_kill_switch(
            policy,
            gate_input.kill_switches,
        )
        checks.append(
            self._check("KILL_SWITCH", kill_ok, kill_reason)
        )
        # 10. EXPECTED_OUTCOME
        outcome_ok, outcome_reason = self._check_outcome(
            policy,
            gate_input.expected_outcome,
            action,
        )
        checks.append(
            self._check(
                "EXPECTED_OUTCOME",
                outcome_ok,
                outcome_reason,
                warn_ok=(
                    policy is not None
                    and not policy.requires_outcome_verification
                    and gate_input.expected_outcome is None
                ),
            )
        )
        blocked = [
            check.reason
            for check in checks
            if check.status is GateCheckStatus.BLOCK
        ]
        warnings = [
            check.reason
            for check in checks
            if check.status is GateCheckStatus.WARN
        ]
        contract_eligible = not blocked
        verdict = GateVerdict.BLOCKED_REFERENCE
        runtime_eligible = False
        if (
            policy is not None
            and policy.execution_mode is ExecutionMode.MOCK_ONLY
        ):
            contract_eligible = False
            verdict = GateVerdict.BLOCKED_REFERENCE
            if "runtime mode MOCK_ONLY" not in blocked:
                blocked.append("runtime mode MOCK_ONLY")
        elif blocked:
            contract_eligible = False
            verdict = GateVerdict.BLOCKED_REFERENCE
        elif warnings:
            contract_eligible = False
            verdict = GateVerdict.WARNING_REFERENCE
        else:
            contract_eligible = True
            verdict = GateVerdict.ELIGIBLE_REFERENCE
            runtime_eligible = (
                gate_input.runtime_mode is not ExecutionMode.MOCK_ONLY
            )
        return ControlledExecutionGateReference(
            gate_id=new_id(),
            verdict=verdict,
            blocked_reasons=blocked,
            warnings=warnings,
            action_reference=(
                f"{getattr(action.action_type, 'value', action.action_type)}: "
                f"{action.target_reference}"
                if action is not None
                else gate_input.action_validation
            ),
            policy_id=policy.policy_id if policy is not None else "",
            session_id=session.session_id if session is not None else "",
            window_binding_id=(
                binding.binding_id if binding is not None else ""
            ),
            expected_outcome_id=(
                gate_input.expected_outcome.expectation_id
                if gate_input.expected_outcome is not None
                else ""
            ),
            checks=checks,
            contract_eligible=contract_eligible,
            runtime_eligible=runtime_eligible,
        )

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
        """兼容路径:旧签名 -> 强类型 GateInputReference(legacy action reference)。"""
        confirmation = None
        if confirmation_status:
            try:
                confirmation = ConfirmationStatus(confirmation_status)
            except ValueError:
                confirmation = None
        token = (
            permission
            if isinstance(permission, PermissionToken)
            else (
                PermissionToken(
                    token_id="legacy",
                    approved=bool(getattr(permission, "approved", False)),
                    scope=str(getattr(permission, "scope", "")),
                    expires_at=getattr(permission, "expires_at", None),
                )
                if permission is not None
                else None
            )
        )
        gate_input = GateInputReference(
            action=None,
            action_validation=action_reference,
            safety_evaluation=safety_evaluation,
            confirmation=confirmation,
            permission=token,
            window_binding=window_binding,
            session=session,
            policy=policy,
            kill_switches=kill_switches or [],
            expected_outcome=None,
            budget=None,
            runtime_mode=ExecutionMode.MOCK_ONLY,
        )
        # legacy 路径:expected_outcome_id 非空视为 outcome 满足
        if expected_outcome_id:
            gate_input = gate_input.model_copy(
                update={
                    "expected_outcome": self._legacy_outcome(
                        expected_outcome_id
                    )
                }
            )
        gate = self.evaluate_typed(gate_input)
        if action_reference:
            gate = gate.model_copy(update={"action_reference": action_reference})
        return gate

    @staticmethod
    def _legacy_outcome(expected_outcome_id: str):
        from maple_agent.action_verification.models import (
            ExpectedOutcomeReference,
        )

        return ExpectedOutcomeReference(
            expectation_id=expected_outcome_id,
        )

    @staticmethod
    def _check(
        gate_name: str,
        ok: bool,
        reason: str,
        *,
        warn_ok: bool = False,
    ) -> GateCheckReference:
        if ok:
            return GateCheckReference(
                gate_name=gate_name,
                status=GateCheckStatus.PASS,
                reason=f"{gate_name} passed",
            )
        if warn_ok:
            return GateCheckReference(
                gate_name=gate_name,
                status=GateCheckStatus.WARN,
                reason=reason,
            )
        return GateCheckReference(
            gate_name=gate_name,
            status=GateCheckStatus.BLOCK,
            reason=reason,
        )

    @staticmethod
    def _check_action(
        action: ActionProposalReference | None,
        action_validation: str,
    ) -> bool:
        if action is None:
            # legacy 路径:仅提供 action_reference 字符串时宽松通过
            return bool(action_validation)
        if action.action_type not in set(ActionType):
            return False
        result = ActionProposalValidator().validate(action)
        return result.verdict is ActionProposalVerdict.VALID

    @staticmethod
    def _check_permission(
        permission: PermissionToken | None,
        permission_policy,
        action: ActionProposalReference | None,
        binding: GameWindowBindingReference | None,
        session: ExecutionSessionReference | None,
    ) -> tuple[bool, str]:
        if permission is None or not permission.approved:
            return False, "permission missing or not approved"
        now = datetime.now(UTC)
        if permission.expires_at is not None and permission.expires_at < now:
            return False, "stale permission"
        if (
            permission_policy is not None
            and permission_policy.expires_at is not None
            and permission_policy.expires_at < now
        ):
            return False, "stale permission"
        if action is not None:
            scope = (
                permission_policy.scope.value
                if permission_policy is not None
                else permission.scope
            )
            action_type_value = getattr(
                action.action_type,
                "value",
                action.action_type,
            )
            if scope and action_type_value != scope:
                return False, "permission scope mismatch"
            if (
                permission_policy is not None
                and permission_policy.target_restrictions
                and action.target_reference
                not in permission_policy.target_restrictions
            ):
                return False, "permission target mismatch"
            if (
                permission_policy is not None
                and permission_policy.allowed_action_types
                and getattr(
                    action.action_type,
                    "value",
                    action.action_type,
                )
                not in permission_policy.allowed_action_types
            ):
                return False, "permission action type mismatch"
        if (
            permission_policy is not None
            and permission_policy.window_restriction
            and binding is not None
            and permission_policy.window_restriction != binding.binding_id
        ):
            return False, "permission window mismatch"
        if (
            permission_policy is not None
            and permission_policy.session_restriction
            and session is not None
            and permission_policy.session_restriction != session.session_id
        ):
            return False, "permission session mismatch"
        if (
            permission_policy is not None
            and permission_policy.max_actions > 0
            and session is not None
            and session.action_count >= permission_policy.max_actions
        ):
            return False, "permission action budget exceeded"
        return True, "permission valid"

    @staticmethod
    def _check_binding(
        binding: GameWindowBindingReference | None,
        policy: ControlledExecutionPolicyReference | None,
        permission_policy,
    ) -> tuple[bool, str]:
        if binding is None:
            return False, "window binding missing"
        if binding.validation_status is not ReadinessStatus.PASSED:
            return False, "window binding not valid"
        if not binding.process_reference or not binding.window_reference:
            return False, "window binding incomplete"
        if (
            binding.expires_at is not None
            and binding.expires_at < datetime.now(UTC)
        ):
            return False, "binding expired"
        if (
            policy is not None
            and policy.window_restriction
            and policy.window_restriction != binding.binding_id
        ):
            return False, "policy window mismatch"
        if (
            permission_policy is not None
            and permission_policy.window_restriction
            and permission_policy.window_restriction != binding.binding_id
        ):
            return False, "permission window mismatch"
        return True, "window binding valid"

    @staticmethod
    def _check_session(
        session: ExecutionSessionReference | None,
        policy: ControlledExecutionPolicyReference | None,
        binding: GameWindowBindingReference | None,
    ) -> tuple[bool, str]:
        if session is None:
            return False, "execution session missing"
        if session.status != "ACTIVE":
            return False, "execution session not active"
        if (
            session.expires_at is not None
            and session.expires_at < datetime.now(UTC)
        ):
            return False, "session expired"
        if policy is not None:
            if session.architecture_version != policy.architecture_version:
                return False, "session architecture incompatible"
            if session.execution_mode != policy.execution_mode:
                return False, "session mode incompatible"
            if (
                session.policy_id
                and session.policy_id != policy.policy_id
            ):
                return False, "session policy mismatch"
        if (
            session.window_binding_id
            and binding is not None
            and session.window_binding_id != binding.binding_id
        ):
            return False, "wrong window"
        return True, "execution session valid"

    @staticmethod
    def _check_policy(
        policy: ControlledExecutionPolicyReference | None,
        action: ActionProposalReference | None,
        binding: GameWindowBindingReference | None,
    ) -> tuple[bool, str]:
        if policy is None:
            return False, "policy missing"
        if not policy.enabled:
            return False, "policy disabled"
        if (
            policy.expires_at is not None
            and policy.expires_at < datetime.now(UTC)
        ):
            return False, "policy expired"
        if policy.architecture_version.value != "VNEXT":
            return False, "policy version incompatible"
        if action is not None:
            action_type_value = getattr(
                action.action_type,
                "value",
                action.action_type,
            )
            if (
                policy.allowed_action_types
                and action_type_value not in policy.allowed_action_types
            ):
                return False, "policy action type mismatch"
            if (
                policy.target_restrictions
                and action.target_reference
                not in policy.target_restrictions
            ):
                return False, "policy target mismatch"
        if (
            policy.window_restriction
            and binding is not None
            and policy.window_restriction != binding.binding_id
        ):
            return False, "policy window mismatch"
        return True, "policy valid"

    @staticmethod
    def _check_budget(
        policy: ControlledExecutionPolicyReference | None,
        budget: ExecutionBudgetReference | None,
        action: ActionProposalReference | None,
    ) -> tuple[bool, str]:
        if policy is None or budget is None:
            return True, "budget not provided"
        if budget.actions_last_second >= policy.max_actions_per_second:
            return False, "rate per second exceeded"
        if budget.actions_last_minute >= policy.max_actions_per_minute:
            return False, "rate per minute exceeded"
        if (
            budget.continuous_execution_seconds
            >= policy.max_continuous_execution_time
        ):
            return False, "continuous execution budget exceeded"
        if budget.retry_count >= policy.max_retry_count:
            return False, "retry budget exceeded"
        if budget.failure_count >= policy.max_failure_count:
            return False, "failure budget exceeded"
        if (
            action is not None
            and getattr(action.action_type, "value", action.action_type)
            == "NAVIGATE"
            and budget.current_action_elapsed
            >= policy.max_navigation_timeout
        ):
            return False, "navigation timeout budget exceeded"
        if (
            action is not None
            and getattr(action.action_type, "value", action.action_type)
            == "COMBAT"
            and budget.current_action_elapsed >= policy.max_combat_duration
        ):
            return False, "combat duration budget exceeded"
        return True, "budget valid"

    @staticmethod
    def _check_kill_switch(
        policy: ControlledExecutionPolicyReference | None,
        kill_switches: list[KillSwitchReference],
    ) -> tuple[bool, str]:
        if policy is not None and policy.requires_kill_switch:
            if not kill_switches:
                return False, "kill switch missing"
        for switch in kill_switches:
            if switch.state is KillSwitchState.ACTIVE:
                if switch.kill_switch_type.value == "USER_EMERGENCY":
                    return False, "user emergency stop active"
                return False, "kill switch active"
        return True, "kill switch clear"

    @staticmethod
    def _check_outcome(
        policy: ControlledExecutionPolicyReference | None,
        expected_outcome,
        action: ActionProposalReference | None,
    ) -> tuple[bool, str]:
        if policy is None:
            return False, "policy missing"
        if policy.requires_outcome_verification:
            if expected_outcome is None:
                return False, "outcome verification required"
            if not expected_outcome.expectation_id:
                return False, "outcome verification required"
            if action is not None and expected_outcome.action_id:
                if expected_outcome.action_id != action.action_id:
                    return False, "outcome action mismatch"
            return True, "expected outcome present"
        if expected_outcome is None:
            return False, "outcome verification recommended"
        return True, "expected outcome present"


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
