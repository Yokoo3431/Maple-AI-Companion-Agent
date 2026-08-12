"""MapleKnowledgeValidator:领域知识校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    KnowledgeRelationType,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)


class MapleKnowledgeVerdict(StrEnum):
    """知识校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class MapleKnowledgeValidationResult(BaseModel):
    """知识校验结果。"""

    verdict: MapleKnowledgeVerdict
    issues: list[str] = Field(default_factory=list)


class MapleKnowledgeValidator:
    """检查实体完整 / 类型 / 置信度 / 关系完整性。"""

    def validate_entity(
        self,
        entity: MapleKnowledgeEntity,
    ) -> MapleKnowledgeValidationResult:
        if entity.knowledge_type not in set(MapleKnowledgeType):
            return MapleKnowledgeValidationResult(
                verdict=MapleKnowledgeVerdict.BLOCKED,
                issues=["invalid type"],
            )
        if not (0 <= entity.confidence <= 1):
            return MapleKnowledgeValidationResult(
                verdict=MapleKnowledgeVerdict.BLOCKED,
                issues=["confidence outside 0-1"],
            )
        if not entity.name:
            return MapleKnowledgeValidationResult(
                verdict=MapleKnowledgeVerdict.BLOCKED,
                issues=["缺少名称"],
            )
        issues: list[str] = []
        if not entity.description:
            issues.append("missing description")
        if entity.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            MapleKnowledgeVerdict.VALID
            if not issues
            else MapleKnowledgeVerdict.WARNING
        )
        return MapleKnowledgeValidationResult(
            verdict=verdict,
            issues=issues,
        )

    def validate_relation(
        self,
        relation: KnowledgeRelation,
        graph: MapleKnowledgeGraph | None = None,
    ) -> MapleKnowledgeValidationResult:
        if relation.relation_type not in set(KnowledgeRelationType):
            return MapleKnowledgeValidationResult(
                verdict=MapleKnowledgeVerdict.BLOCKED,
                issues=["invalid type"],
            )
        if not (0 <= relation.confidence <= 1):
            return MapleKnowledgeValidationResult(
                verdict=MapleKnowledgeVerdict.BLOCKED,
                issues=["confidence outside 0-1"],
            )
        if graph is not None:
            if (
                graph.base.get_entity(relation.source_id) is None
                or graph.base.get_entity(relation.target_id) is None
            ):
                return MapleKnowledgeValidationResult(
                    verdict=MapleKnowledgeVerdict.BLOCKED,
                    issues=["broken relation"],
                )
        return MapleKnowledgeValidationResult(
            verdict=MapleKnowledgeVerdict.VALID,
            issues=[],
        )
