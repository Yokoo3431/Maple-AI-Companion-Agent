"""MapleContextValidator:认知上下文校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.maple_context.models import MapleCompanionContextReference


class MapleContextVerdict(StrEnum):
    """上下文校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class MapleContextValidationResult(BaseModel):
    """上下文校验结果。"""

    verdict: MapleContextVerdict
    issues: list[str] = Field(default_factory=list)


class MapleContextValidator:
    """检查结构完整 / 置信度 / 必需上下文 / 可选信息。"""

    def validate(
        self,
        reference: MapleCompanionContextReference,
    ) -> MapleContextValidationResult:
        if not (0 <= reference.confidence <= 1):
            return MapleContextValidationResult(
                verdict=MapleContextVerdict.BLOCKED,
                issues=["invalid confidence"],
            )
        if (
            reference.player_context is None
            or reference.world_context is None
        ):
            return MapleContextValidationResult(
                verdict=MapleContextVerdict.BLOCKED,
                issues=["missing required context"],
            )
        issues: list[str] = []
        if reference.goal_context is None:
            issues.append("缺少目标上下文")
        elif not reference.goal_context.active_goal:
            issues.append("缺少目标信息")
        if reference.cognitive_context is None:
            issues.append("缺少认知上下文")
        if not reference.summary:
            issues.append("缺少摘要")
        verdict = (
            MapleContextVerdict.VALID
            if not issues
            else MapleContextVerdict.WARNING
        )
        return MapleContextValidationResult(
            verdict=verdict,
            issues=issues,
        )
