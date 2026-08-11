"""SemanticRelationBuilder:语义关系构造(只读)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.memory_association.models import (
    SemanticMemoryRelation,
    SemanticRelationType,
)
from maple_agent.memory_graph.models import MemoryNode


class SemanticRelationBuilder:
    """按类型构造语义关系。"""

    def build(
        self,
        *,
        relation_type: SemanticRelationType,
        source: MemoryNode,
        target: MemoryNode,
        confidence: float,
        reasoning: str,
    ) -> SemanticMemoryRelation:
        return SemanticMemoryRelation(
            relation_id=new_id(),
            source_memory=source.memory_id,
            target_memory=target.memory_id,
            relation_type=relation_type,
            confidence=round(confidence, 4),
            reasoning=reasoning,
            context={
                "source_type": source.memory_type.value,
                "target_type": target.memory_type.value,
            },
        )
