"""RecoveryPlanner:ReflectionResult -> RecoveryPlan(失败恢复规划)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from maple_agent.logging_setup import new_id
from maple_agent.reflection.models import FailureType, ReflectionResult


class RecoveryAction(StrEnum):
    """恢复动作。"""

    RETRY = "retry"
    RE_OBSERVATION = "re-observation"
    KNOWLEDGE_REFRESH = "knowledge_refresh"
    HUMAN_CONFIRMATION = "human_confirmation"


class RecoveryPlan(BaseModel):
    """恢复计划。"""

    plan_id: str
    goal_id: str = ""
    task_id: str = ""
    action: RecoveryAction
    reason: str = ""
    trace_id: str = ""


class RecoveryPlanner:
    """按失败类型映射恢复动作(只读)。"""

    _MAPPING = {
        FailureType.EXECUTION_FAILED: RecoveryAction.RETRY,
        FailureType.WORLD_MISMATCH: RecoveryAction.RE_OBSERVATION,
        FailureType.KNOWLEDGE_ERROR: RecoveryAction.KNOWLEDGE_REFRESH,
        FailureType.LOW_CONFIDENCE: RecoveryAction.HUMAN_CONFIRMATION,
        FailureType.OBSERVATION_FAILED: RecoveryAction.RE_OBSERVATION,
    }

    def plan(
        self,
        reflection: ReflectionResult,
        *,
        goal_id: str = "",
        task_id: str = "",
    ) -> RecoveryPlan:
        if reflection.failure_type is None:
            return RecoveryPlan(
                plan_id=new_id(),
                goal_id=goal_id,
                task_id=task_id,
                action=RecoveryAction.RETRY,
                reason="未指明失败类型,保守重试",
                trace_id=reflection.trace_id,
            )
        action = self._MAPPING.get(
            reflection.failure_type,
            RecoveryAction.RETRY,
        )
        return RecoveryPlan(
            plan_id=new_id(),
            goal_id=goal_id,
            task_id=task_id,
            action=action,
            reason=f"失败类型 {reflection.failure_type.value} 触发 {action.value}",
            trace_id=reflection.trace_id,
        )
