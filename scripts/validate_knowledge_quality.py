"""Knowledge Quality 只读校验:来源 -> 导入 -> canonical -> 校验 -> benchmark -> readiness -> trace。

无 --source 时输出当前 demo(MANUAL_CURATED),诚实保持 FOUNDATION_ONLY。
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.knowledge_quality import (  # noqa: E402
    CanonicalMapper,
    KnowledgeCoverageDenominator,
    KnowledgeImportOrchestrator,
    KnowledgeReadinessPolicy,
    KnowledgeSourceReference,
    KnowledgeSourceType,
    LocalStaticKnowledgeAdapter,
    ManualCuratedAdapter,
    save_knowledge_acquisition_trace,
    write_versioned_dataset_record,
)
from maple_agent.logging_setup import new_id  # noqa: E402
from maple_agent.maple_knowledge import (  # noqa: E402
    MapleKnowledgeGraph,
    load_demo_knowledge,
)


def _demo_source(
    game_profile: str,
    server_profile: str,
    dataset_version: str,
) -> KnowledgeSourceReference:
    return KnowledgeSourceReference(
        source_id="manual-demo",
        source_type=KnowledgeSourceType.MANUAL_CURATED,
        source_name="demo manual dataset",
        game_profile=game_profile,
        server_profile=server_profile,
        data_version=dataset_version,
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="fixture",
        trust_level=0.5,
        confidence=0.5,
        adapter_name="ManualCuratedAdapter",
        adapter_version="1.0",
    )


def _local_source(
    source_path: str,
    game_profile: str,
    server_profile: str,
    dataset_version: str,
) -> KnowledgeSourceReference:
    return KnowledgeSourceReference(
        source_id="local-static",
        source_type=KnowledgeSourceType.LOCAL_STATIC_FILE,
        source_name=str(Path(source_path).name),
        source_reference=source_path,
        game_profile=game_profile,
        server_profile=server_profile,
        data_version=dataset_version,
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="",
        trust_level=0.6,
        confidence=0.6,
        adapter_name="LocalStaticKnowledgeAdapter",
        adapter_version="1.0",
    )


def _write_versioned_dataset(
    result,
    base_dir: Path,
) -> None:
    """写 versioned metadata only; raw source packets are never persisted."""
    write_versioned_dataset_record(result, str(base_dir))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Knowledge Quality 只读校验"
    )
    parser.add_argument("--source", default="")
    parser.add_argument("--source-type", default="manual")
    parser.add_argument("--game-profile", default="maple-v113")
    parser.add_argument("--server-profile", default="nostalgic")
    parser.add_argument("--dataset-version", default="demo-v1")
    parser.add_argument("--output", default="sessions")
    parser.add_argument(
        "--knowledge-root",
        default="knowledge/versions",
        help="versioned dataset 输出目录",
    )
    args = parser.parse_args()
    trace_id = new_id()
    output = Path(args.output)
    graph = MapleKnowledgeGraph()
    entities, relations = load_demo_knowledge()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    mapper = CanonicalMapper.from_maple_graph(
        graph,
        game_profile=args.game_profile,
        server_profile=args.server_profile,
        data_version=args.dataset_version,
    )
    policy = KnowledgeReadinessPolicy(minimum_total_entities=5)
    orchestrator = KnowledgeImportOrchestrator(
        canonical_mapper=mapper,
        policy=policy,
    )
    if args.source and args.source_type == "local":
        source = _local_source(
            args.source,
            args.game_profile,
            args.server_profile,
            args.dataset_version,
        )
        adapter = LocalStaticKnowledgeAdapter()
    else:
        source = _demo_source(
            args.game_profile,
            args.server_profile,
            args.dataset_version,
        )
        adapter = ManualCuratedAdapter()
    denominators = [
        KnowledgeCoverageDenominator(
            source_name="fixture",
            expected_counts={
                "map": 3,
                "portal": 2,
                "npc": 1,
                "monster": 1,
                "quest": 1,
                "item": 2,
            },
        )
    ]
    result = orchestrator.acquire(
        source,
        adapter,
        denominators=denominators,
    )
    _write_versioned_dataset(result, Path(args.knowledge_root))
    manifest = result.manifest.model_dump(mode="json")
    save_knowledge_acquisition_trace(
        output,
        trace_id,
        manifest=manifest,
        sources=result.source.model_dump(mode="json"),
        import_summary={
            "entity_counts": result.manifest.entity_counts,
            "relation_counts": result.manifest.relation_counts,
        },
        mapping_summary={
            "mapped": result.manifest.canonical_mapped_count,
            "unresolved": result.manifest.unresolved_count,
            "duplicates": result.manifest.duplicate_count,
            "conflicts": result.manifest.conflict_count,
        },
        conflicts=[],
        benchmark=result.benchmark,
        readiness=result.readiness.model_dump(mode="json"),
        validation=result.readiness.status.value,
    )
    print("source =", source.source_type.value, source.source_id)
    print("entities =", result.manifest.entity_counts)
    print("relations =", result.manifest.relation_counts)
    print(
        "canonical =",
        result.manifest.canonical_mapped_count,
        "unresolved =",
        result.manifest.unresolved_count,
    )
    print(
        "validation_score =",
        result.benchmark.validation_score,
    )
    print(
        "KnowledgeReadiness =",
        result.readiness.status.value,
    )
    print(
        "TRACE:",
        output / trace_id / "knowledge_acquisition_trace.json",
    )
    print(
        "VERSIONED DATASET:",
        Path(args.knowledge_root) / result.manifest.data_version,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
