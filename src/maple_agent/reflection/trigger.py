"""ReflectionTrigger:是否触发重新规划(只读决策)。"""

from __future__ import annotations

from enum import StrEnum

from maple_agent.reflection.models import ReflectionResult


class TriggerDecision(StrEnum):
    """重新规划触发结论。"""

    REPLAN_REQUIRED = "REPLAN_REQUIRED"
    NO_ACTION = "NO_ACTION"


class ReflectionTrigger:
    """触发规则:执行失败 / 反馈失败 / 世界状态不一致 → 重新规划。"""

    def evaluate(
        self,
        reflection: ReflectionResult,
        *,
        execution_failed: bool | None = None,
        feedback_success: bool | None = None,
        world_mismatch: bool | None = None,
    ) -> TriggerDecision:
        if execution_failed is True or not reflection.success:
            return TriggerDecision.REPLAN_REQUIRED
        if feedback_success is False:
            return TriggerDecision.REPLAN_REQUIRED
        if world_mismatch is True:
            return TriggerDecision.REPLAN_REQUIRED
        return TriggerDecision.NO_ACTION
