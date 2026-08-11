"""EnvironmentReasoningValidator:推理结果校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.environment_reasoning.models import (
    EnvironmentInterpretation,
    EnvironmentRiskReference,
    OpportunityReference,
    OpportunityType,
)


class EnvironmentReasoningValidationResult(BaseModel):
    """环境推理校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class EnvironmentReasoningValidator:
    """检查语义解释 / 机会与风险一致性。"""

    def validate(
        self,
        *,
        interpretation: EnvironmentInterpretation,
        opportunities: list[OpportunityReference],
        risk_reference: EnvironmentRiskReference,
    ) -> EnvironmentReasoningValidationResult:
        issues: list[str] = []
        if not interpretation.meaning:
            issues.append("缺少语义解释")
        if risk_reference.risk_level not in ("LOW", "MEDIUM", "HIGH"):
            issues.append("非法风险等级")
        if risk_reference.risk_level == "HIGH":
            for opportunity in opportunities:
                if opportunity.opportunity_type in (
                    OpportunityType.SAFE_AREA,
                    OpportunityType.TASK_PROGRESS,
                ):
                    issues.append(
                        "高风险环境误报机会: "
                        f"{opportunity.opportunity_type.value}"
                    )
        return EnvironmentReasoningValidationResult(
            valid=not issues,
            issues=issues,
        )
