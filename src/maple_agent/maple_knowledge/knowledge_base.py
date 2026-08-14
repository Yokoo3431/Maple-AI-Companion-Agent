"""MapleKnowledgeBase + KnowledgeGraph:冒险岛领域知识存储与查询(确定性,无 LLM)。"""

from __future__ import annotations

from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)


class MapleKnowledgeBase:
    """知识实体与关系存储。"""

    def __init__(self) -> None:
        self._entities: dict[str, MapleKnowledgeEntity] = {}
        self._relations: list[KnowledgeRelation] = []
        self._conflicts: list[str] = []

    def add_entity(self, entity: MapleKnowledgeEntity) -> None:
        existing = self._entities.get(entity.knowledge_id)
        if existing is not None:
            if existing.model_dump(mode="json") != entity.model_dump(mode="json"):
                self._conflicts.append(
                    f"duplicate canonical id: {entity.knowledge_id}"
                )
            return
        self._entities[entity.knowledge_id] = entity

    def add_relation(self, relation: KnowledgeRelation) -> None:
        self._relations.append(relation)

    def get_entity(self, knowledge_id: str) -> MapleKnowledgeEntity | None:
        return self._entities.get(knowledge_id)

    def entities(self) -> list[MapleKnowledgeEntity]:
        return list(self._entities.values())

    def relations(self) -> list[KnowledgeRelation]:
        return list(self._relations)

    def entity_count(self) -> int:
        return len(self._entities)

    def relation_count(self) -> int:
        return len(self._relations)

    def conflicts(self) -> list[str]:
        return list(self._conflicts)


class MapleKnowledgeGraph:
    """确定性知识图谱查询。"""

    def __init__(self, base: MapleKnowledgeBase | None = None) -> None:
        self.base = base or MapleKnowledgeBase()

    def add_entity(self, entity: MapleKnowledgeEntity) -> None:
        self.base.add_entity(entity)

    def add_relation(self, relation: KnowledgeRelation) -> None:
        self.base.add_relation(relation)

    def find_by_name(self, name: str) -> MapleKnowledgeEntity | None:
        normalized = name.strip().lower()
        for entity in self.base.entities():
            if entity.name.strip().lower() == normalized:
                return entity
            if any(
                alias.strip().lower() == normalized
                for alias in entity.aliases
            ):
                return entity
        return None

    def find_by_type(
        self,
        knowledge_type: MapleKnowledgeType,
    ) -> list[MapleKnowledgeEntity]:
        return [
            entity
            for entity in self.base.entities()
            if entity.knowledge_type is knowledge_type
        ]

    def find_related(
        self,
        entity_id: str,
    ) -> list[tuple[KnowledgeRelation, MapleKnowledgeEntity]]:
        results: list[tuple[KnowledgeRelation, MapleKnowledgeEntity]] = []
        for relation in self.base.relations():
            if relation.source_id != entity_id:
                continue
            target = self.base.get_entity(relation.target_id)
            if target is not None:
                results.append((relation, target))
        return results

    def all_entities(self) -> list[MapleKnowledgeEntity]:
        return self.base.entities()

    def all_relations(self) -> list[KnowledgeRelation]:
        return self.base.relations()

    def conflicts(self) -> list[str]:
        return self.base.conflicts()
