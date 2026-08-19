"""Read-only information references for Phase 13-Q."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from maple_agent.context_reasoning.models import (
    ContextEntityReference,
    ContextRelationReference,
    ContextUnderstanding,
    TemporalState,
)
from maple_agent.game_state.models import SemanticGameState


class PlanningReferenceType(StrEnum):
    """Information categories, never commands or action types."""

    QUEST_CONTEXT = "QUEST_CONTEXT"
    MISSING_REQUIREMENT = "MISSING_REQUIREMENT"
    KNOWN_LOCATION = "KNOWN_LOCATION"
    RELATED_ENTITY = "RELATED_ENTITY"
    INFORMATION_GAP = "INFORMATION_GAP"
    CONFLICT_NOTICE = "CONFLICT_NOTICE"


class PlanningReference(BaseModel):
    """A trustworthy fact or uncertainty for human review."""

    reference_id: str
    reference_type: PlanningReferenceType
    title: str
    description: str
    supporting_entities: list[ContextEntityReference] = Field(
        default_factory=list
    )
    supporting_relations: list[ContextRelationReference] = Field(
        default_factory=list
    )
    source_state_id: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    reasoning_summary: str


class PlanningReferenceCase(BaseModel):
    """Sanitized semantic input and expected information category."""

    case_id: str
    description: str
    expected_reference_types: list[PlanningReferenceType]
    semantic_state: SemanticGameState
    temporal_state: TemporalState | None = None
    context_understanding: ContextUnderstanding
    knowledge_graph: Any = Field(exclude=True)


class PlanningReferenceEvaluationResult(BaseModel):
    """Comparison between expected information references and generated ones."""

    case_id: str
    expected_reference_types: list[PlanningReferenceType]
    actual_reference_types: list[PlanningReferenceType]
    reference_count: int = Field(ge=0)
    confidence_bound_violations: int = Field(default=0, ge=0)
    action_leakage_count: int = Field(default=0, ge=0)
    uncertainties_preserved: bool
    expired_entities_excluded: bool
    passed: bool
    failure_reason: str = ""


class PlanningReferenceMetrics(BaseModel):
    """Benchmark metrics with explicit denominators."""

    denominator_status: str = "INSUFFICIENT_DATA"
    denominators: dict[str, int] = Field(default_factory=dict)
    reference_accuracy: float | None = Field(default=None, ge=0, le=1)
    uncertainty_preservation_rate: float | None = Field(
        default=None, ge=0, le=1
    )
    confidence_bound_violation_count: int = Field(default=0, ge=0)
    action_leakage_count: int = Field(default=0, ge=0)


class PlanningReferenceEvaluationReport(BaseModel):
    """Sanitized Phase 13-Q benchmark report."""

    report_id: str
    dataset_reference: str
    results: list[PlanningReferenceEvaluationResult] = Field(
        default_factory=list
    )
    metrics: PlanningReferenceMetrics
    sanitized: bool = True
