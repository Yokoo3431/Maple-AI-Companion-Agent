"""KnowledgeImportOrchestrator:外部来源 -> Generic Pipeline -> Canonical -> World/Spatial。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge.importer.models import ImportSource
from maple_agent.knowledge.importer.pipeline import run_import
from maple_agent.knowledge_quality.benchmark import KnowledgeQualityBenchmark
from maple_agent.knowledge_quality.canonical import CanonicalMapper
from maple_agent.knowledge_quality.models import (
    KnowledgeAcquisitionManifest,
    KnowledgeCoverageDenominator,
    KnowledgeDatasetMetadata,
    KnowledgeQualityBenchmarkResult,
    KnowledgeReadinessPolicy,
    KnowledgeSourceReference,
    MergeOutcome,
    MergeRecord,
)
from maple_agent.knowledge_quality.readiness import build_knowledge_readiness
from maple_agent.knowledge_quality.source import (
    KnowledgeSourceAdapter,
    content_hash,
    sanitize_source_metadata,
)
from maple_agent.knowledge_quality.topology import (
    TopologyValidationResult,
    WorldTopologyValidator,
)
from maple_agent.logging_setup import new_id
from maple_agent.safety_vnext.models import KnowledgeReadinessReference
from maple_agent.world_knowledge.importer import WorldKnowledgeImporter
from maple_agent.world_knowledge.relation import MapRelationBuilder


class AcquisitionResult(BaseModel):
    """知识获取结果(数据集 + 图谱 + 映射 + 指标 + 就绪)。"""

    manifest: KnowledgeAcquisitionManifest
    source: KnowledgeSourceReference
    dataset: KnowledgeDataset | None = None
    graph: dict | None = None
    mappings: list[MergeRecord] = Field(default_factory=list)
    topology: TopologyValidationResult | None = None
    benchmark: KnowledgeQualityBenchmarkResult | None = None
    readiness: KnowledgeReadinessReference | None = None
    dataset_metadata: KnowledgeDatasetMetadata | None = None
    validation: str = ""


def to_generic_packet(packet: dict) -> dict:
    """把来源 packet 规范化为 Generic Import Pipeline 输入(不创建新 importer)。"""
    if any(
        key in packet
        for key in (
            "npcs",
            "monsters",
            "items",
            "equipment",
            "quests",
            "story_lore",
        )
    ):
        return packet
    generic: dict = {
        "maps": [],
        "npcs": [],
        "monsters": [],
        "items": [],
        "equipment": [],
        "quests": [],
        "story_lore": [],
        "relations": [],
    }
    name_to_id: dict[str, str] = {}
    for item in packet.get("maps", []):
        name = str(item.get("name", ""))
        if name:
            name_to_id[name] = str(item.get("map_id", ""))
        generic["maps"].append(
            {
                "map_id": item.get("map_id"),
                "name": name,
                "aliases": item.get("aliases", []),
                "region": item.get("region", ""),
            }
        )
    for entity in packet.get("entities", []):
        entity_type = entity.get("knowledge_type", "")
        if entity_type == "NPC":
            generic["npcs"].append(
                {
                    "npc_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                    "description": entity.get("description", ""),
                }
            )
        elif entity_type == "MONSTER":
            generic["monsters"].append(
                {
                    "monster_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                }
            )
        elif entity_type == "ITEM":
            generic["items"].append(
                {
                    "item_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                }
            )
        elif entity_type == "EQUIPMENT":
            generic["equipment"].append(
                {
                    "equipment_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                    "slot": entity.get("attributes", {}).get("slot", ""),
                }
            )
        elif entity_type == "QUEST":
            generic["quests"].append(
                {
                    "quest_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                    "description": entity.get("description", ""),
                }
            )
        elif entity_type == "STORY_LORE":
            generic["story_lore"].append(
                {
                    "lore_id": entity.get("knowledge_id"),
                    "name": entity.get("name", ""),
                    "aliases": entity.get("aliases", []),
                    "description": entity.get("description", ""),
                }
            )
    for relation in packet.get("relations", []):
        # knowledge 格式关系(source_id/target_id)由 maple_knowledge 层持有,
        # 不进入 generic dataset;仅透传 generic 格式(source/target)。
        if "source" not in relation or "target" not in relation:
            continue
        generic["relations"].append(
            {
                "source": relation.get("source"),
                "source_id": relation.get("source_id"),
                "target": relation.get("target"),
                "target_id": relation.get("target_id"),
                "relation_type": relation.get("relation_type", ""),
            }
        )
    return generic


def _external_id(entity) -> str:
    for attr in (
        "map_id",
        "npc_id",
        "monster_id",
        "item_id",
        "equipment_id",
        "quest_id",
        "lore_id",
    ):
        value = getattr(entity, attr, None)
        if value is not None:
            return str(value)
    return ""


class KnowledgeImportOrchestrator:
    """编排来源导入:Adapter -> Generic Pipeline -> Canonical -> World Graph
    -> Benchmark -> Readiness(不创建第三套 generic importer)。"""

    def __init__(
        self,
        *,
        canonical_mapper: CanonicalMapper | None = None,
        policy: KnowledgeReadinessPolicy | None = None,
    ) -> None:
        self.canonical_mapper = canonical_mapper
        self.policy = policy or KnowledgeReadinessPolicy()
        self.last_result: AcquisitionResult | None = None

    def acquire(
        self,
        source: KnowledgeSourceReference,
        adapter: KnowledgeSourceAdapter,
        *,
        source_id_mapping: dict[str, str] | None = None,
        denominators: list[KnowledgeCoverageDenominator] | None = None,
    ) -> AcquisitionResult:
        packet = adapter.load(source)
        packet_hash = content_hash(packet)
        source = source.model_copy(
            update={
                "content_hash": packet_hash,
                "adapter_name": getattr(
                    adapter, "adapter_name", source.adapter_name
                ),
                "adapter_version": getattr(
                    adapter, "adapter_version", source.adapter_version
                ),
            }
        )
        generic = to_generic_packet(packet)
        bundle = run_import(
            generic,
            source=ImportSource(
                source_id=source.source_id,
                source_type=source.source_type.value,
                version=source.data_version,
                game_profile=source.game_profile,
                server_profile=source.server_profile,
                content_hash=packet_hash,
            ),
        )
        dataset = bundle.dataset
        dataset.game_profile = source.game_profile
        dataset.server_profile = source.server_profile
        dataset.source_provenance = [source.source_id]
        dataset.content_hash = packet_hash
        mappings: list[MergeRecord] = []
        if self.canonical_mapper is not None:
            for entity in (
                list(dataset.maps)
                + list(dataset.npcs)
                + list(dataset.monsters)
                + list(dataset.items)
                + list(dataset.equipment)
                + list(dataset.quests)
                + list(dataset.story_lore)
            ):
                canonical_id, outcome, reason = (
                    self.canonical_mapper.resolve(
                        external_id=_external_id(entity),
                        name=entity.name,
                        aliases=list(entity.aliases),
                        source_id_mapping=source_id_mapping,
                    )
                )
                mappings.append(
                    MergeRecord(
                        external_id=_external_id(entity),
                        canonical_id=canonical_id,
                        outcome=outcome,
                        reason=reason,
                    )
                )
        graph, import_warnings = WorldKnowledgeImporter.import_from_dataset(
            dataset
        )
        # 地图连接由 world-specific strict adapter 构建(unknown 不静默 PORTAL)
        strict_connections, strict_warnings = MapRelationBuilder.build_strict(
            packet.get("connections", [])
        )
        for connection in strict_connections:
            if (
                graph.find_map(connection.source_map) is not None
                and graph.find_map(connection.target_map) is not None
            ):
                graph.add_connection(connection)
            else:
                strict_warnings.append(
                    f"dangling connection: "
                    f"{connection.source_map}->{connection.target_map}"
                )
        import_warnings = import_warnings + strict_warnings
        topology = WorldTopologyValidator().validate(
            graph,
            canonical_mapper=self.canonical_mapper,
        )
        duplicates = sum(
            1 for warning in bundle.result.warnings if "重复" in warning
        )
        conflicts = sum(
            1 for warning in bundle.result.warnings if "命名冲突" in warning
        )
        mapped_count = sum(
            1
            for record in mappings
            if record.outcome is MergeOutcome.MERGED
        )
        unresolved_count = sum(
            1
            for record in mappings
            if record.outcome is MergeOutcome.UNRESOLVED
        )
        entity_counts = {
            "map": len(dataset.maps),
            "npc": len(dataset.npcs),
            "monster": len(dataset.monsters),
            "item": len(dataset.items),
            "equipment": len(dataset.equipment),
            "quest": len(dataset.quests),
            "story_lore": len(dataset.story_lore),
        }
        relation_counts = {
            "total": len(dataset.relations),
            "portal": sum(
                1
                for connection in graph.all_connections()
                if connection.connection_type.value == "PORTAL"
            ),
        }
        manifest = KnowledgeAcquisitionManifest(
            manifest_id=new_id(),
            source_reference=source.source_id,
            game_profile=source.game_profile,
            server_profile=source.server_profile,
            data_version=source.data_version,
            entity_counts=entity_counts,
            relation_counts=relation_counts,
            canonical_mapped_count=mapped_count,
            unresolved_count=unresolved_count,
            duplicate_count=duplicates,
            conflict_count=conflicts,
            content_hash=packet_hash,
            import_status=(
                "WARNINGS" if bundle.result.warnings else "OK"
            ),
            warnings=bundle.result.warnings + import_warnings,
            errors=[],
        )
        benchmark = KnowledgeQualityBenchmark().evaluate(
            dataset,
            manifest,
            mappings,
            topology,
            denominators,
        )
        readiness = build_knowledge_readiness(
            benchmark,
            policy=self.policy,
            game_profile=source.game_profile,
            server_version=source.server_profile,
            dataset_version=source.data_version,
            source_provenance=(
                source.source_name or source.source_type.value
            ),
            denominators=denominators,
        )
        result = AcquisitionResult(
            manifest=manifest,
            source=source,
            dataset=dataset,
            graph={
                "node_count": graph.node_count(),
                "connection_count": graph.connection_count(),
                "maps": graph.known_map_names(),
            },
            mappings=mappings,
            topology=topology,
            benchmark=benchmark,
            readiness=readiness,
            dataset_metadata=KnowledgeDatasetMetadata(
                dataset_version=source.data_version or dataset.version,
                game_profile=source.game_profile,
                server_profile=source.server_profile,
                source_provenance=[source.source_id],
                content_hash=packet_hash,
                adapter_name=source.adapter_name,
                adapter_version=source.adapter_version,
            ),
            validation=readiness.status.value,
        )
        self.last_result = result
        return result


def write_versioned_dataset_record(
    result: AcquisitionResult,
    base_dir: str,
) -> str:
    """Write sanitized metadata for one dataset version; never write raw packet."""
    version = result.manifest.data_version or "unversioned"
    version_dir = Path(base_dir) / version
    version_dir.mkdir(parents=True, exist_ok=True)
    (version_dir / "manifest.json").write_text(
        json.dumps(
            result.manifest.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (version_dir / "sources.json").write_text(
        json.dumps(
            sanitize_source_metadata(result.source),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (version_dir / "canonical_map.json").write_text(
        json.dumps(
            {
                record.external_id: record.canonical_id
                for record in result.mappings
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (version_dir / "dataset_metadata.json").write_text(
        json.dumps(
            (
                result.dataset_metadata.model_dump(mode="json")
                if result.dataset_metadata is not None
                else {}
            ),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (version_dir / "validation_report.json").write_text(
        json.dumps(
            result.benchmark.model_dump(mode="json")
            if result.benchmark is not None
            else {},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return str(version_dir)
