"""Runtime knowledge contract and cross-graph reconciliation audit."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, Field

from maple_agent.companion_runtime.models import SourceProvenanceSummary
from maple_agent.knowledge.importer.builder import build_dataset
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_quality.package import KnowledgeDatasetPackage
from maple_agent.maple_knowledge.knowledge_base import (
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
)
from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    KnowledgeRelationType,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)

AUDIT_ENTITY_TYPES = ("MAP", "NPC", "QUEST", "ITEM")
TYPE_PREFIXES = {
    "MAP": "map",
    "NPC": "npc",
    "MONSTER": "monster",
    "ITEM": "item",
    "EQUIPMENT": "equipment",
    "QUEST": "quest",
    "STORY_LORE": "story_lore",
}
ENTITY_COLLECTIONS = {
    "MAP": ("maps", "map_id"),
    "NPC": ("npcs", "npc_id"),
    "MONSTER": ("monsters", "monster_id"),
    "ITEM": ("items", "item_id"),
    "EQUIPMENT": ("equipment", "equipment_id"),
    "QUEST": ("quests", "quest_id"),
    "STORY_LORE": ("story_lore", "lore_id"),
}


class KnowledgeContractAudit(BaseModel):
    """Sanitized result of comparing the two historical graph interfaces."""

    dataset_id: str
    game_profile: str
    server_profile: str
    resolution_graph_entity_count: int = Field(ge=0)
    relationship_graph_entity_count: int = Field(ge=0)
    canonical_overlap_count: int = Field(ge=0)
    canonical_mismatch_count: int = Field(ge=0)
    missing_left_count: int = Field(ge=0)
    missing_right_count: int = Field(ge=0)
    alias_conflict_count: int = Field(ge=0)
    profile_mismatch_count: int = Field(ge=0)
    provenance_mismatch_count: int = Field(ge=0)
    version_mismatch_count: int = Field(ge=0)
    denominator_status: str = "INSUFFICIENT_DATA"
    valid: bool = False
    issues: list[str] = Field(default_factory=list)
    sanitized: bool = True


@dataclass(frozen=True)
class RuntimeKnowledgeBundle:
    """Dependency bundle; it stores references, not a third graph or facts."""

    resolution_graph: MapleKnowledgeGraph
    relationship_graph: KnowledgeGraph
    provenance: SourceProvenanceSummary
    dataset_id: str
    canonical_mapping: dict[str, str]
    audit: KnowledgeContractAudit

    @classmethod
    def from_graphs(
        cls,
        resolution_graph: MapleKnowledgeGraph,
        relationship_graph: KnowledgeGraph,
        *,
        provenance: SourceProvenanceSummary,
        dataset_id: str | None = None,
        canonical_mapping: dict[str, str] | None = None,
    ) -> RuntimeKnowledgeBundle:
        resolved_dataset_id = dataset_id or provenance.data_version
        audit = audit_graph_contract(
            resolution_graph,
            relationship_graph,
            provenance=provenance,
            dataset_id=resolved_dataset_id,
        )
        return cls(
            resolution_graph=resolution_graph,
            relationship_graph=relationship_graph,
            provenance=provenance,
            dataset_id=resolved_dataset_id,
            canonical_mapping=dict(canonical_mapping or {}),
            audit=audit,
        )

    @classmethod
    def from_dataset_package(
        cls,
        package: KnowledgeDatasetPackage,
    ) -> RuntimeKnowledgeBundle:
        """Build both historical views through the existing generic importer."""
        canonical_packet, canonical_mapping = _canonicalize_packet(package)
        dataset, _ = build_dataset(
            canonical_packet,
            source=package.manifest.source_id,
            version=package.manifest.dataset_version,
        )
        relationship_graph = KnowledgeGraph(
            maps=dataset.maps,
            npcs=dataset.npcs,
            monsters=dataset.monsters,
            items=dataset.items,
            equipment=dataset.equipment,
            quests=dataset.quests,
            story_lore=dataset.story_lore,
            relations=dataset.relations,
        )
        resolution_graph = _legacy_graph_from_modern(relationship_graph)
        provenance = SourceProvenanceSummary(
            source_id=package.manifest.source_id,
            source_type=package.manifest.source_type.value,
            game_profile=package.manifest.game_profile,
            server_profile=package.manifest.server_profile,
            data_version=package.manifest.dataset_version,
            dataset_reference=package.manifest.dataset_version,
            source_reference=package.manifest.source_reference,
            content_hash=package.manifest.content_hash,
        )
        return cls.from_graphs(
            resolution_graph,
            relationship_graph,
            provenance=provenance,
            dataset_id=package.manifest.dataset_version,
            canonical_mapping=canonical_mapping,
        )


def audit_graph_contract(
    resolution_graph: MapleKnowledgeGraph,
    relationship_graph: KnowledgeGraph,
    *,
    provenance: SourceProvenanceSummary,
    dataset_id: str,
) -> KnowledgeContractAudit:
    """Compare identity and metadata without repairing either graph."""
    left = _legacy_entities(resolution_graph)
    right = _modern_entities(relationship_graph)
    left_ids = set(left)
    right_ids = set(right)
    overlap = left_ids & right_ids
    left_missing = left_ids - right_ids
    right_missing = right_ids - left_ids
    alias_mismatches = 0
    profile_mismatches = 0
    provenance_mismatches = 0
    version_mismatches = 0
    issues: list[str] = []
    for canonical_id in sorted(overlap):
        left_item = left[canonical_id]
        right_item = right[canonical_id]
        if _normalized_aliases(left_item.get("aliases", [])) != _normalized_aliases(
            right_item.get("aliases", [])
        ):
            alias_mismatches += 1
        left_provenance = left_item.get("provenance", {})
        right_provenance = right_item.get("provenance", {})
        if (
            left_provenance.get("game_profile", "")
            != right_provenance.get("game_profile", "")
            or left_provenance.get("server_profile", "")
            != right_provenance.get("server_profile", "")
        ):
            profile_mismatches += 1
        if _provenance_key(left_provenance) != _provenance_key(right_provenance):
            provenance_mismatches += 1
        if left_item.get("version", "") != right_item.get("version", ""):
            version_mismatches += 1
    if left_missing:
        issues.append(f"missing relationship graph entities: {len(left_missing)}")
    if right_missing:
        issues.append(f"missing resolution graph entities: {len(right_missing)}")
    if alias_mismatches:
        issues.append(f"alias mismatch count: {alias_mismatches}")
    if profile_mismatches:
        issues.append(f"profile mismatch count: {profile_mismatches}")
    if provenance_mismatches:
        issues.append(f"provenance mismatch count: {provenance_mismatches}")
    if version_mismatches:
        issues.append(f"version mismatch count: {version_mismatches}")
    metadata_bound = all(
        value not in {"", "UNKNOWN", "UNBOUND"}
        for value in (
            provenance.source_id,
            provenance.game_profile,
            provenance.server_profile,
            provenance.data_version,
        )
    )
    if not metadata_bound:
        issues.append("runtime dataset metadata is UNKNOWN/UNBOUND")
    if left_missing or right_missing:
        issues.append("canonical identity sets differ; no automatic repair")
    valid = not issues
    return KnowledgeContractAudit(
        dataset_id=dataset_id,
        game_profile=provenance.game_profile,
        server_profile=provenance.server_profile,
        resolution_graph_entity_count=len(left),
        relationship_graph_entity_count=len(right),
        canonical_overlap_count=len(overlap),
        canonical_mismatch_count=len(left_missing) + len(right_missing),
        missing_left_count=len(left_missing),
        missing_right_count=len(right_missing),
        alias_conflict_count=alias_mismatches,
        profile_mismatch_count=profile_mismatches,
        provenance_mismatch_count=provenance_mismatches,
        version_mismatch_count=version_mismatches,
        denominator_status=("SUFFICIENT" if overlap else "INSUFFICIENT_DATA"),
        valid=valid,
        issues=issues,
    )


def _legacy_entities(graph: MapleKnowledgeGraph) -> dict[str, dict[str, Any]]:
    return {
        entity.knowledge_id: {
            "aliases": entity.aliases,
            "version": entity.version or entity.provenance.data_version,
            "provenance": entity.provenance.model_dump(mode="json"),
        }
        for entity in graph.all_entities()
        if entity.knowledge_type.value in AUDIT_ENTITY_TYPES
    }


def _modern_entities(graph: KnowledgeGraph) -> dict[str, dict[str, Any]]:
    nodes: dict[str, dict[str, Any]] = {}
    for entity_type, collection in (
        ("MAP", graph.maps),
        ("NPC", graph.npcs),
        ("ITEM", graph.items),
        ("QUEST", graph.quests),
    ):
        prefix = TYPE_PREFIXES[entity_type]
        for node in collection:
            entity_id = getattr(node, f"{prefix}_id", None)
            nodes[str(entity_id)] = {
                "aliases": node.aliases,
                "version": node.version or node.provenance.data_version,
                "provenance": node.provenance.model_dump(mode="json"),
            }
    return nodes


def _normalized_aliases(values: list[str]) -> set[str]:
    return {"".join(str(value).lower().split()) for value in values if value}


def _provenance_key(value: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        str(value.get(field, ""))
        for field in (
            "source_id",
            "source_type",
            "game_profile",
            "server_profile",
            "data_version",
            "snapshot_version",
            "content_hash",
        )
    )


def _canonicalize_packet(
    package: KnowledgeDatasetPackage,
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, str]]:
    packet = {
        key: [dict(item) for item in values]
        for key, values in package.packet.items()
    }
    mapping: dict[str, str] = {}
    for entity_type, (collection, id_field) in ENTITY_COLLECTIONS.items():
        prefix = TYPE_PREFIXES[entity_type]
        for item in packet.get(collection, []):
            raw_id = str(item.get(id_field, ""))
            canonical_id = f"{prefix}_{raw_id}"
            mapping[f"{entity_type}:{raw_id}"] = canonical_id
            item[id_field] = canonical_id
    for item in packet.get("npcs", []):
        if item.get("map_id") is not None:
            item["map_id"] = mapping.get(
                f"MAP:{item['map_id']}", item["map_id"]
            )
    for item in packet.get("quests", []):
        for field, entity_type in (
            ("npc_ids", "NPC"),
            ("map_ids", "MAP"),
            ("item_ids", "ITEM"),
            ("monster_ids", "MONSTER"),
        ):
            item[field] = [
                mapping.get(f"{entity_type}:{value}", value)
                for value in item.get(field, [])
            ]
    for relation in packet.get("relations", []):
        source_type = str(relation.get("source", "")).upper()
        target_type = str(relation.get("target", "")).upper()
        relation["source_id"] = mapping.get(
            f"{source_type}:{relation.get('source_id')}",
            relation.get("source_id"),
        )
        relation["target_id"] = mapping.get(
            f"{target_type}:{relation.get('target_id')}",
            relation.get("target_id"),
        )
    return packet, mapping


def _legacy_graph_from_modern(graph: KnowledgeGraph) -> MapleKnowledgeGraph:
    base = MapleKnowledgeBase()
    collections = (
        (MapleKnowledgeType.MAP, graph.maps),
        (MapleKnowledgeType.NPC, graph.npcs),
        (MapleKnowledgeType.ITEM, graph.items),
        (MapleKnowledgeType.QUEST, graph.quests),
        (MapleKnowledgeType.MONSTER, graph.monsters),
        (MapleKnowledgeType.EQUIPMENT, graph.equipment),
        (MapleKnowledgeType.STORY_LORE, graph.story_lore),
    )
    for entity_type, nodes in collections:
        prefix = TYPE_PREFIXES[entity_type.value]
        for node in nodes:
            identifier = getattr(node, f"{prefix}_id")
            base.add_entity(
                MapleKnowledgeEntity(
                    knowledge_id=str(identifier),
                    knowledge_type=entity_type,
                    name=node.name,
                    aliases=node.aliases,
                    source=node.provenance.source_id,
                    confidence=node.confidence,
                    version=node.version,
                    provenance=node.provenance.model_dump(mode="json"),
                )
            )
    legacy_relation_types = {item.value for item in KnowledgeRelationType}
    for index, relation in enumerate(graph.all_relations()):
        relation_type = relation.relation_type.value
        if relation_type not in legacy_relation_types:
            relation_type = KnowledgeRelationType.RELATED_TO.value
        base.add_relation(
            KnowledgeRelation(
                relation_id=f"runtime-{index}",
                source_id=f"{relation.source}_{relation.source_id}",
                target_id=f"{relation.target}_{relation.target_id}",
                relation_type=relation_type,
                confidence=relation.confidence,
            )
        )
    return MapleKnowledgeGraph(base)
