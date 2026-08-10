"""Execution Orchestration 数据模型(Phase 5-C,只读模拟编排)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.execution.feedback import ExecutionFeedback
from maple_agent.execution.state_machine import ExecutionStepStatus
from maple_agent.executor.models import (
    ExecutionResult,
    ExecutionTask,
    SafetyResult,
)


class ExecutionStepRecord(BaseModel):
    """单个步骤的编排记录。"""

    step_id: str
    step_index: int
    task: ExecutionTask
    status: ExecutionStepStatus = ExecutionStepStatus.CREATED
    safety: SafetyResult | None = None
    transitions: list[dict] = Field(default_factory=list)
    result: ExecutionResult | None = None
    feedback: ExecutionFeedback | None = None


class ExecutionOrchestrationState(BaseModel):
    """编排器状态快照(供 WebUI/Replay 展示)。"""

    plan_id: str = ""
    total_steps: int = 0
    current_step: int = 0
    status: str = "IDLE"
    mode: str = "MOCK ONLY"
    last_result: str = ""
    trace_id: str = ""
