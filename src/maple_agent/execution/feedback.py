"""Execution Feedback:模拟执行后重新观察世界(Mock,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.execution.state_machine import ExecutionStepStatus
from maple_agent.executor.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
)


class ExecutionFeedback(BaseModel):
    """执行反馈(模拟观察结果)。"""

    execution_id: str
    observed: dict[str, bool | str | float] = Field(default_factory=dict)
    success: bool = False
    reason: str = ""
    next_state: ExecutionStepStatus = ExecutionStepStatus.COMPLETED
    trace_id: str = ""


def build_mock_feedback(
    task: ExecutionTask,
    result: ExecutionResult,
) -> ExecutionFeedback:
    """根据 action 语义生成模拟观察反馈(不触发真实观察)。"""
    observed: dict[str, bool | str | float] = {}
    action = task.action.upper()
    if action == "TALK":
        observed = {"dialog_detected": True, "npc_present": True}
    elif action == "COLLECT":
        observed = {"item_count_increased": True}
    elif action == "DEFEAT":
        observed = {"monster_defeated": True}
    elif action == "DELIVER":
        observed = {"delivery_completed": True}
    elif action == "COMPLETE":
        observed = {"quest_completed": True}
    elif action == "MOVE_HINT":
        observed = {"map_changed": True}
    elif action == "WAIT":
        observed = {"condition_checked": True}
    elif action == "PAUSE":
        observed = {"user_confirmed": False}
    else:
        observed = {"observation_ok": True}
    success = result.status is ExecutionStatus.COMPLETED
    return ExecutionFeedback(
        execution_id=task.execution_id,
        observed=observed,
        success=success,
        reason="mock observation" if success else result.message,
        next_state=(
            ExecutionStepStatus.COMPLETED
            if success
            else ExecutionStepStatus.FAILED
        ),
        trace_id=task.trace_id,
    )
