"""KnowledgeImporter + Demo Loader:结构化数据 -> 知识实体(不爬取)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)
from maple_agent.maple_knowledge.relations import KnowledgeRelationBuilder


class KnowledgeImporter:
    """接受结构化数据,校验 schema,转换为知识实体。"""

    def import_entities(
        self,
        data: dict,
    ) -> list[MapleKnowledgeEntity]:
        entities: list[MapleKnowledgeEntity] = []
        for item in data.get("entities", []):
            entities.append(
                MapleKnowledgeEntity(
                    knowledge_id=item["knowledge_id"],
                    knowledge_type=MapleKnowledgeType(
                        item["knowledge_type"]
                    ),
                    name=item["name"],
                    aliases=item.get("aliases", []),
                    description=item.get("description", ""),
                    attributes=item.get("attributes", {}),
                    source=item.get("source", "external"),
                    confidence=item.get("confidence", 0.8),
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
