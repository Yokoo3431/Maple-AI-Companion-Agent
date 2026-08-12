"""NavigationValidator:导航参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.navigation.models import NavigationReference


class NavigationVerdict(StrEnum):
    """导航校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class NavigationValidationResult(BaseModel):
    """导航校验结果。"""

    verdict: NavigationVerdict
    issues: list[str] = Field(default_factory=list)


class NavigationValidator:
    """检查起点/目标/路由/成本/置信度。"""

    def validate(
        self,
        reference: NavigationReference,
    ) -> NavigationValidationResult:
        if not reference.navigation_id:
            return NavigationValidationResult(
                verdict=NavigationVerdict.BLOCKED,
                issues=["missing navigation id"],
            )
        if not (0 <= reference.confidence <= 1) or (
            reference.estimated_cost < 0
        ):
            return NavigationValidationResult(
                verdict=NavigationVerdict.BLOCKED,
                issues=["value out of range"],
            )
        if not reference.start_location or not reference.target_location:
            return NavigationValidationResult(
                verdict=NavigationVerdict.BLOCKED,
                issues=["missing start or target"],
            )
        issues: list[str] = []
        if not reference.route_steps:
            issues.append("empty route")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            NavigationVerdict.VALID
            if not issues
            else NavigationVerdict.WARNING
        )
        return NavigationValidationResult(verdict=verdict, issues=issues)
