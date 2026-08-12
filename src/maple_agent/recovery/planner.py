"""RecoveryPlanner:失败类型 -> 恢复建议参考(只读)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import ActionProposalReference
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.recovery.models import (
    FailureType,
    RecoveryReference,
    RecoveryType,
)
from maple_agent.safety_gate.models import SafetyEvaluationReference


class RecoveryPlanner:
    """把失败类型映射为恢复建议。"""

    _MAPPING = {
        FailureType.NAVIGATION_TIMEOUT: RecoveryType.RETRY_REFERENCE,
        FailureType.ACTION_TIMEOUT: RecoveryType.RETRY_REFERENCE,
        FailureType.STATE_MISMATCH: RecoveryType.REPLAN_REFERENCE,
        FailureType.OUTCOME_MISMATCH: RecoveryType.REPLAN_REFERENCE,
        FailureType.COMBAT_FAILURE: (
            RecoveryType.WAIT_OBSERVATION_REFERENCE
        ),
        FailureType.SAFETY_BLOCKED: RecoveryType.ABORT_REFERENCE,
        FailureType.UNKNOWN: (
            RecoveryType.WAIT_OBSERVATION_REFERENCE
        ),
    }
    _CONFIDENCE = {
        RecoveryType.RETRY_REFERENCE: 0.8,
        RecoveryType.REPLAN_REFERENCE: 0.85,
        RecoveryType.WAIT_OBSERVATION_REFERENCE: 0.8,
        RecoveryType.CHANGE_TARGET_REFERENCE: 0.8,
        RecoveryType.ABORT_REFERENCE: 0.95,
    }

    def __init__(self) -> None:
        self.last_reference: RecoveryReference | None = None

    def plan(
        self,
        action: ActionProposalReference,
        failure_type: FailureType,
        *,
        game_state: GameStateReference | None = None,
        safety_evaluation: SafetyEvaluationReference | None = None,
    ) -> RecoveryReference:
        recovery_type = self._MAPPING.get(
            failure_type,
            RecoveryType.WAIT_OBSERVATION_REFERENCE,
        )
        reasoning = [
            f"失败类型: {failure_type.value}",
            f"建议恢复: {recovery_type.value}",
        ]
        if failure_type is FailureType.SAFETY_BLOCKED:
            reasoning.append("安全门阻止,建议终止当前动作链")
        elif failure_type is FailureType.COMBAT_FAILURE:
            reasoning.append("战斗中出现 HP 下降,建议先观察恢复")
        reference = RecoveryReference(
            recovery_id=new_id(),
            source_action=(
                f"{getattr(action.action_type, 'value', action.action_type)}: "
                f"{action.target_reference}"
            ),
            failure_type=failure_type,
            recovery_type=recovery_type,
            reasoning=reasoning,
            confidence=self._CONFIDENCE[recovery_type],
            validation="",
        )
        self.last_reference = reference
        return reference
