"""SafetyGateValidator:安全审核参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)


class SafetyGateVerdict(StrEnum):
    """安全审核校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class SafetyGateValidationResult(BaseModel):
    """安全审核校验结果。"""

    verdict: SafetyGateVerdict
    issues: list[str] = Field(default_factory=list)


class SafetyGateValidator:
    """检查审核对象完整 / 决策合法 / 置信度范围。"""

    def validate(
        self,
        reference: SafetyEvaluationReference,
    ) -> SafetyGateValidationResult:
        if not reference.evaluation_id:
            return SafetyGateValidationResult(
                verdict=SafetyGateVerdict.BLOCKED,
                issues=["missing evaluation id"],
            )
        if not (0 <= reference.confidence <= 1):
            return SafetyGateValidationResult(
                verdict=SafetyGateVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if reference.decision not in set(SafetyDecisionType):
            return SafetyGateValidationResult(
                verdict=SafetyGateVerdict.BLOCKED,
                issues=["invalid decision"],
            )
        if not reference.source_action:
            return SafetyGateValidationResult(
                verdict=SafetyGateVerdict.WARNING,
                issues=["missing source action"],
            )
        return SafetyGateValidationResult(
            verdict=SafetyGateVerdict.VALID,
            issues=[],
        )
