"""SemanticAssociationValidator:语义关联校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.memory_association.models import (
    SemanticMemoryReference,
    SemanticMemoryRelation,
    SemanticRelationType,
)


class SemanticMemoryVerdict(StrEnum):
    """语义校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class SemanticMemoryValidationResult(BaseModel):
    """语义校验结果。"""

    verdict: SemanticMemoryVerdict
    issues: list[str] = Field(default_factory=list)


class SemanticAssociationValidator:
    """检查关系类型 / 置信度 / 引用完整性 / 弱关联。"""

    def validate_relation(
        self,
        relation: SemanticMemoryRelation,
    ) -> SemanticMemoryValidationResult:
        if relation.relation_type not in set(SemanticRelationType):
            return SemanticMemoryValidationResult(
                verdict=SemanticMemoryVerdict.BLOCKED,
                issues=["非法关系类型"],
            )
        if not (0 <= relation.confidence <= 1):
            return SemanticMemoryValidationResult(
                verdict=SemanticMemoryVerdict.BLOCKED,
                issues=["confidence 越界"],
            )
        if not relation.source_memory or not relation.target_memory:
            return SemanticMemoryValidationResult(
                verdict=SemanticMemoryVerdict.BLOCKED,
                issues=["corrupted: 缺少记忆引用"],
            )
        if relation.confidence < 0.4:
            return SemanticMemoryValidationResult(
                verdict=SemanticMemoryVerdict.WARNING,
                issues=["弱关联"],
            )
        return SemanticMemoryValidationResult(
            verdict=SemanticMemoryVerdict.VALID,
            issues=[],
        )

    def validate_reference(
        self,
        reference: SemanticMemoryReference,
    ) -> SemanticMemoryValidationResult:
        empty = not (
            reference.related_experiences
            or reference.failure_patterns
            or reference.decision_hints
            or reference.preference_alignment
            or reference.world_context
        )
        if empty:
            return SemanticMemoryValidationResult(
                verdict=SemanticMemoryVerdict.BLOCKED,
                issues=["corrupted memory reference: 无关联"],
            )
        return SemanticMemoryValidationResult(
            verdict=SemanticMemoryVerdict.VALID,
            issues=[],
        )
