"""Sanitized, human-readable models for the Phase 13-R loop."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.context_reasoning.models import (
    ContextUnderstanding,
    TemporalState,
)
from maple_agent.game_state.models import (
    EntityLifecycle,
)
from maple_agent.planning_reference.models import PlanningReference


class SourceProvenanceSummary(BaseModel):
    """Path-free provenance summary retained by a public snapshot."""

    source_id: str
    source_type: str
    game_profile: str
    server_profile: str
    data_version: str
    dataset_reference: str
    source_reference: str = ""
    content_hash: str = ""


class CompanionEntitySummary(BaseModel):
    """Path-free entity projection used by the public snapshot."""

    canonical_id: str
    entity_type: str
    display_name: str
    lifecycle: EntityLifecycle
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""


class SemanticStateSummary(BaseModel):
    """Semantic state projection without raw evidence payloads."""

    state_id: str
    observation_id: str
    timestamp: datetime
    location: CompanionEntitySummary | None = None
    nearby_entities: list[CompanionEntitySummary] = Field(
        default_factory=list
    )
    quest_context: list[CompanionEntitySummary] = Field(
        default_factory=list
    )
    inventory_references: list[CompanionEntitySummary] = Field(
        default_factory=list
    )
    unknown_count: int = Field(default=0, ge=0)
    unresolved_evidence_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    history_size: int = Field(default=0, ge=0)
    confidence: float = Field(default=0.0, ge=0, le=1)


class TemporalSummary(BaseModel):
    """Lifecycle summary derived from existing Phase 13-K state."""

    state_id: str
    history_size: int = Field(default=0, ge=0)
    lifecycle_by_entity: dict[str, EntityLifecycle] = Field(
        default_factory=dict
    )
    stale_evidence_count: int = Field(default=0, ge=0)
    conflict_evidence_count: int = Field(default=0, ge=0)

    @classmethod
    def from_temporal_state(cls, temporal: TemporalState) -> TemporalSummary:
        return cls(
            state_id=temporal.state_id,
            history_size=temporal.history_size,
            lifecycle_by_entity=temporal.lifecycle_by_entity,
            stale_evidence_count=temporal.stale_evidence_count,
            conflict_evidence_count=temporal.conflict_evidence_count,
        )


class CompanionSnapshot(BaseModel):
    """The read-only current companion state; no raw evidence or action fields."""

    snapshot_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    observation_id: str
    semantic_state: SemanticStateSummary
    temporal_summary: TemporalSummary
    context_understanding: ContextUnderstanding
    planning_references: list[PlanningReference] = Field(default_factory=list)
    information_gaps: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    data_quality_notes: list[str] = Field(default_factory=list)
    readiness_notes: list[str] = Field(default_factory=list)
    source_provenance: SourceProvenanceSummary


class CompanionSession(BaseModel):
    """Path-free session summary; raw observations stay in the in-memory reducer only."""

    session_id: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    current_snapshot: CompanionSnapshot | None = None
    snapshot_count: int = Field(default=0, ge=0)
    history_reference_ids: list[str] = Field(default_factory=list)
    quality_status: str = "FOUNDATION_ONLY"


class FailureCategory(StrEnum):
    """Integration failure taxonomy, never an execution taxonomy."""

    RESOLUTION_FAILURE = "RESOLUTION_FAILURE"
    SEMANTIC_STATE_FAILURE = "SEMANTIC_STATE_FAILURE"
    TEMPORAL_CONTINUITY_FAILURE = "TEMPORAL_CONTINUITY_FAILURE"
    CONTEXT_FAILURE = "CONTEXT_FAILURE"
    REFERENCE_FAILURE = "REFERENCE_FAILURE"
    PROVENANCE_MISSING = "PROVENANCE_MISSING"
    CONFIDENCE_VIOLATION = "CONFIDENCE_VIOLATION"
    ACTION_SEMANTIC_LEAKAGE = "ACTION_SEMANTIC_LEAKAGE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    UNKNOWN = "UNKNOWN"
