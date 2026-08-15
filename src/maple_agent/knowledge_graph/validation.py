"""Deterministic validation for the existing relationship-aware graph."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from maple_agent.knowledge_graph.models import RelationType

VALID_ENTITY_TYPES = {
    "map",
    "npc",
    "monster",
    "item",
    "equipment",
    "quest",
    "story_lore",
}
VALID_RELATION_TYPES = {relation.value for relation in RelationType}
REQUIRED_RELATION_PROVENANCE = (
    "source_id",
    "source_type",
    "game_profile",
    "server_profile",
    "data_version",
)


class RelationValidationResult(BaseModel):
    """Machine-readable relationship integrity result."""

    valid: bool = False
    edge_count: int = 0
    duplicate_edge_count: int = 0
    dangling_reference_count: int = 0
    invalid_entity_type_count: int = 0
    invalid_relation_type_count: int = 0
    invalid_endpoint_count: int = 0
    missing_provenance_count: int = 0
    invalid_confidence_count: int = 0
    errors: list[str] = Field(default_factory=list)


def validate_relation_records(
    records: list[dict[str, Any]],
    known_ids: dict[str, set[str]],
) -> RelationValidationResult:
    """Validate raw records before the generic importer can discard them."""
    errors: list[str] = []
    duplicate_edges = 0
    dangling = 0
    invalid_entity_types = 0
    invalid_relation_types = 0
    invalid_endpoints = 0
    missing_provenance = 0
    invalid_confidence = 0
    seen_edges: set[tuple[str, str, str, str, str]] = set()

    for index, record in enumerate(records):
        source = str(record.get("source", "")).strip().lower()
        target = str(record.get("target", "")).strip().lower()
        source_id = str(record.get("source_id", ""))
        target_id = str(record.get("target_id", ""))
        relation_type = str(record.get("relation_type", "")).strip().upper()
        edge_key = (source, source_id, target, target_id, relation_type)
        if edge_key in seen_edges:
            duplicate_edges += 1
            errors.append(f"duplicate edge at index {index}: {edge_key}")
        seen_edges.add(edge_key)

        if source not in VALID_ENTITY_TYPES or target not in VALID_ENTITY_TYPES:
            invalid_entity_types += 1
            errors.append(f"invalid entity type at index {index}")
        if relation_type not in VALID_RELATION_TYPES:
            invalid_relation_types += 1
            errors.append(f"invalid relation type at index {index}")

        if source not in known_ids or source_id not in known_ids.get(source, set()):
            dangling += 1
        if target not in known_ids or target_id not in known_ids.get(target, set()):
            dangling += 1

        allowed_endpoint = {
            "CONTAINS": {("map", "npc"), ("map", "monster")},
            "GIVES": {("npc", "quest")},
            "REQUIRES": {("quest", "item")},
            "DROPS": {("monster", "item")},
            "REWARDS": {("quest", "item")},
            "REWARD": {("quest", "item")},
            "LOCATED_AT": {("npc", "map"), ("monster", "map")},
            "SPAWNS": {("map", "monster")},
            "CONNECTED_TO": {("map", "map")},
        }
        if relation_type in allowed_endpoint and (
            source,
            target,
        ) not in allowed_endpoint[relation_type]:
            invalid_endpoints += 1
            errors.append(f"invalid relation endpoint at index {index}")

        provenance = record.get("provenance") or {}
        if not all(provenance.get(field) for field in REQUIRED_RELATION_PROVENANCE):
            missing_provenance += 1
            errors.append(f"missing relation provenance at index {index}")

        confidence = record.get("confidence", 0.0)
        if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
            invalid_confidence += 1
            errors.append(f"invalid relation confidence at index {index}")

    return RelationValidationResult(
        valid=not errors,
        edge_count=len(records),
        duplicate_edge_count=duplicate_edges,
        dangling_reference_count=dangling,
        invalid_entity_type_count=invalid_entity_types,
        invalid_relation_type_count=invalid_relation_types,
        invalid_endpoint_count=invalid_endpoints,
        missing_provenance_count=missing_provenance,
        invalid_confidence_count=invalid_confidence,
        errors=list(dict.fromkeys(errors)),
    )


class KnowledgeGraphValidator:
    """Validate relations already held by the existing KnowledgeGraph."""

    def validate(self, graph) -> RelationValidationResult:
        known_ids = {
            "map": {str(node.map_id) for node in graph.maps},
            "npc": {str(node.npc_id) for node in graph.npcs},
            "monster": {str(node.monster_id) for node in graph.monsters},
            "item": {str(node.item_id) for node in graph.items},
            "equipment": {str(node.equipment_id) for node in graph.equipment},
            "quest": {str(node.quest_id) for node in graph.quests},
            "story_lore": {str(node.lore_id) for node in graph.story_lore},
        }
        records = [relation.model_dump(mode="json") for relation in graph.all_relations()]
        return validate_relation_records(records, known_ids)
