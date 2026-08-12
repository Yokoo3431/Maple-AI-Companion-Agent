"""MapGraph:确定性世界地图图谱(无 LLM)。"""

from __future__ import annotations

from maple_agent.world_knowledge.models import (
    MapConnectionReference,
    MapNodeReference,
)


class MapGraph:
    """地图节点与连接存储,提供确定性查询。"""

    def __init__(self) -> None:
        self._nodes: dict[str, MapNodeReference] = {}
        self._connections: list[MapConnectionReference] = []

    def add_node(self, node: MapNodeReference) -> None:
        self._nodes[node.map_id] = node

    def add_connection(
        self,
        connection: MapConnectionReference,
    ) -> None:
        self._connections.append(connection)

    def find_map(self, name: str) -> MapNodeReference | None:
        normalized = name.strip().lower()
        for node in self._nodes.values():
            if node.map_name.strip().lower() == normalized:
                return node
            if any(
                alias.strip().lower() == normalized
                for alias in node.aliases
            ):
                return node
        return None

    def find_connections(
        self,
        map_name: str,
    ) -> list[MapConnectionReference]:
        return [
            connection
            for connection in self._connections
            if connection.source_map == map_name
            or connection.target_map == map_name
        ]

    def find_reachable_maps(self, map_name: str) -> list[str]:
        reachable: list[str] = []
        for connection in self._connections:
            if connection.source_map == map_name:
                reachable.append(connection.target_map)
            elif connection.target_map == map_name:
                reachable.append(connection.source_map)
        return list(dict.fromkeys(reachable))

    def find_related_npcs(self, map_name: str) -> list[str]:
        node = self.find_map(map_name)
        return list(node.npc_references) if node is not None else []

    def find_related_monsters(self, map_name: str) -> list[str]:
        node = self.find_map(map_name)
        return list(node.monster_references) if node is not None else []

    def find_related_quests(self, map_name: str) -> list[str]:
        node = self.find_map(map_name)
        return list(node.quest_references) if node is not None else []

    def known_map_names(self) -> list[str]:
        return sorted(
            node.map_name for node in self._nodes.values()
        )

    def node_count(self) -> int:
        return len(self._nodes)

    def connection_count(self) -> int:
        return len(self._connections)
