"""Goal 领域模型(Phase 2-B,不绑定 Quest)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class GoalType(StrEnum):
    """目标类型。"""

    QUEST = "QUEST"
    LEVELING = "LEVELING"
    EXPLORATION = "EXPLORATION"
    COLLECTION = "COLLECTION"
    MAINTENANCE = "MAINTENANCE"
    CUSTOM = "CUSTOM"


class GoalStatus(StrEnum):
    """目标状态。"""

    CREATED = "CREATED"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class Goal(BaseModel):
    """目标定义(与 Quest 解耦,未来可来自任务/用户/系统)。"""

    goal_id: str
    goal_type: GoalType = GoalType.CUSTOM
    title: str
    description: str = ""
    priority: int = Field(default=1, ge=1, le=100)
    status: GoalStatus = GoalStatus.CREATED
    source: str = ""
    confidence: float = Field(default=1.0, ge=0, le=1)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str = ""
