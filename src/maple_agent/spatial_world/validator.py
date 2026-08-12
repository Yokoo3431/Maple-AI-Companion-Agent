"""SpatialWorldValidator:空间参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.spatial_world.models import SpatialWorldReference


class SpatialWorldVerdict(StrEnum):
    """空间校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class SpatialWorldValidationResult(BaseModel):
    """空间校验结果。"""

    verdict: SpatialWorldVerdict
    issues: list[str] = Field(default_factory=list)


class SpatialWorldValidator:
    """检查当前地图 / 空间数据 / 置信度。"""

    def validate(
        self,
        reference: SpatialWorldReference,
    ) -> SpatialWorldValidationResult:
        if not (0 <= reference.spatial_confidence <= 1):
            return SpatialWorldValidationResult(
                verdict=SpatialWorldVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        issues: list[str] = []
        if not reference.current_map:
            issues.append("missing current map")
        if not reference.nearby_points:
            issues.append("no spatial data")
        if not reference.portals:
            issues.append("no portals")
        if not reference.npc_positions:
            issues.append("no npc locations")
        if reference.spatial_confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            SpatialWorldVerdict.VALID
            if not issues
            else SpatialWorldVerdict.WARNING
        )
        return SpatialWorldValidationResult(
            verdict=verdict,
            issues=issues,
        )
