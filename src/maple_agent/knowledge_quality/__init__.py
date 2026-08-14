"""Knowledge Acquisition & Quality Gate 层(Phase 13-G,静态知识,只读)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.knowledge_quality.benchmark import KnowledgeQualityBenchmark
from maple_agent.knowledge_quality.canonical import CanonicalMapper
from maple_agent.knowledge_quality.consolidator import (
    AcquisitionResult,
    KnowledgeImportOrchestrator,
    to_generic_packet,
    write_versioned_dataset_record,
)
from maple_agent.knowledge_quality.models import (
    CanonicalEntityReference,
    KnowledgeAcquisitionManifest,
    KnowledgeCoverageDenominator,
    KnowledgeDatasetMetadata,
    KnowledgeQualityBenchmarkResult,
    KnowledgeReadinessPolicy,
    KnowledgeSourceReference,
    KnowledgeSourceType,
    MergeOutcome,
    MergeRecord,
)
from maple_agent.knowledge_quality.package import (
    DatasetPackageValidation,
    KnowledgeDatasetPackage,
    KnowledgeDatasetPackageAdapter,
    KnowledgeDatasetPackageManifest,
)
from maple_agent.knowledge_quality.readiness import build_knowledge_readiness
from maple_agent.knowledge_quality.source import (
    KnowledgeSourceAdapter,
    LocalStaticKnowledgeAdapter,
    ManualCuratedAdapter,
    StaticGameResourceAdapter,
    WikiCommunityAdapter,
    content_hash,
    sanitize_source_metadata,
)
from maple_agent.knowledge_quality.topology import (
    TopologyValidationResult,
    WorldTopologyValidator,
)


def save_knowledge_acquisition_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    manifest: dict,
    sources: dict,
    import_summary: dict,
    mapping_summary: dict,
    conflicts: list[str],
    benchmark: object,
    readiness: dict,
    validation: str,
) -> None:
    """写入 knowledge_acquisition_trace.json(不存大型原始资源)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "manifest": manifest,
        "sources": sanitize_source_metadata(sources),
        "import_summary": import_summary,
        "mapping_summary": mapping_summary,
        "conflicts": conflicts,
        "benchmark": benchmark.model_dump(mode="json"),
        "readiness": readiness,
        "validation": validation,
    }
    (directory / "knowledge_acquisition_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "AcquisitionResult",
    "CanonicalEntityReference",
    "CanonicalMapper",
    "KnowledgeAcquisitionManifest",
    "KnowledgeCoverageDenominator",
    "KnowledgeDatasetPackage",
    "KnowledgeDatasetPackageAdapter",
    "KnowledgeDatasetPackageManifest",
    "DatasetPackageValidation",
    "KnowledgeDatasetMetadata",
    "KnowledgeImportOrchestrator",
    "KnowledgeQualityBenchmark",
    "KnowledgeQualityBenchmarkResult",
    "KnowledgeReadinessPolicy",
    "KnowledgeSourceAdapter",
    "KnowledgeSourceReference",
    "KnowledgeSourceType",
    "LocalStaticKnowledgeAdapter",
    "ManualCuratedAdapter",
    "MergeOutcome",
    "MergeRecord",
    "StaticGameResourceAdapter",
    "TopologyValidationResult",
    "WikiCommunityAdapter",
    "WorldTopologyValidator",
    "build_knowledge_readiness",
    "content_hash",
    "sanitize_source_metadata",
    "save_knowledge_acquisition_trace",
    "to_generic_packet",
    "write_versioned_dataset_record",
]
