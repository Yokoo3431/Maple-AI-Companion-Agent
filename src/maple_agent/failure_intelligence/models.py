"""Failure Pattern Intelligence 数据模型(Phase 7-E,只读失败理解)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FailurePatternRecord(BaseModel):
    """结构化失败模式。"""

    pattern_id: str
    failure_type: str = ""
    trigger_conditions: list[str] = Field(default_factory=list)
    context_snapshot: dict = Field(default_factory=dict)
    affected_tasks: list[str] = Field(default_factory=list)
    root_cause: str = ""
    resolution_strategy: str = ""
    success_rate: float = Field(default=0.0, ge=0, le=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    trace_id: str = ""


class FailureMatchResult(BaseModel):
    """失败模式匹配结果。"""

    pattern_id: str
    score: float = Field(default=0.0, ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class RootCauseAnalysis(BaseModel):
    """根因分析。"""

    pattern_id: str = ""
    root_cause: str = ""
    risk_level: str = ""
    prevention_strategy: str = ""
    recommended_adjustment: str = ""


class FailurePreventionReference(BaseModel):
    """规划预防参考(供 PlanningOptimizer 输入)。"""

    avoid_tasks: list[str] = Field(default_factory=list)
    risk_warnings: list[str] = Field(default_factory=list)
    recovery_points: list[str] = Field(default_factory=list)
    prevention_notes: list[str] = Field(default_factory=list)
    summary: str = ""
