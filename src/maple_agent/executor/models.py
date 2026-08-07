"""Execution 数据模型(Phase 2-D,仅契约)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel


class ExecutionStatus(StrEnum):
    """执行状态。"""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class ExecutionTask(BaseModel):
    """执行任务(语义动作,非真实输入)。"""

    execution_id: str
    plan_id: str = ""
    step_id: str = ""
    action: str
    target: str = ""
    status: ExecutionStatus = ExecutionStatus.CREATED
    trace_id: str = ""


class ExecutionResult(BaseModel):
    """执行结果。"""

    execution_id: str
    status: ExecutionStatus
    message: str = ""
    trace_id: str = ""


class SafetyResult(BaseModel):
    """安全门检查结果。"""

    allowed: bool
    reason: str = ""
    mode: str = "mock_only"
