"""Executor Sandbox 数据模型(Phase 6-D,受限执行沙箱,仅 Mock)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class SandboxExecutionStatus(StrEnum):
    """沙箱执行状态。"""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    AUTHORIZED = "AUTHORIZED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class SandboxExecutionRequest(BaseModel):
    """沙箱执行请求。"""

    execution_id: str
    trace_id: str = ""
    permission_token_id: str = ""
    action: str = ""
    target: str = ""
    scope: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class SandboxExecutionResult(BaseModel):
    """沙箱执行结果(mode 固定 MOCK_ONLY)。"""

    execution_id: str
    status: SandboxExecutionStatus
    success: bool = False
    message: str = ""
    mode: str = "MOCK_ONLY"
    audit: dict = Field(default_factory=dict)
