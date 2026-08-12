"""MapleKnowledgeRetriever:MapleCompanionContext -> 领域知识参考(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import (
    MapleKnowledgeEntity,
    MapleKnowledgeReference,
    MapleKnowledgeType,
)


class MapleKnowledgeRetriever:
    """按当前 Maple 上下文检索相关领域知识。"""

    def __init__(self, graph: MapleKnowledgeGraph) -> None:
        self.graph = graph
        self.last_reference: MapleKnowledgeReference | None = None

    def retrieve(
        self,
        *,
        context: MapleCompanionContextReference | None = None,
    ) -> MapleKnowledgeReference:
        location = ""
        visible_entities: list[str] = []
        if context is not None and context.world_context is not None:
            location = context.world_context.location
            visible_entities = list(
                context.world_context.visible_entities
            )
        reasoning: list[str] = []
        map_entity = self.graph.find_by_name(location) if location else None
        related_maps = [map_entity.name] if map_entity is not None else []
        npcs: list[str] = []
        monsters: list[str] = []
        for visible in visible_entities:
            entity = self.graph.find_by_name(visible)
            if entity is None:
                continue
            if entity.knowledge_type is MapleKnowledgeType.NPC:
                npcs.append(entity.name)
            elif entity.knowledge_type is MapleKnowledgeType.MONSTER:
                monsters.append(entity.name)
        quests = self._related_quests(map_entity, npcs)
        items = self._related_items(map_entity, monsters)
        if map_entity is not None:
            reasoning.append(f"地图: {map_entity.name}")
        if npcs:
            reasoning.append("NPC: " + ", ".join(npcs))
        if quests:
            reasoning.append("任务: " + ", ".join(quests))
        confidence = self._confidence(
            map_entity,
            npcs,
            monsters,
            quests,
        )
        reference = MapleKnowledgeReference(
            related_npcs=sorted(set(npcs)),
            related_maps=related_maps,
            related_monsters=sorted(set(monsters)),
            related_items=sorted(set(items)),
            related_quests=sorted(set(quests)),
            confidence=confidence,
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference

    def _related_quests(
        self,
        map_entity: MapleKnowledgeEntity | None,
        npcs: list[str],
    ) -> list[str]:
        quests: list[str] = []
        anchors = set(npcs)
        if map_entity is not None:
            anchors.add(map_entity.name)
        for entity in self.graph.all_entities():
            if entity.knowledge_type is not MapleKnowledgeType.QUEST:
                continue
            for relation, target in self.graph.find_related(
                entity.knowledge_id
            ):
                if target.name in anchors:
                    quests.append(entity.name)
                    break
        return quests

    def _related_items(
        self,
        map_entity: MapleKnowledgeEntity | None,
        monsters: list[str],
    ) -> list[str]:
        items: list[str] = []
        monster_ids = {
            entity.knowledge_id
            for entity in self.graph.all_entities()
            if entity.name in monsters
        }
        for entity_id in monster_ids:
            for relation, target in self.graph.find_related(entity_id):
                if target.knowledge_type is MapleKnowledgeType.ITEM:
                    items.append(target.name)
        return items

    @staticmethod
    def _confidence(
        map_entity: MapleKnowledgeEntity | None,
        npcs: list[str],
        monsters: list[str],
        quests: list[str],
    ) -> float:
        values: list[float] = []
        if map_entity is not None:
            values.append(map_entity.confidence)
        if npcs:
            values.append(0.9)
        if monsters:
            values.append(0.9)
        if quests:
            values.append(0.85)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)


def save_maple_knowledge_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    knowledge_entities: list[MapleKnowledgeEntity],
    relations: list,
    retrieval_result: MapleKnowledgeReference,
    validation: str,
) -> None:
    """写入 maple_knowledge_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "knowledge_entities": [
            entity.model_dump(mode="json")
            for entity in knowledge_entities
        ],
        "relations": [
            relation.model_dump(mode="json") for relation in relations
        ],
        "retrieval_result": retrieval_result.model_dump(mode="json"),
        "validation": validation,
    }
    (directory / "maple_knowledge_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
