"""Structured, sanitized evaluation models for Phase 13-P."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from maple_agent.context_reasoning.models import ContextType, TemporalState
from maple_agent.game_state.models import SemanticGameState


class EvaluationCase(BaseModel):
    """One semantic fixture case; it contains no raw perception payload."""

    case_id: str
    input_reference: str
    description: str
    expected_context: ContextType
    expected_active: bool
    expected_uncertainty: bool
    semantic_state: SemanticGameState
    temporal_state: TemporalState | None = None
    input_confidences: list[float] = Field(default_factory=list)
    relation_confidence_threshold: float | None = Field(default=None, ge=0, le=1)
    expects_conflict_preservation: bool = False
    expects_expired_exclusion: bool = False
    expects_historical_reference: bool = False


class EvaluationResult(BaseModel):
    """Legacy agent-loop evaluation result kept for compatibility."""

    evaluation_id: str = ""
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
    """Legacy aggregate metrics used by the agent loop."""

    decision_accuracy: float = Field(default=0.0, ge=0, le=1)
    plan_valid_rate: float = Field(default=0.0, ge=0, le=1)
    execution_success_rate: float = Field(default=0.0, ge=0, le=1)
    reflection_accuracy: float = Field(default=0.0, ge=0, le=1)
    experience_hit_rate: float = Field(default=0.0, ge=0, le=1)
    replan_rate: float = Field(default=0.0, ge=0, le=1)
    average_confidence: float = Field(default=0.0, ge=0, le=1)
    overall_score: float = Field(default=0.0, ge=0, le=1)


class ContextEvaluationResult(BaseModel):
    """Auditable comparison between expected and actual semantic context."""

    case_id: str
    input_reference: str
    expected_context: ContextType
    actual_context: ContextType
    expected_active: bool
    actual_active: bool
    expected_uncertainty: bool
    actual_uncertainty: bool
    confidence: float = Field(ge=0, le=1)
    input_min_confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_bound_violations: int = Field(default=0, ge=0)
    uncertainty: list[str] = Field(default_factory=list)
    passed: bool
    failure_reason: str = ""


class EvaluationMetrics(BaseModel):
    """Metrics with explicit denominators; empty denominators stay unknown."""

    denominator_status: str = "INSUFFICIENT_DATA"
    denominators: dict[str, int] = Field(default_factory=dict)
    context_accuracy: float | None = Field(default=None, ge=0, le=1)
    unknown_preservation_rate: float | None = Field(default=None, ge=0, le=1)
    conflict_preservation_rate: float | None = Field(default=None, ge=0, le=1)
    false_promotion_rate: float | None = Field(default=None, ge=0, le=1)
    expired_exclusion_rate: float | None = Field(default=None, ge=0, le=1)
    lost_handling_accuracy: float | None = Field(default=None, ge=0, le=1)
    confidence_bound_violation_count: int = Field(default=0, ge=0)


class EvaluationReport(BaseModel):
    """Sanitized report for the semantic quality gate."""

    report_id: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    dataset_reference: str
    results: list[ContextEvaluationResult] = Field(default_factory=list)
    metrics: EvaluationMetrics
    sanitized: bool = True
