"""FailureDetector:动作失败检测(确定性规则,无 LLM)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.game_state.models import GameStateReference
from maple_agent.recovery.models import FailureType
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)


class FailureDetector:
    """检测导航超时 / 状态不匹配 / 战斗失败 / 安全阻止。"""

    def detect(
        self,
        action: ActionProposalReference,
        *,
        game_state: GameStateReference | None = None,
        safety_evaluation: SafetyEvaluationReference | None = None,
        timeout_hint: bool = False,
        npc_missing: bool = False,
        hp_decreased: bool = False,
    ) -> FailureType:
        if (
            safety_evaluation is not None
            and safety_evaluation.decision
            is SafetyDecisionType.BLOCKED
        ):
            return FailureType.SAFETY_BLOCKED
        if timeout_hint:
            return FailureType.NAVIGATION_TIMEOUT
        if (
            action.action_type is ActionType.INTERACT
            and npc_missing
        ):
            return FailureType.STATE_MISMATCH
        if (
            action.action_type is ActionType.COMBAT
            and hp_decreased
        ):
            return FailureType.COMBAT_FAILURE
        return FailureType.UNKNOWN
