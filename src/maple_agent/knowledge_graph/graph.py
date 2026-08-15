"""KnowledgeGraph:节点与关系查询(只读)。"""

from __future__ import annotations

from collections import defaultdict

from maple_agent.knowledge_graph.models import (
    EquipmentNode,
    ItemNode,
    MapNode,
    MonsterNode,
    NPCNode,
    QuestNode,
    Relation,
    RelationReference,
    RelationType,
    StoryLoreNode,
)


class KnowledgeGraph:
    """基于节点与关系构建的知识图谱(只读查询)。"""

    def __init__(
        self,
        maps: list[MapNode] | None = None,
        npcs: list[NPCNode] | None = None,
        monsters: list[MonsterNode] | None = None,
        items: list[ItemNode] | None = None,
        equipment: list[EquipmentNode] | None = None,
        quests: list[QuestNode] | None = None,
        story_lore: list[StoryLoreNode] | None = None,
        relations: list[Relation] | None = None,
    ) -> None:
        self._maps: dict[str, MapNode] = {}
        self._npcs: dict[str, NPCNode] = {}
        self._monsters: dict[str, MonsterNode] = {}
        self._items: dict[str, ItemNode] = {}
        self._equipment: dict[str, EquipmentNode] = {}
        self._quests: dict[str, QuestNode] = {}
        self._story_lore: dict[str, StoryLoreNode] = {}
        self._relations: list[Relation] = relations or []
        self._relations_index: dict[tuple[str, str], list[Relation]] = defaultdict(list)

        for node in maps or []:
            self._maps[str(node.map_id)] = node
            self._maps[node.name] = node
            for alias in node.aliases:
                self._maps[alias] = node
        for node in npcs or []:
            self._npcs[str(node.npc_id)] = node
            self._npcs[node.name] = node
            for alias in node.aliases:
                self._npcs[alias] = node
        for node in monsters or []:
            self._monsters[str(node.monster_id)] = node
            self._monsters[node.name] = node
            for alias in node.aliases:
                self._monsters[alias] = node
        for node in items or []:
            self._items[str(node.item_id)] = node
            self._items[node.name] = node
            for alias in node.aliases:
                self._items[alias] = node
        for node in equipment or []:
            self._equipment[str(node.equipment_id)] = node
            self._equipment[node.name] = node
            for alias in node.aliases:
                self._equipment[alias] = node
        for node in quests or []:
            self._quests[str(node.quest_id)] = node
            self._quests[node.name] = node
            for alias in node.aliases:
                self._quests[alias] = node
        for node in story_lore or []:
            self._story_lore[str(node.lore_id)] = node
            self._story_lore[node.name] = node
            for alias in node.aliases:
                self._story_lore[alias] = node
        for relation in self._relations:
            self._relations_index[(relation.source, str(relation.source_id))].append(
                relation
            )

    def find_map(self, ref: int | str) -> MapNode | None:
        return self._maps.get(str(ref))

    def find_npc(self, ref: int | str) -> NPCNode | None:
        return self._npcs.get(str(ref))

    def find_monster(self, ref: int | str) -> MonsterNode | None:
        return self._monsters.get(str(ref))

    def find_item(self, ref: int | str) -> ItemNode | None:
        return self._items.get(str(ref))

    def find_equipment(self, ref: int | str) -> EquipmentNode | None:
        return self._equipment.get(str(ref))

    def find_quest(self, ref: int | str) -> QuestNode | None:
        return self._quests.get(str(ref))

    def find_story_lore(self, ref: int | str) -> StoryLoreNode | None:
        return self._story_lore.get(str(ref))

    @property
    def maps(self) -> list[MapNode]:
        seen: dict[str, MapNode] = {}
        for node in self._maps.values():
            seen.setdefault(str(node.map_id), node)
        return list(seen.values())

    @property
    def npcs(self) -> list[NPCNode]:
        seen: dict[str, NPCNode] = {}
        for node in self._npcs.values():
            seen.setdefault(str(node.npc_id), node)
        return list(seen.values())

    @property
    def monsters(self) -> list[MonsterNode]:
        seen: dict[str, MonsterNode] = {}
        for node in self._monsters.values():
            seen.setdefault(str(node.monster_id), node)
        return list(seen.values())

    @property
    def items(self) -> list[ItemNode]:
        seen: dict[str, ItemNode] = {}
        for node in self._items.values():
            seen.setdefault(str(node.item_id), node)
        return list(seen.values())

    @property
    def equipment(self) -> list[EquipmentNode]:
        seen: dict[str, EquipmentNode] = {}
        for node in self._equipment.values():
            seen.setdefault(str(node.equipment_id), node)
        return list(seen.values())

    @property
    def quests(self) -> list[QuestNode]:
        seen: dict[str, QuestNode] = {}
        for node in self._quests.values():
            seen.setdefault(str(node.quest_id), node)
        return list(seen.values())

    @property
    def story_lore(self) -> list[StoryLoreNode]:
        seen: dict[str, StoryLoreNode] = {}
        for node in self._story_lore.values():
            seen.setdefault(str(node.lore_id), node)
        return list(seen.values())

    def npcs_in_map(self, map_id: int | str) -> list[NPCNode]:
        result: list[NPCNode] = []
        for relation in self._relations_index.get(("map", str(map_id)), []):
            if (
                relation.relation_type is RelationType.CONTAINS
                and relation.target == "npc"
            ):
                node = self._npcs.get(str(relation.target_id))
                if node is not None:
                    result.append(node)
        return result

    def monsters_in_map(self, map_id: int | str) -> list[MonsterNode]:
        result: list[MonsterNode] = []
        for relation in self._relations_index.get(("map", str(map_id)), []):
            if (
                relation.relation_type is RelationType.SPAWNS
                and relation.target == "monster"
            ):
                node = self._monsters.get(str(relation.target_id))
                if node is not None:
                    result.append(node)
        return result

    def relations_for(self, entity_type: str, entity_id: int | str) -> list[Relation]:
        return list(
            self._relations_index.get((entity_type, str(entity_id)), [])
        )

    def all_relations(self) -> list[Relation]:
        return list(self._relations)

    def _node_for(self, entity_type: str, entity_id: int | str):
        finders = {
            "map": self.find_map,
            "npc": self.find_npc,
            "monster": self.find_monster,
            "item": self.find_item,
            "equipment": self.find_equipment,
            "quest": self.find_quest,
            "story_lore": self.find_story_lore,
        }
        finder = finders.get(entity_type.strip().lower())
        return finder(entity_id) if finder else None

    def relation_references_for(
        self,
        entity_type: str,
        entity_id: int | str,
        *,
        include_incoming: bool = True,
    ) -> list[RelationReference]:
        """Return neighboring entities without proposing any action."""
        source_type = entity_type.strip().lower()
        source_id = str(entity_id)
        records: list[RelationReference] = []
        for relation in self._relations:
            target_type = relation.target.strip().lower()
            if relation.source == source_type and str(relation.source_id) == source_id:
                node = self._node_for(target_type, relation.target_id)
                if node is not None:
                    records.append(
                        RelationReference(
                            entity_type=target_type,
                            entity_id=relation.target_id,
                            name=node.name,
                            relation_type=relation.relation_type,
                            confidence=relation.confidence,
                            provenance=relation.provenance,
                        )
                    )
            if (
                include_incoming
                and relation.target == source_type
                and str(relation.target_id) == source_id
            ):
                node = self._node_for(relation.source, relation.source_id)
                if node is not None:
                    records.append(
                        RelationReference(
                            entity_type=relation.source,
                            entity_id=relation.source_id,
                            name=node.name,
                            relation_type=relation.relation_type,
                            confidence=relation.confidence,
                            provenance=relation.provenance,
                        )
                    )
        return records

    def query_related(
        self,
        entity_type: str,
        entity_id: int | str,
    ) -> dict[str, list[RelationReference]]:
        """Group deterministic neighboring references by requested entity type."""
        grouped = {"npcs": [], "items": [], "maps": [], "quests": []}
        key_map = {"npc": "npcs", "item": "items", "map": "maps", "quest": "quests"}
        seen: set[tuple[str, str, str, str]] = set()
        for reference in self.relation_references_for(entity_type, entity_id):
            key = (
                reference.entity_type,
                str(reference.entity_id),
                reference.relation_type.value,
                reference.provenance.source_id,
            )
            if reference.entity_type in key_map and key not in seen:
                grouped[key_map[reference.entity_type]].append(reference)
                seen.add(key)
        return grouped

    def related_npcs(self, entity_type: str, entity_id: int | str) -> list[RelationReference]:
        return self.query_related(entity_type, entity_id)["npcs"]

    def related_items(self, entity_type: str, entity_id: int | str) -> list[RelationReference]:
        return self.query_related(entity_type, entity_id)["items"]

    def related_maps(self, entity_type: str, entity_id: int | str) -> list[RelationReference]:
        return self.query_related(entity_type, entity_id)["maps"]

    def related_quests(self, entity_type: str, entity_id: int | str) -> list[RelationReference]:
        return self.query_related(entity_type, entity_id)["quests"]
