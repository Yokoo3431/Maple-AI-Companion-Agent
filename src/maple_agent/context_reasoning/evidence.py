"""Evidence-preserving helpers for context reasoning."""

from __future__ import annotations

from typing import Any

from maple_agent.context_reasoning.models import TemporalState
from maple_agent.game_state.models import (
    EntityLifecycle,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.knowledge_graph.models import KnowledgeEntityProvenance


def semantic_references(state: SemanticGameState) -> list[SemanticEntityReference]:
    """Return state references without mutating or inferring missing entities."""
    return [
        reference
        for reference in [
            state.location,
            *state.nearby_entities,
            *state.quest_context,
            *state.inventory_references,
            *state.unknown_references,
        ]
        if reference is not None
    ]


def split_reference(reference: SemanticEntityReference) -> tuple[str, str]:
    """Normalize a semantic reference such as ``npc_100`` to graph keys."""
    entity_type = reference.entity_type.strip().lower()
    canonical_id = reference.canonical_id
    prefix = f"{entity_type}_"
    if canonical_id.startswith(prefix):
        canonical_id = canonical_id[len(prefix) :]
    return entity_type, canonical_id


def effective_lifecycle(
    reference: SemanticEntityReference,
    temporal_state: TemporalState,
) -> EntityLifecycle:
    return temporal_state.lifecycle_for(reference.canonical_id, reference.lifecycle)


def resolution_confidence(state: SemanticGameState, canonical_id: str) -> float:
    values = [
        candidate.resolution_confidence
        for candidate in state.resolution_candidates
        if candidate.canonical_id == canonical_id
    ]
    return max(values, default=0.0)


def graph_node(graph: Any, entity_type: str, entity_id: int | str) -> Any:
    finders = {
        "map": graph.find_map,
        "npc": graph.find_npc,
        "monster": graph.find_monster,
        "item": graph.find_item,
        "equipment": graph.find_equipment,
        "quest": graph.find_quest,
        "story_lore": graph.find_story_lore,
    }
    finder = finders.get(entity_type)
    return finder(entity_id) if finder else None


def node_provenance(node: Any) -> KnowledgeEntityProvenance:
    return getattr(node, "provenance", KnowledgeEntityProvenance())
