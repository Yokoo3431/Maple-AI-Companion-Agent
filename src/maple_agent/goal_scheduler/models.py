"""Multi Goal Scheduling 数据模型(Phase 7-F,多目标调度,只读)。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class GoalScheduleStatus(StrEnum):
    """目标调度状态。"""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    DEFERRED = "DEFERRED"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class GoalScheduleRecord(BaseModel):
    """目标调度记录。"""

    schedule_id: str
    goal_id: str = ""
    priority: int = Field(default=1, ge=1, le=100)
    urgency: float = Field(default=0.0, ge=0, le=1)
    importance: float = Field(default=0.0, ge=0, le=1)
    resource_cost: float = Field(default=0.0, ge=0, le=1)
    dependency: str = ""
    deadline: datetime | None = None
    status: GoalScheduleStatus = GoalScheduleStatus.PENDING
    confidence: float = Field(default=0.0, ge=0, le=1)


class GoalPriorityResult(BaseModel):
    """目标优先级评分。"""

    goal_id: str
    score: float = Field(default=0.0, ge=0, le=1)
    components: dict = Field(default_factory=dict)
    reasoning: list[str] = Field(default_factory=list)


class OptimizedGoalSchedule(BaseModel):
    """优化后的目标调度参考。"""

    goal_order: list[str] = Field(default_factory=list)
    selected_goal: str = ""
    deferred_goals: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    summary: str = ""


class ConflictResolution(BaseModel):
    """目标冲突消解。"""

    conflict_type: str = ""
    affected_goals: list[str] = Field(default_factory=list)
    resolution: str = ""
