"""KnowledgeImporter + Demo Loader:结构化数据 -> 知识实体(不爬取)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.maple_knowledge.models import (
    KnowledgeEntityProvenance,
    KnowledgeRelation,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)
from maple_agent.maple_knowledge.relations import KnowledgeRelationBuilder


class KnowledgeImporter:
    """接受结构化数据,校验 schema,转换为知识实体。"""

    def __init__(self) -> None:
        self.last_conflicts: list[str] = []

    def import_entities(
        self,
        data: dict,
    ) -> list[MapleKnowledgeEntity]:
        entities: list[MapleKnowledgeEntity] = []
        seen_ids: set[str] = set()
        self.last_conflicts = []
        for item in data.get("entities", []):
            knowledge_id = str(item["knowledge_id"])
            if knowledge_id in seen_ids:
                self.last_conflicts.append(
                    f"duplicate canonical id: {knowledge_id}"
                )
                continue
            seen_ids.add(knowledge_id)
            provenance = KnowledgeEntityProvenance.model_validate(
                item.get("provenance", {}) or {}
            )
            entities.append(
                MapleKnowledgeEntity(
                    knowledge_id=knowledge_id,
                    knowledge_type=MapleKnowledgeType(
                        item["knowledge_type"]
                    ),
                    name=item["name"],
                    aliases=item.get("aliases", []),
                    description=item.get("description", ""),
                    attributes=item.get("attributes", {}),
                    source=item.get("source", "external"),
                    confidence=item.get("confidence", 0.8),
                    version=item.get("version", provenance.data_version),
                    provenance=provenance,
                )
            )
        return entities

    def import_relations(
        self,
        data: dict,
    ) -> list[KnowledgeRelation]:
        return KnowledgeRelationBuilder().build_from_pairs(
            data.get("relations", [])
        )


def load_demo_knowledge() -> tuple[
    list[MapleKnowledgeEntity],
    list[KnowledgeRelation],
]:
    """加载 data/demo_maple_knowledge.json 演示数据。"""
    path = (
        Path(__file__).resolve().parent
        / "data"
        / "demo_maple_knowledge.json"
    )
    raw = json.loads(path.read_text(encoding="utf-8"))
    importer = KnowledgeImporter()
    return importer.import_entities(raw), importer.import_relations(raw)


def load_phase13j_fixture() -> tuple[
    list[MapleKnowledgeEntity],
    list[KnowledgeRelation],
]:
    """Load the small sanitized Phase 13-J fixture dataset."""
    path = Path(__file__).resolve().parent / "data" / "phase13j_fixture.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    importer = KnowledgeImporter()
    return importer.import_entities(raw), importer.import_relations(raw)
