"""Import Pipeline:构建 → 校验 → Replay。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge.importer.builder import build_dataset
from maple_agent.knowledge.importer.models import ImportResult, ImportSource
from maple_agent.knowledge.importer.validator import (
    DatasetValidationResult,
    DatasetValidator,
)


class ImportBundle(BaseModel):
    """导入产物。"""

    dataset: KnowledgeDataset
    result: ImportResult
    validation: DatasetValidationResult


def run_import(
    source_data: dict,
    *,
    source: ImportSource | None = None,
    sessions_dir: str | Path = "sessions",
) -> ImportBundle:
    """执行导入流水线并落盘 knowledge_import.json(Data Driven,只读)。"""
    src = source or ImportSource(source_id="external", source_type="json")
    dataset, result = build_dataset(
        source_data,
        source=src.source_id,
        version=src.version,
    )
    validation = DatasetValidator().validate(dataset)
    result.warnings.extend(validation.warnings)
    _write_import_replay(sessions_dir, src, result, validation)
    return ImportBundle(
        dataset=dataset,
        result=result,
        validation=validation,
    )


def _write_import_replay(
    sessions_dir: str | Path,
    source: ImportSource,
    result: ImportResult,
    validation: DatasetValidationResult,
) -> None:
    directory = Path(sessions_dir)
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "source": source.source_id,
        "source_type": source.source_type,
        "version": source.version,
        "imported_count": {
            "maps": result.imported_maps,
            "npcs": result.imported_npcs,
            "monsters": result.imported_monsters,
            "items": result.imported_items,
            "relations": result.imported_relations,
        },
        "warnings": result.warnings,
        "validation_result": validation.model_dump(mode="json"),
        "timestamp": source.timestamp.isoformat(),
    }
    (directory / "knowledge_import.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
