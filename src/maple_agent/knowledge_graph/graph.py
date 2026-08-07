"""KnowledgeGraph:节点与关系查询(只读)。"""

from __future__ import annotations

from collections import defaultdict

from maple_agent.knowledge_graph.models import (
    ItemNode,
    MapNode,
    MonsterNode,
    NPCNode,
    Relation,
    RelationType,
)


class KnowledgeGraph:
    """基于节点与关系构建的知识图谱(只读查询)。"""

    def __init__(
        self,
        maps: list[MapNode] | None = None,
        npcs: list[NPCNode] | None = None,
        monsters: list[MonsterNode] | None = None,
        items: list[ItemNode] | None = None,
        relations: list[Relation] | None = None,
    ) -> None:
        self._maps: dict[str, MapNode] = {}
        self._npcs: dict[str, NPCNode] = {}
        self._monsters: dict[str, MonsterNode] = {}
        self._items: dict[str, ItemNode] = {}
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
