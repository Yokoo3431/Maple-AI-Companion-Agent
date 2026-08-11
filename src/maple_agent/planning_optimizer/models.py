"""Adaptive Planning Optimization 数据模型(Phase 7-D,只读规划优化)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlanningAnalysis(BaseModel):
    """任务图分析结果。"""

    goal_id: str = ""
    dag_complete: bool = False
    redundant_tasks: list[str] = Field(default_factory=list)
    risk_nodes: list[str] = Field(default_factory=list)
    failure_probability: float = Field(default=0.0, ge=0, le=1)
    experience_match: float = Field(default=0.0, ge=0, le=1)
    task_count: int = 0
    issues: list[str] = Field(default_factory=list)


class PlanningQualityScore(BaseModel):
    """规划质量评分。"""

    planning_score: float = Field(default=0.0, ge=0, le=1)
    dependency_score: float = Field(default=0.0, ge=0, le=1)
    risk_score: float = Field(default=0.0, ge=0, le=1)
    experience_alignment: float = Field(default=0.0, ge=0, le=1)
    estimated_success_probability: float = Field(default=0.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class OptimizedPlanningReference(BaseModel):
    """优化后的规划参考(不触碰执行器)。"""

    goal_id: str = ""
    optimized_order: list[str] = Field(default_factory=list)
    removed_tasks: list[str] = Field(default_factory=list)
    added_recovery_points: list[str] = Field(default_factory=list)
    risk_adjustments: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    summary: str = ""
