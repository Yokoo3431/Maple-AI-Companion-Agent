"""Read-only context understanding models for Phase 13-O."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.game_state.models import EntityLifecycle, SemanticGameState
from maple_agent.knowledge_graph.models import (
    KnowledgeEntityProvenance,
    RelationType,
)


class ContextType(StrEnum):
    """Descriptive context labels; none is an action or command."""

    QUEST_RELATED_CONTEXT = "QUEST_RELATED_CONTEXT"
    ITEM_QUEST_CONTEXT = "ITEM_QUEST_CONTEXT"
    LOCATION_CONTEXT = "LOCATION_CONTEXT"
    NPC_RELATED_CONTEXT = "NPC_RELATED_CONTEXT"
    ITEM_RELATED_CONTEXT = "ITEM_RELATED_CONTEXT"
    EXPLORATION_CONTEXT = "EXPLORATION_CONTEXT"
    UNKNOWN_CONTEXT = "UNKNOWN_CONTEXT"


class TemporalState(BaseModel):
    """Read-only lifecycle view derived from Phase 13-K semantic state."""

    state_id: str
    timestamp: datetime
    history_size: int = Field(default=0, ge=0)
    lifecycle_by_entity: dict[str, EntityLifecycle] = Field(default_factory=dict)
    stale_evidence_count: int = Field(default=0, ge=0)
    conflict_evidence_count: int = Field(default=0, ge=0)

    @classmethod
    def from_semantic_state(cls, state: SemanticGameState) -> TemporalState:
        references = [
            reference
            for reference in [
                state.location,
                *state.nearby_entities,
                *state.quest_context,
                *state.inventory_references,
                *state.unknown_references,
            ]
            if reference is not None and reference.canonical_id
        ]
        return cls(
            state_id=state.state_id,
            timestamp=state.timestamp,
            history_size=state.history_size,
            lifecycle_by_entity={
                reference.canonical_id: reference.lifecycle
                for reference in references
            },
            stale_evidence_count=len(state.stale_evidence_ids),
            conflict_evidence_count=len(state.conflict_evidence_ids),
        )

    def lifecycle_for(
        self,
        canonical_id: str,
        fallback: EntityLifecycle = EntityLifecycle.UNKNOWN,
    ) -> EntityLifecycle:
        return self.lifecycle_by_entity.get(canonical_id, fallback)


class ContextEntityReference(BaseModel):
    """Entity retained in a context interpretation."""

    canonical_id: str
    entity_type: str
    display_name: str
    lifecycle: EntityLifecycle
    confidence: float = Field(default=0.0, ge=0, le=1)
    resolution_confidence: float = Field(default=0.0, ge=0, le=1)
    relation_confidence: float | None = Field(default=None, ge=0, le=1)
    provenance: KnowledgeEntityProvenance = Field(
        default_factory=KnowledgeEntityProvenance
    )
    historical_only: bool = False


class ContextRelationReference(BaseModel):
    """A graph edge used by a context interpretation."""

    source_type: str
    source_id: int | str
    target_type: str
    target_id: int | str
    relation_type: RelationType
    confidence: float = Field(default=0.0, ge=0, le=1)
    provenance: KnowledgeEntityProvenance = Field(
        default_factory=KnowledgeEntityProvenance
    )


class ContextUnderstanding(BaseModel):
    """Final read-only semantic interpretation of the current context."""

    context_id: str
    timestamp: datetime
    semantic_state_reference: str
    related_entities: list[ContextEntityReference] = Field(default_factory=list)
    related_relations: list[ContextRelationReference] = Field(default_factory=list)
    context_type: ContextType
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning_trace: list[str] = Field(default_factory=list)
    uncertainties: list[str] = Field(default_factory=list)
