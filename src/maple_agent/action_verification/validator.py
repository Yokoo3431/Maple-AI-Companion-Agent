"""ActionOutcomeValidator:结果验证参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.action_verification.models import (
    ActionOutcomeReference,
    ActionOutcomeStatus,
)


class ActionOutcomeVerdict(StrEnum):
    """结果校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class ActionOutcomeValidationResult(BaseModel):
    """结果校验结论对象。"""

    verdict: ActionOutcomeVerdict
    issues: list[str] = Field(default_factory=list)


class ActionOutcomeValidator:
    """检查结果对象结构 / 状态合法 / 置信度范围。"""

    def validate(
        self,
        reference: ActionOutcomeReference,
    ) -> ActionOutcomeValidationResult:
        if not reference.outcome_id:
            return ActionOutcomeValidationResult(
                verdict=ActionOutcomeVerdict.BLOCKED,
                issues=["missing outcome id"],
            )
        if not (0 <= reference.confidence <= 1):
            return ActionOutcomeValidationResult(
                verdict=ActionOutcomeVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if reference.status not in set(ActionOutcomeStatus):
            return ActionOutcomeValidationResult(
                verdict=ActionOutcomeVerdict.BLOCKED,
                issues=["invalid status"],
            )
        if (
            reference.expected_outcome is None
            or not reference.expected_outcome.expectation_id
        ):
            return ActionOutcomeValidationResult(
                verdict=ActionOutcomeVerdict.BLOCKED,
                issues=["broken expectation"],
            )
        issues: list[str] = []
        if reference.status is ActionOutcomeStatus.INCONCLUSIVE:
            issues.append("inconclusive outcome")
        if not reference.evidence:
            issues.append("missing evidence")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            ActionOutcomeVerdict.VALID
            if not issues
            else ActionOutcomeVerdict.WARNING
        )
        return ActionOutcomeValidationResult(
            verdict=verdict,
            issues=issues,
        )
