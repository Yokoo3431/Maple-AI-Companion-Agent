"""Deterministic, read-only semantic context reasoning."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from maple_agent.context_reasoning.evidence import (
    effective_lifecycle,
    graph_node,
    node_provenance,
    resolution_confidence,
    semantic_references,
    split_reference,
)
from maple_agent.context_reasoning.models import (
    ContextEntityReference,
    ContextRelationReference,
    ContextType,
    ContextUnderstanding,
    TemporalState,
)
from maple_agent.context_reasoning.rules import (
    ACTIVE_LIFECYCLE,
    DEFAULT_RELATION_CONFIDENCE_THRESHOLD,
    ITEM_TYPES,
    LOCATION_TYPES,
    NPC_TYPES,
    QUEST_TYPES,
)
from maple_agent.game_state.models import (
    EntityLifecycle,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.knowledge_graph.models import Relation, RelationType


@dataclass
class _Candidate:
    context_type: ContextType
    related_entities: list[ContextEntityReference] = field(default_factory=list)
    related_relations: list[ContextRelationReference] = field(default_factory=list)
    confidence_values: list[float] = field(default_factory=list)
    reasoning: list[str] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)


class ContextReasoner:
    """Interpret a semantic state against the existing validated graph."""

    def __init__(
        self,
        graph: Any,
        *,
        relation_confidence_threshold: float = DEFAULT_RELATION_CONFIDENCE_THRESHOLD,
    ) -> None:
        if not 0 <= relation_confidence_threshold <= 1:
            raise ValueError("relation confidence threshold must be between 0 and 1")
        self.graph = graph
        self.relation_confidence_threshold = relation_confidence_threshold

    def reason(
        self,
        semantic_state: SemanticGameState,
        temporal_state: TemporalState | None = None,
    ) -> ContextUnderstanding:
        """Return one deterministic context interpretation."""
        temporal = temporal_state or TemporalState.from_semantic_state(semantic_state)
        references = semantic_references(semantic_state)
        normalized = [
            (reference, *split_reference(reference))
            for reference in references
            if reference.canonical_id
        ]
        active = [
            item
            for item in normalized
            if effective_lifecycle(item[0], temporal) is ACTIVE_LIFECYCLE
        ]
        lost = [
            item
            for item in normalized
            if effective_lifecycle(item[0], temporal) is EntityLifecycle.LOST
        ]
        expired = [
            item
            for item in normalized
            if effective_lifecycle(item[0], temporal) is EntityLifecycle.EXPIRED
        ]
        unknown = [
            reference
            for reference in semantic_state.unknown_references
            if not reference.canonical_id
            or effective_lifecycle(reference, temporal) is EntityLifecycle.UNKNOWN
        ]
        base_uncertainties: list[str] = []
        base_uncertainties.extend(
            f"relation {relation.relation_type.value} "
            f"{relation.source_id}->{relation.target_id} below confidence threshold"
            for relation in self.graph.all_relations()
            if relation.confidence < self.relation_confidence_threshold
        )
        if lost:
            base_uncertainties.append("lost references retained as historical context only")
        if expired:
            base_uncertainties.append("expired references excluded from current context")
        if unknown:
            base_uncertainties.append("unknown references remain unresolved")
        if semantic_state.conflict_evidence_ids:
            base_uncertainties.append("semantic state contains conflicting evidence")
        if temporal.state_id != semantic_state.state_id:
            base_uncertainties.append("temporal state does not match semantic state")

        candidates = [
            self._quest_candidate(semantic_state, temporal, active),
            self._item_quest_candidate(semantic_state, temporal, active),
        ]
        candidates = [candidate for candidate in candidates if candidate is not None]
        if candidates:
            candidate = self._select_candidate(candidates)
        else:
            candidate = self._fallback_candidate(semantic_state, temporal, active, unknown)

        candidate.uncertainties = list(dict.fromkeys(base_uncertainties + candidate.uncertainties))
        candidate.related_entities.extend(
            self._state_entity_reference(
                semantic_state,
                temporal,
                reference,
                entity_type,
                entity_id,
                historical_only=True,
            )
            for reference, entity_type, entity_id in lost
        )
        candidate.related_entities.extend(
            ContextEntityReference(
                canonical_id=reference.canonical_id,
                entity_type=reference.entity_type.strip().lower(),
                display_name=reference.display_name or "UNKNOWN",
                lifecycle=EntityLifecycle.UNKNOWN,
                confidence=reference.confidence,
                resolution_confidence=resolution_confidence(
                    semantic_state, reference.canonical_id
                ),
                historical_only=False,
            )
            for reference in unknown
        )
        candidate.related_entities = self._dedupe_entities(candidate.related_entities)
        candidate.related_relations = self._dedupe_relations(candidate.related_relations)
        return ContextUnderstanding(
            context_id=f"context-{semantic_state.state_id}",
            timestamp=temporal.timestamp,
            semantic_state_reference=semantic_state.state_id,
            related_entities=candidate.related_entities,
            related_relations=candidate.related_relations,
            context_type=candidate.context_type,
            confidence=self._confidence(
                semantic_state.confidence,
                candidate.confidence_values,
            ),
            reasoning_trace=list(dict.fromkeys(candidate.reasoning)),
            uncertainties=candidate.uncertainties,
        )

    def _quest_candidate(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        active: list[tuple[SemanticEntityReference, str, str]],
    ) -> _Candidate | None:
        locations = [item for item in active if item[1] in LOCATION_TYPES]
        npcs = [item for item in active if item[1] in NPC_TYPES]
        if not locations or not npcs:
            return None
        contains = [
            relation
            for relation in self.graph.all_relations()
            if relation.relation_type is RelationType.CONTAINS
            and relation.source.strip().lower() == "map"
            and relation.target.strip().lower() == "npc"
            and any(self._matches(item, "map", relation.source_id) for item in locations)
            and any(self._matches(item, "npc", relation.target_id) for item in npcs)
        ]
        candidate = _Candidate(
            context_type=ContextType.QUEST_RELATED_CONTEXT,
            reasoning=["visible location and NPC matched the graph context rule"],
        )
        valid_contains = self._accepted_relations(contains, candidate)
        if not valid_contains:
            return None
        quests: list[Relation] = []
        for contains_relation in valid_contains:
            quests.extend(
                relation
                for relation in self.graph.all_relations()
                if relation.relation_type is RelationType.GIVES
                and relation.source.strip().lower() == "npc"
                and relation.target.strip().lower() == "quest"
                and str(relation.source_id) == str(contains_relation.target_id)
            )
        valid_quests = self._accepted_relations(quests, candidate)
        if not valid_quests:
            return None
        if len({str(relation.target_id) for relation in valid_quests}) > 1:
            candidate.uncertainties.append("multiple quest relation candidates remain")
        candidate.related_relations = [
            *[self._relation_reference(relation) for relation in valid_contains],
            *[self._relation_reference(relation) for relation in valid_quests],
        ]
        candidate.related_entities = [
            self._state_entity_reference(
                state, temporal, item[0], item[1], item[2]
            )
            for item in [*locations, *npcs]
        ]
        candidate.related_entities.extend(
            self._graph_entity_reference(
                "quest", relation.target_id, relation.confidence
            )
            for relation in valid_quests
        )
        candidate.confidence_values.extend(
            relation.confidence for relation in [*valid_contains, *valid_quests]
        )
        candidate.confidence_values.extend(item[0].confidence for item in [*locations, *npcs])
        candidate.confidence_values.extend(
            getattr(self.graph.find_quest(relation.target_id), "confidence", 0.0)
            for relation in valid_quests
        )
        candidate.reasoning.append("NPC gives at least one validated quest relation")
        return candidate

    def _item_quest_candidate(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        active: list[tuple[SemanticEntityReference, str, str]],
    ) -> _Candidate | None:
        quests = [item for item in active if item[1] in QUEST_TYPES]
        items = [item for item in active if item[1] in ITEM_TYPES]
        if not quests or not items:
            return None
        relations = [
            relation
            for relation in self.graph.all_relations()
            if relation.relation_type is RelationType.REQUIRES
            and relation.source.strip().lower() == "quest"
            and relation.target.strip().lower() == "item"
            and any(self._matches(item, "quest", relation.source_id) for item in quests)
            and any(self._matches(item, "item", relation.target_id) for item in items)
        ]
        candidate = _Candidate(
            context_type=ContextType.ITEM_QUEST_CONTEXT,
            reasoning=["visible quest and inventory item matched the requirement rule"],
        )
        valid_relations = self._accepted_relations(relations, candidate)
        if not valid_relations:
            return None
        candidate.related_relations = [
            self._relation_reference(relation) for relation in valid_relations
        ]
        candidate.related_entities = [
            self._state_entity_reference(
                state, temporal, item[0], item[1], item[2]
            )
            for item in [*quests, *items]
        ]
        candidate.confidence_values.extend(
            relation.confidence for relation in valid_relations
        )
        candidate.confidence_values.extend(item[0].confidence for item in [*quests, *items])
        return candidate

    def _fallback_candidate(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        active: list[tuple[SemanticEntityReference, str, str]],
        unknown: list[SemanticEntityReference],
    ) -> _Candidate:
        if not active:
            return _Candidate(
                context_type=ContextType.UNKNOWN_CONTEXT,
                related_entities=[],
                confidence_values=[state.confidence],
                reasoning=["no visible semantic reference supports an active context"],
                uncertainties=[
                    "no active context promoted",
                    *("unknown semantic reference retained" for _ in unknown),
                ],
            )
        entities = [
            self._state_entity_reference(
                state, temporal, reference, entity_type, entity_id
            )
            for reference, entity_type, entity_id in active
        ]
        entity_types = {entity_type for _, entity_type, _ in active}
        if entity_types & LOCATION_TYPES:
            context_type = ContextType.LOCATION_CONTEXT
        elif entity_types & NPC_TYPES:
            context_type = ContextType.NPC_RELATED_CONTEXT
        elif entity_types & ITEM_TYPES:
            context_type = ContextType.ITEM_RELATED_CONTEXT
        else:
            context_type = ContextType.EXPLORATION_CONTEXT
        return _Candidate(
            context_type=context_type,
            related_entities=entities,
            confidence_values=[reference.confidence for reference, _, _ in active],
            reasoning=["visible semantic references provide descriptive context only"],
        )

    def _accepted_relations(
        self,
        relations: list[Relation],
        candidate: _Candidate,
    ) -> list[Relation]:
        accepted: list[Relation] = []
        for relation in relations:
            if relation.confidence < self.relation_confidence_threshold:
                candidate.uncertainties.append(
                    f"relation {relation.relation_type.value} "
                    f"{relation.source_id}->{relation.target_id} below confidence threshold"
                )
                continue
            accepted.append(relation)
        if len(relations) > len(accepted) and not accepted:
            candidate.uncertainties.append("all matching relations remain uncertain")
        if len(accepted) > 1:
            keys = {
                (
                    relation.source,
                    str(relation.source_id),
                    relation.target,
                    str(relation.target_id),
                    relation.relation_type.value,
                )
                for relation in accepted
            }
            if len(keys) < len(accepted):
                candidate.uncertainties.append("duplicate relation evidence remains unresolved")
        return accepted

    def _state_entity_reference(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        reference: SemanticEntityReference,
        entity_type: str,
        entity_id: str,
        *,
        historical_only: bool = False,
        relation_confidence: float | None = None,
    ) -> ContextEntityReference:
        graph_entity_type = self._graph_type(entity_type)
        node = graph_node(self.graph, graph_entity_type, entity_id)
        lifecycle = effective_lifecycle(reference, temporal)
        return ContextEntityReference(
            canonical_id=reference.canonical_id,
            entity_type=graph_entity_type,
            display_name=reference.display_name,
            lifecycle=lifecycle,
            confidence=reference.confidence,
            resolution_confidence=resolution_confidence(
                state, reference.canonical_id
            )
            or reference.confidence,
            relation_confidence=relation_confidence,
            provenance=node_provenance(node),
            historical_only=historical_only,
        )

    def _graph_entity_reference(
        self,
        entity_type: str,
        entity_id: int | str,
        relation_confidence: float,
    ) -> ContextEntityReference:
        node = graph_node(self.graph, entity_type, entity_id)
        canonical_id = str(entity_id)
        if not canonical_id.startswith(f"{entity_type}_"):
            canonical_id = f"{entity_type}_{canonical_id}"
        return ContextEntityReference(
            canonical_id=canonical_id,
            entity_type=entity_type,
            display_name=getattr(node, "name", "UNKNOWN"),
            lifecycle=EntityLifecycle.UNKNOWN,
            confidence=getattr(node, "confidence", 0.0),
            resolution_confidence=0.0,
            relation_confidence=relation_confidence,
            provenance=node_provenance(node),
        )

    @staticmethod
    def _relation_reference(relation: Relation) -> ContextRelationReference:
        return ContextRelationReference(
            source_type=relation.source,
            source_id=relation.source_id,
            target_type=relation.target,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            confidence=relation.confidence,
            provenance=relation.provenance,
        )

    @staticmethod
    def _matches(
        item: tuple[SemanticEntityReference, str, str],
        entity_type: str,
        entity_id: int | str,
    ) -> bool:
        normalized_type = {
            "location": "map",
            "map_label": "map",
            "character": "npc",
            "quest_context": "quest",
            "inventory": "item",
            "inventory_item": "item",
        }.get(item[1], item[1])
        candidate_id = str(item[2])
        observed_id = str(entity_id)
        return normalized_type == entity_type and observed_id in {
            candidate_id,
            f"{entity_type}_{candidate_id}",
        }

    @staticmethod
    def _graph_type(entity_type: str) -> str:
        return {
            "location": "map",
            "map_label": "map",
            "character": "npc",
            "quest_context": "quest",
            "inventory": "item",
            "inventory_item": "item",
        }.get(entity_type, entity_type)

    @staticmethod
    def _confidence(state_confidence: float, values: list[float]) -> float:
        candidates = [state_confidence, *values]
        return round(min(candidates), 4) if candidates else 0.0

    @staticmethod
    def _select_candidate(candidates: list[_Candidate]) -> _Candidate:
        priority = {
            ContextType.ITEM_QUEST_CONTEXT: 0,
            ContextType.QUEST_RELATED_CONTEXT: 1,
        }
        return sorted(
            candidates,
            key=lambda candidate: priority.get(candidate.context_type, 99),
        )[0]

    @staticmethod
    def _dedupe_entities(
        entities: list[ContextEntityReference],
    ) -> list[ContextEntityReference]:
        result: list[ContextEntityReference] = []
        seen: set[tuple[str, str, bool]] = set()
        for entity in entities:
            key = (entity.entity_type, entity.canonical_id, entity.historical_only)
            if key not in seen:
                seen.add(key)
                result.append(entity)
        return result

    @staticmethod
    def _dedupe_relations(
        relations: list[ContextRelationReference],
    ) -> list[ContextRelationReference]:
        result: list[ContextRelationReference] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for relation in relations:
            key = (
                relation.source_type,
                str(relation.source_id),
                relation.target_type,
                str(relation.target_id),
                relation.relation_type.value,
            )
            if key not in seen:
                seen.add(key)
                result.append(relation)
        return result
