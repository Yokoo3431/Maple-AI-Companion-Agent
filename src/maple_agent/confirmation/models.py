"""Human Confirmation 数据模型(Phase 6-C,人工授权门控,不执行)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ConfirmationStatus(StrEnum):
    """确认请求状态。"""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"
    BLOCKED = "BLOCKED"


class ConfirmationRequest(BaseModel):
    """人工确认请求。"""

    confirmation_id: str
    trace_id: str = ""
    action_plan_id: str = ""
    action: str = ""
    target: str = ""
    risk_level: str = ""
    vision_score: float = Field(default=0.0, ge=0, le=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ConfirmationStatus = ConfirmationStatus.PENDING


class PermissionToken(BaseModel):
    """逻辑许可令牌(仅授权契约,禁止绑定真实执行)。"""

    token_id: str
    confirmation_id: str = ""
    approved: bool = False
    scope: str = ""
    expires_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
