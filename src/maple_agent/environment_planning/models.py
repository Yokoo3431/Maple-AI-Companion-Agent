"""Environment-Aware Planning 数据模型(Phase 8-D,环境驱动规划参考,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class GoalPriorityReference(BaseModel):
    """机会驱动的目标优先级参考。"""

    goal_id: str = ""
    suggested_priority: int = Field(default=1, ge=1, le=100)
    reason: str = ""
    opportunity_type: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class PlanningConstraint(BaseModel):
    """风险驱动的规划约束。"""

    level: str = ""
    source_risk: str = ""
    message: str = ""
    recommendation: str = ""


class EnvironmentPlanningReference(BaseModel):
    """环境规划参考(不触发任何动作)。"""

    recommended_goals: list[str] = Field(default_factory=list)
    blocked_goals: list[str] = Field(default_factory=list)
    priority_adjustments: list[GoalPriorityReference] = Field(
        default_factory=list
    )
    risk_notes: list[str] = Field(default_factory=list)
    opportunity_notes: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
