"""MemoryIndex:记忆节点索引(只读检索接口)。"""

from __future__ import annotations

from maple_agent.memory_graph.models import MemoryNode, MemoryType


class MemoryIndex:
    """内存索引;add 构建,查询接口只读。"""

    def __init__(
        self,
        nodes: list[MemoryNode] | None = None,
    ) -> None:
        self._nodes: list[MemoryNode] = list(nodes or [])
        self._by_id = {
            node.memory_id: node for node in self._nodes
        }

    def add(self, node: MemoryNode) -> None:
        if node.memory_id in self._by_id:
            return
        self._nodes.append(node)
        self._by_id[node.memory_id] = node

    def add_many(self, nodes: list[MemoryNode]) -> None:
        for node in nodes:
            self.add(node)

    def get(self, memory_id: str) -> MemoryNode | None:
        return self._by_id.get(memory_id)

    def all(self) -> list[MemoryNode]:
        return list(self._nodes)

    def count(self) -> int:
        return len(self._nodes)

    def by_type(self, memory_type: MemoryType) -> list[MemoryNode]:
        return [
            node
            for node in self._nodes
            if node.memory_type is memory_type
        ]

    def by_context(self, context: dict) -> list[MemoryNode]:
        return [
            node
            for node in self._nodes
            if all(
                node.context.get(key) == value
                for key, value in context.items()
            )
        ]

    def related(self, node: MemoryNode) -> list[MemoryNode]:
        results: list[MemoryNode] = []
        for relation in node.relations:
            target = self._by_id.get(relation.target_id)
            if target is not None:
                results.append(target)
        return results
