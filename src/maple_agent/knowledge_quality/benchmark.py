"""KnowledgeQualityBenchmark:基于真实 Dataset 统计质量指标。"""

from __future__ import annotations

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge_quality.models import (
    KnowledgeAcquisitionManifest,
    KnowledgeCoverageDenominator,
    KnowledgeQualityBenchmarkResult,
    MergeRecord,
)
from maple_agent.knowledge_quality.topology import TopologyValidationResult


class KnowledgeQualityBenchmark:
    """汇总实体/关系/映射/拓扑/来源指标。"""

    def evaluate(
        self,
        dataset: KnowledgeDataset,
        manifest: KnowledgeAcquisitionManifest,
        mappings: list[MergeRecord],
        topology: TopologyValidationResult | None = None,
        denominators: list[KnowledgeCoverageDenominator] | None = None,
    ) -> KnowledgeQualityBenchmarkResult:
        reasons: list[str] = []
        total_entities = (
            len(dataset.maps)
            + len(dataset.npcs)
            + len(dataset.monsters)
            + len(dataset.items)
        )
        mapped = sum(
            1
            for record in mappings
            if record.outcome.value == "MERGED"
        )
        unresolved = sum(
            1
            for record in mappings
            if record.outcome.value == "UNRESOLVED"
        )
        duplicates = manifest.duplicate_count
        conflicts = manifest.conflict_count
        canonical_coverage = (
            round(mapped / total_entities, 4) if total_entities else None
        )
        provenance_coverage = (
            round(
                min(1.0, manifest.canonical_mapped_count / total_entities),
                4,
            )
            if total_entities
            else None
        )
        profile_ok = manifest.game_profile and manifest.server_profile
        version_ok = bool(manifest.data_version)
        profile_binding = 1.0 if profile_ok else None
        version_binding = 1.0 if version_ok else None
        if not profile_ok:
            reasons.append("server profile missing")
        unresolved_rate = (
            round(unresolved / total_entities, 4)
            if total_entities
            else None
        )
        dangling_rate = None
        if topology is not None and topology.edge_count:
            dangling_rate = round(
                (
                    topology.dangling_source + topology.dangling_target
                )
                / topology.edge_count,
                4,
            )
        duplicate_rate = (
            round(duplicates / total_entities, 4)
            if total_entities
            else None
        )
        conflict_rate = (
            round(conflicts / total_entities, 4)
            if total_entities
            else None
        )
        map_topology_valid_rate = (
            round(
                (topology.edge_count - topology.invalid_relation_types)
                / topology.edge_count,
                4,
            )
            if topology and topology.edge_count
            else None
        )
        portal_target_valid_rate = (
            round(
                1.0 - dangling_rate,
                4,
            )
            if dangling_rate is not None
            else None
        )
        source_validation_rate = (
            round(
                max(
                    0.0,
                    1.0
                    - (len(manifest.warnings) + len(manifest.errors))
                    / max(1, total_entities),
                ),
                4,
            )
            if total_entities
            else None
        )
        coverage_known = bool(denominators)
        if not coverage_known:
            reasons.append("dataset denominator unavailable")
        values = [
            value
            for value in (
                canonical_coverage,
                provenance_coverage,
                profile_binding,
                version_binding,
                map_topology_valid_rate,
                portal_target_valid_rate,
                source_validation_rate,
            )
            if value is not None
        ]
        validation_score = (
            round(sum(values) / len(values), 4) if values else None
        )
        if validation_score is None:
            reasons.append("validation score unavailable")
        return KnowledgeQualityBenchmarkResult(
            total_entities=total_entities,
            total_relations=len(dataset.relations),
            map_count=len(dataset.maps),
            portal_count=manifest.relation_counts.get("portal", 0),
            npc_count=len(dataset.npcs),
            monster_count=len(dataset.monsters),
            quest_count=manifest.entity_counts.get("quest", 0),
            item_count=len(dataset.items),
            canonical_id_coverage=canonical_coverage,
            provenance_coverage=provenance_coverage,
            profile_binding_coverage=profile_binding,
            version_binding_coverage=version_binding,
            unresolved_reference_rate=unresolved_rate,
            dangling_reference_rate=dangling_rate,
            duplicate_rate=duplicate_rate,
            conflict_rate=conflict_rate,
            map_topology_valid_rate=map_topology_valid_rate,
            portal_target_valid_rate=portal_target_valid_rate,
            source_validation_rate=source_validation_rate,
            validation_score=validation_score,
            reasons=reasons,
        )
