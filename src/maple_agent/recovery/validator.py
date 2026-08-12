"""RecoveryValidator:恢复建议校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.recovery.models import (
    FailureType,
    RecoveryReference,
    RecoveryType,
)


class RecoveryVerdict(StrEnum):
    """恢复校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class RecoveryValidationResult(BaseModel):
    """恢复校验结果。"""

    verdict: RecoveryVerdict
    issues: list[str] = Field(default_factory=list)


class RecoveryValidator:
    """检查恢复对象完整 / 类型合法 / 置信度范围。"""

    def validate(
        self,
        reference: RecoveryReference,
    ) -> RecoveryValidationResult:
        if not reference.recovery_id:
            return RecoveryValidationResult(
                verdict=RecoveryVerdict.BLOCKED,
                issues=["missing recovery id"],
            )
        if not (0 <= reference.confidence <= 1):
            return RecoveryValidationResult(
                verdict=RecoveryVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if (
            reference.failure_type not in set(FailureType)
            or reference.recovery_type not in set(RecoveryType)
        ):
            return RecoveryValidationResult(
                verdict=RecoveryVerdict.BLOCKED,
                issues=["invalid recovery type"],
            )
        issues: list[str] = []
        if reference.failure_type is FailureType.UNKNOWN:
            issues.append("unknown failure")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            RecoveryVerdict.VALID if not issues else RecoveryVerdict.WARNING
        )
        return RecoveryValidationResult(verdict=verdict, issues=issues)
