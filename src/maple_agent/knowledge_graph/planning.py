"""Read-only planning reference context built from semantic state and graph."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field

from maple_agent.knowledge_graph.models import (
    KnowledgeEntityProvenance,
    RelationType,
)

if TYPE_CHECKING:
    from maple_agent.game_state.models import SemanticGameState


class PlanningReference(BaseModel):
    """A knowledge fact available for later human-reviewed planning."""

    entity_type: str
    entity_id: int | str
    name: str
    relation_type: RelationType
    confidence: float = Field(default=0.0, ge=0, le=1)
    provenance: KnowledgeEntityProvenance = Field(
        default_factory=KnowledgeEntityProvenance
    )


class PlanningContext(BaseModel):
    """Semantic context only; it contains no action or execution fields."""

    current_semantic_state: Any = None
    relevant_knowledge: list[PlanningReference] = Field(default_factory=list)
    possible_references: dict[str, list[PlanningReference]] = Field(
        default_factory=lambda: {
            "npcs": [],
            "items": [],
            "maps": [],
            "quests": [],
        }
    )
    reasoning: list[str] = Field(default_factory=list)

    @classmethod
    def from_state(cls, graph, state: SemanticGameState) -> PlanningContext:
        """Build deterministic references from the current semantic state."""
        grouped: dict[str, list[PlanningReference]] = {
            "npcs": [],
            "items": [],
            "maps": [],
            "quests": [],
        }
        seen: set[tuple[str, str, str]] = set()
        state_references = [
            reference
            for reference in [
                state.location,
                *state.nearby_entities,
                *state.quest_context,
                *state.inventory_references,
            ]
            if reference is not None and reference.canonical_id
        ]
        for state_reference in state_references:
            entity_type, entity_id = _split_reference(
                state_reference.entity_type,
                state_reference.canonical_id,
            )
            for reference in graph.relation_references_for(entity_type, entity_id):
                key = (
                    reference.entity_type,
                    str(reference.entity_id),
                    reference.relation_type.value,
                )
                group = f"{reference.entity_type}s"
                if group not in grouped or key in seen:
                    continue
                seen.add(key)
                grouped[group].append(
                    PlanningReference.model_validate(reference.model_dump())
                )
        relevant = [reference for values in grouped.values() for reference in values]
        return cls(
            current_semantic_state=state,
            relevant_knowledge=relevant,
            possible_references=grouped,
            reasoning=[
                f"semantic references={len(state_references)}",
                f"related references={len(relevant)}",
                "read-only planning reference; no action or execution proposed",
            ],
        )


def _split_reference(entity_type: str, canonical_id: str) -> tuple[str, str]:
    normalized_type = entity_type.strip().lower()
    prefix = f"{normalized_type}_"
    if canonical_id.startswith(prefix):
        return normalized_type, canonical_id[len(prefix) :]
    return normalized_type, canonical_id
