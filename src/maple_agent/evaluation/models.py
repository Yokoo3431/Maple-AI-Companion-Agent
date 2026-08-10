"""Agent Evaluation 数据模型(Phase 5-F,只读评估,不改变 Agent 行为)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class EvaluationCase(BaseModel):
    """单个评估用例。"""

    case_id: str
    trace_id: str = ""
    goal: str = ""
    expected_behavior: str = ""
    actual_behavior: str = ""
    source: str = ""


class EvaluationResult(BaseModel):
    """单个 trace 的评估结果。"""

    evaluation_id: str
    trace_id: str = ""
    decision_score: float = Field(default=0.0, ge=0, le=1)
    planning_score: float = Field(default=0.0, ge=0, le=1)
    execution_score: float = Field(default=0.0, ge=0, le=1)
    reflection_score: float = Field(default=0.0, ge=0, le=1)
    memory_score: float = Field(default=0.0, ge=0, le=1)
    overall_score: float = Field(default=0.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


class AgentMetrics(BaseModel):
    """跨 trace 的 Agent 质量指标。"""

    decision_accuracy: float = Field(default=0.0, ge=0, le=1)
    plan_valid_rate: float = Field(default=0.0, ge=0, le=1)
    execution_success_rate: float = Field(default=0.0, ge=0, le=1)
    reflection_accuracy: float = Field(default=0.0, ge=0, le=1)
    experience_hit_rate: float = Field(default=0.0, ge=0, le=1)
    replan_rate: float = Field(default=0.0, ge=0, le=1)
    average_confidence: float = Field(default=0.0, ge=0, le=1)
    overall_score: float = Field(default=0.0, ge=0, le=1)
