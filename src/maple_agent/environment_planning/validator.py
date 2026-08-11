"""EnvironmentPlanningValidator:规划参考校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.environment_reasoning.models import (
    EnvironmentRiskReference,
)


class EnvironmentPlanningValidationResult(BaseModel):
    """环境规划校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class EnvironmentPlanningValidator:
    """检查参考非空 / 风险与推荐一致性。"""

    def validate(
        self,
        *,
        reference: EnvironmentPlanningReference,
        risk_reference: EnvironmentRiskReference,
    ) -> EnvironmentPlanningValidationResult:
        issues: list[str] = []
        if (
            not reference.recommended_goals
            and not reference.blocked_goals
            and not reference.priority_adjustments
        ):
            issues.append("规划参考为空")
        if (
            risk_reference.risk_level == "HIGH"
            and reference.recommended_goals
        ):
            issues.append("高风险环境仍推荐目标")
        if (
            risk_reference.risk_level == "HIGH"
            and not reference.blocked_goals
        ):
            issues.append("高风险环境缺少阻断目标")
        return EnvironmentPlanningValidationResult(
            valid=not issues,
            issues=issues,
        )
