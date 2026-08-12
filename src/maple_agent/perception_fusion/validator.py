"""PerceptionFusionValidator:融合参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.perception_fusion.models import PerceptionFusionReference


class PerceptionFusionVerdict(StrEnum):
    """融合校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class PerceptionFusionValidationResult(BaseModel):
    """融合校验结果。"""

    verdict: PerceptionFusionVerdict
    issues: list[str] = Field(default_factory=list)


class PerceptionFusionValidator:
    """检查融合对象完整 / 数值范围 / 冲突与缺失信号。"""

    def validate(
        self,
        reference: PerceptionFusionReference,
    ) -> PerceptionFusionValidationResult:
        if not reference.fusion_id:
            return PerceptionFusionValidationResult(
                verdict=PerceptionFusionVerdict.BLOCKED,
                issues=["missing fusion id"],
            )
        if not (0 <= reference.fused_confidence <= 1) or not (
            0 <= reference.consistency_score <= 1
        ):
            return PerceptionFusionValidationResult(
                verdict=PerceptionFusionVerdict.BLOCKED,
                issues=["value out of range"],
            )
        if not reference.source_inputs:
            return PerceptionFusionValidationResult(
                verdict=PerceptionFusionVerdict.BLOCKED,
                issues=["no source inputs"],
            )
        issues: list[str] = []
        if reference.conflicts:
            issues.append("conflicts present")
        if reference.missing_signals:
            issues.append("missing signals")
        if reference.fused_confidence < 0.5:
            issues.append("low fusion confidence")
        verdict = (
            PerceptionFusionVerdict.VALID
            if not issues
            else PerceptionFusionVerdict.WARNING
        )
        return PerceptionFusionValidationResult(
            verdict=verdict,
            issues=issues,
        )
