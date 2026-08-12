"""ReflexValidator:反射参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.reflex.models import ReflexReference, ReflexStateType


class ReflexVerdict(StrEnum):
    """反射校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class ReflexValidationResult(BaseModel):
    """反射校验结果。"""

    verdict: ReflexVerdict
    issues: list[str] = Field(default_factory=list)


class ReflexValidator:
    """检查状态合法 / 置信度范围 / 数据结构完整。"""

    def validate(
        self,
        reference: ReflexReference,
    ) -> ReflexValidationResult:
        if not reference.reflex_id:
            return ReflexValidationResult(
                verdict=ReflexVerdict.BLOCKED,
                issues=["missing reflex id"],
            )
        if not (0 <= reference.confidence <= 1):
            return ReflexValidationResult(
                verdict=ReflexVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if reference.state not in set(ReflexStateType):
            return ReflexValidationResult(
                verdict=ReflexVerdict.BLOCKED,
                issues=["invalid state"],
            )
        for item in (reference.hp_reference, reference.mp_reference):
            if (
                item is not None
                and item.ratio is not None
                and not (0 <= item.ratio <= 1)
            ):
                return ReflexValidationResult(
                    verdict=ReflexVerdict.BLOCKED,
                    issues=["hp/mp ratio out of range"],
                )
        issues: list[str] = []
        if reference.hp_reference is None or reference.mp_reference is None:
            issues.append("missing hp/mp reference")
        elif (
            reference.hp_reference.ratio is None
            or reference.mp_reference.ratio is None
        ):
            issues.append("missing ratio data")
        if reference.state is ReflexStateType.UNKNOWN:
            issues.append("state unknown")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            ReflexVerdict.VALID if not issues else ReflexVerdict.WARNING
        )
        return ReflexValidationResult(verdict=verdict, issues=issues)
