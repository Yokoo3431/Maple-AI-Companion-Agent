"""SafetyVNextPolicyService:策略默认值 / 模式不变量(仅契约)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.safety_vnext.models import (
    ControlledExecutionPolicyReference,
    ExecutionMode,
)


class SafetyVNextPolicyService:
    """提供策略默认值与模式约束检查。"""

    @staticmethod
    def default_policy() -> ControlledExecutionPolicyReference:
        """生产默认:MOCK_ONLY 且未启用。"""
        return ControlledExecutionPolicyReference(
            policy_id=new_id(),
            execution_mode=ExecutionMode.MOCK_ONLY,
            enabled=False,
        )

    @staticmethod
    def controlled_test_policy(
        *,
        allowed_action_types: list[str] | None = None,
    ) -> ControlledExecutionPolicyReference:
        """定义 CONTROLLED_TEST 策略,但保持未启用。"""
        return ControlledExecutionPolicyReference(
            policy_id=new_id(),
            execution_mode=ExecutionMode.CONTROLLED_TEST,
            allowed_action_types=list(allowed_action_types or []),
            enabled=False,
        )

    @staticmethod
    def validate_mode_invariant(
        policy: ControlledExecutionPolicyReference,
    ) -> list[str]:
        """当前约束:非 MOCK_ONLY 模式不得启用。"""
        issues: list[str] = []
        if (
            policy.execution_mode is not ExecutionMode.MOCK_ONLY
            and policy.enabled
        ):
            issues.append(
                "non-MOCK_ONLY policy must remain disabled "
                "until Safety vNext approved"
            )
        if policy.requires_human_confirmation is False:
            issues.append("human confirmation is mandatory")
        if policy.requires_permission_token is False:
            issues.append("permission token is mandatory")
        if policy.requires_outcome_verification is False:
            issues.append("outcome verification is mandatory")
        if policy.requires_kill_switch is False:
            issues.append("kill switch is mandatory")
        return issues
