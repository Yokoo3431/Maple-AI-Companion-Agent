"""WorldKnowledgeValidator:世界知识参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.world_knowledge.models import WorldKnowledgeReference


class WorldKnowledgeVerdict(StrEnum):
    """世界知识校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class WorldKnowledgeValidationResult(BaseModel):
    """世界知识校验结果。"""

    verdict: WorldKnowledgeVerdict
    issues: list[str] = Field(default_factory=list)


class WorldKnowledgeValidator:
    """检查地图 / 可达 / 关联 / 置信度。"""

    def validate(
        self,
        reference: WorldKnowledgeReference,
    ) -> WorldKnowledgeValidationResult:
        if not (0 <= reference.confidence <= 1):
            return WorldKnowledgeValidationResult(
                verdict=WorldKnowledgeVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if not reference.known_maps:
            return WorldKnowledgeValidationResult(
                verdict=WorldKnowledgeVerdict.BLOCKED,
                issues=["empty world graph"],
            )
        issues: list[str] = []
        if not reference.current_map:
            issues.append("missing current map")
        elif reference.current_map not in reference.known_maps:
            issues.append("unknown current map")
        if not reference.reachable_maps:
            issues.append("no reachable maps")
        if not reference.related_npcs:
            issues.append("no related npc")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            WorldKnowledgeVerdict.VALID
            if not issues
            else WorldKnowledgeVerdict.WARNING
        )
        return WorldKnowledgeValidationResult(
            verdict=verdict,
            issues=issues,
        )
