"""MemoryRelationBuilder:记忆关系构建(只读)。"""

from __future__ import annotations

from maple_agent.memory_graph.models import (
    MemoryNode,
    MemoryRelation,
    MemoryRelationType,
)


class MemoryRelationBuilder:
    """自动为同上下文记忆建立相似关系。"""

    def auto_link(self, nodes: list[MemoryNode]) -> list[MemoryNode]:
        updated: list[MemoryNode] = []
        for node in nodes:
            relations = list(node.relations)
            for other in nodes:
                if other.memory_id == node.memory_id:
                    continue
                if not self._same_context(node, other):
                    continue
                if not any(
                    relation.target_id == other.memory_id
                    for relation in relations
                ):
                    relations.append(
                        MemoryRelation(
                            relation_type=MemoryRelationType.SIMILAR_TO,
                            target_id=other.memory_id,
                        )
                    )
            updated.append(
                node.model_copy(update={"relations": relations})
            )
        return updated

    @staticmethod
    def _same_context(
        left: MemoryNode,
        right: MemoryNode,
    ) -> bool:
        shared = set(left.context) & set(right.context)
        return any(
            left.context[key] == right.context[key] for key in shared
        )
