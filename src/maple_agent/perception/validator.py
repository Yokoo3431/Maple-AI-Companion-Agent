"""PerceptionValidator:感知参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.perception.models import (
    MaplePerceptionReference,
    PerceivedEntityType,
    VisualObservation,
)


class PerceptionVerdict(StrEnum):
    """感知校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class PerceptionValidationResult(BaseModel):
    """感知校验结果。"""

    verdict: PerceptionVerdict
    issues: list[str] = Field(default_factory=list)


class PerceptionValidator:
    """检查观察存在 / 置信度 / 实体类型 / 知识匹配。"""

    def validate(
        self,
        observation: VisualObservation,
        reference: MaplePerceptionReference,
    ) -> PerceptionValidationResult:
        if not observation.observation_id:
            return PerceptionValidationResult(
                verdict=PerceptionVerdict.BLOCKED,
                issues=["malformed observation"],
            )
        if not (0 <= observation.confidence <= 1):
            return PerceptionValidationResult(
                verdict=PerceptionVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        for entity in reference.visible_entities:
            if entity.entity_type not in set(PerceivedEntityType):
                return PerceptionValidationResult(
                    verdict=PerceptionVerdict.BLOCKED,
                    issues=["invalid entity type"],
                )
        issues: list[str] = []
        if not reference.related_knowledge or not any(
            reference.related_knowledge.values()
        ):
            issues.append("missing knowledge match")
        if observation.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            PerceptionVerdict.VALID
            if not issues
            else PerceptionVerdict.WARNING
        )
        return PerceptionValidationResult(
            verdict=verdict,
            issues=issues,
        )
