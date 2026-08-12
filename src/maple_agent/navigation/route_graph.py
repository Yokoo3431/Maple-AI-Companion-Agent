"""RouteGraph:地图连接图 + BFS 路径搜索(确定性,无 LLM)。"""

from __future__ import annotations

from collections import deque

from maple_agent.world_knowledge.models import MapConnectionReference


class RouteGraph:
    """以地图为节点的无向图,支持 BFS 路径搜索。"""

    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._edges: dict[str, set[str]] = {}

    def add_node(self, name: str) -> None:
        self._nodes.add(name)
        self._edges.setdefault(name, set())

    def add_edge(self, source: str, target: str) -> None:
        self.add_node(source)
        self.add_node(target)
        self._edges[source].add(target)
        self._edges[target].add(source)

    @classmethod
    def build_from_connections(
        cls,
        connections: list[MapConnectionReference],
    ) -> RouteGraph:
        graph = cls()
        for connection in connections:
            graph.add_edge(
                connection.source_map,
                connection.target_map,
            )
        return graph

    def find_path(self, start: str, target: str) -> list[str]:
        if start == target:
            return [start]
        if start not in self._nodes or target not in self._nodes:
            return []
        queue: deque[tuple[str, list[str]]] = deque([(start, [start])])
        visited = {start}
        while queue:
            node, path = queue.popleft()
            for neighbor in sorted(self._edges.get(node, set())):
                if neighbor in visited:
                    continue
                next_path = path + [neighbor]
                if neighbor == target:
                    return next_path
                visited.add(neighbor)
                queue.append((neighbor, next_path))
        return []

    def node_count(self) -> int:
        return len(self._nodes)
