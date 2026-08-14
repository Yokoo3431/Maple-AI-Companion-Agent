"""Validate and import the Phase 13-M static dataset package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from maple_agent.knowledge_quality import (
    CanonicalMapper,
    KnowledgeDatasetPackage,
    KnowledgeDatasetPackageAdapter,
    KnowledgeImportOrchestrator,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--package-dir",
        default="knowledge_dataset",
        help="versioned static package directory",
    )
    args = parser.parse_args()

    package = KnowledgeDatasetPackage.load(Path(args.package_dir))
    validation = package.validate()
    payload: dict = {"package_validation": validation.model_dump(mode="json")}
    if validation.valid:
        source = package.source_reference()
        adapter = KnowledgeDatasetPackageAdapter()
        result = KnowledgeImportOrchestrator(
            canonical_mapper=CanonicalMapper(package.canonical_mapper_entities())
        ).acquire(
            source,
            adapter,
            source_id_mapping=package.canonical_source_id_mapping(),
            denominators=[package.denominator()],
        )
        payload.update(
            {
                "import_manifest": result.manifest.model_dump(mode="json"),
                "benchmark": result.benchmark.model_dump(mode="json")
                if result.benchmark
                else None,
                "readiness": result.readiness.model_dump(mode="json")
                if result.readiness
                else None,
            }
        )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if validation.valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
