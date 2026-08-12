"""KnowledgeRelationBuilder:知识关系构造(只读)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    KnowledgeRelationType,
)


class KnowledgeRelationBuilder:
    """按类型构造知识关系。"""

    @staticmethod
    def build(
        *,
        source_id: str,
        target_id: str,
        relation_type: KnowledgeRelationType,
        confidence: float = 0.9,
    ) -> KnowledgeRelation:
        return KnowledgeRelation(
            relation_id=new_id(),
            source_id=source_id,
            target_id=target_id,
            relation_type=relation_type,
            confidence=round(confidence, 4),
        )

    def build_from_pairs(
        self,
        pairs: list[dict],
    ) -> list[KnowledgeRelation]:
        relations: list[KnowledgeRelation] = []
        for pair in pairs:
            relations.append(
                self.build(
                    source_id=pair["source_id"],
                    target_id=pair["target_id"],
                    relation_type=KnowledgeRelationType(
                        pair["relation_type"]
                    ),
                    confidence=pair.get("confidence", 0.9),
                )
            )
        return relations
