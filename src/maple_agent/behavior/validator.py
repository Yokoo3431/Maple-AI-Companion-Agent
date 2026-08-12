"""BehaviorValidator:行为参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.behavior.models import BehaviorReference


class BehaviorVerdict(StrEnum):
    """行为校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class BehaviorValidationResult(BaseModel):
    """行为校验结果。"""

    verdict: BehaviorVerdict
    issues: list[str] = Field(default_factory=list)


class BehaviorValidator:
    """检查行为完整 / 目标 / 置信度。"""

    def validate(
        self,
        reference: BehaviorReference,
    ) -> BehaviorValidationResult:
        if not reference.behavior_id:
            return BehaviorValidationResult(
                verdict=BehaviorVerdict.BLOCKED,
                issues=["missing behavior id"],
            )
        if not (0 <= reference.confidence <= 1):
            return BehaviorValidationResult(
                verdict=BehaviorVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        issues: list[str] = []
        if not reference.goal_reference:
            issues.append("missing goal reference")
        if not reference.behavior_steps:
            issues.append("empty behavior steps")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            BehaviorVerdict.VALID if not issues else BehaviorVerdict.WARNING
        )
        return BehaviorValidationResult(verdict=verdict, issues=issues)
