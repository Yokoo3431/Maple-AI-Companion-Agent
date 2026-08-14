"""Perception Evidence -> Knowledge Resolution -> Semantic Game State."""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.game_state.models import (
    CurrentObservation,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.hybrid_vision.knowledge_resolution import EvidenceResolver
from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph


class SemanticStateResolver:
    """Build a semantic, read-only state without changing observed evidence."""

    _LOCATION_TYPES = {"map", "map_label", "location"}
    _QUEST_TYPES = {"quest", "quest_context"}
    _INVENTORY_TYPES = {"item", "equipment", "inventory", "inventory_item"}

    def __init__(
        self,
        graph: MapleKnowledgeGraph,
        *,
        evidence_resolver: EvidenceResolver | None = None,
    ) -> None:
        self.graph = graph
        self.evidence_resolver = evidence_resolver or EvidenceResolver()
        self.last_state: SemanticGameState | None = None

    def resolve(self, observation: CurrentObservation) -> SemanticGameState:
        resolutions = [
            self.evidence_resolver.resolve(evidence, self.graph)
            for evidence in observation.evidence
        ]
        location: SemanticEntityReference | None = None
        nearby: list[SemanticEntityReference] = []
        quests: list[SemanticEntityReference] = []
        inventory: list[SemanticEntityReference] = []
        candidates = []
        unresolved: list[str] = []
        confidence_values: list[float] = []

        for evidence, resolution in zip(observation.evidence, resolutions):
            candidates.extend(resolution.candidates)
            if not resolution.resolved or resolution.selected is None:
                unresolved.append(evidence.evidence_id)
                continue
            selected = resolution.selected
            reference = SemanticEntityReference(
                canonical_id=selected.canonical_id,
                entity_type=selected.entity_type,
                display_name=selected.display_name,
                confidence=selected.resolution_confidence,
                evidence_ids=[evidence.evidence_id],
                source=selected.source,
                version=selected.version,
            )
            confidence_values.append(selected.resolution_confidence)
            evidence_type = evidence.evidence_type.strip().lower()
            if evidence_type in self._LOCATION_TYPES:
                location = reference
            elif evidence_type in self._QUEST_TYPES:
                quests.append(reference)
            elif evidence_type in self._INVENTORY_TYPES:
                inventory.append(reference)
            else:
                nearby.append(reference)

        state = SemanticGameState(
            state_id=new_id(),
            observation_id=observation.observation_id,
            location=location,
            player_status=observation.player_status,
            nearby_entities=nearby,
            quest_context=quests,
            inventory_references=inventory,
            resolution_candidates=candidates,
            unresolved_evidence_ids=unresolved,
            evidence=list(observation.evidence),
            confidence=(
                round(sum(confidence_values) / len(confidence_values), 4)
                if confidence_values
                else 0.0
            ),
            reasoning=[
                f"resolved={len(confidence_values)}",
                f"unresolved={len(unresolved)}",
                "observations preserved; no action planning performed",
            ],
        )
        self.last_state = state
        return state


def save_semantic_state_trace(
    sessions_dir: str | Path,
    trace_id: str,
    state: SemanticGameState,
) -> None:
    """Write a sanitized semantic replay without screenshots or private paths."""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "state": state.model_dump(mode="json"),
    }
    (directory / "semantic_game_state.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
