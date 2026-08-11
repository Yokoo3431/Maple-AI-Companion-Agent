"""DecisionReferenceValidator:决策参考校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.decision_reference.models import (
    DecisionReference,
    DecisionScore,
)


class DecisionReferenceValidationResult(BaseModel):
    """决策参考校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class DecisionReferenceValidator:
    """检查选项 / 风险等级 / 评分 / 高风险一致性。"""

    def validate(
        self,
        *,
        reference: DecisionReference,
        score: DecisionScore,
    ) -> DecisionReferenceValidationResult:
        issues: list[str] = []
        if (
            not reference.recommended_options
            and not reference.alternative_options
        ):
            issues.append("决策参考无选项")
        if reference.risk_level not in ("LOW", "MEDIUM", "HIGH"):
            issues.append("非法风险等级")
        if not (0 <= score.decision_score <= 1):
            issues.append("决策评分越界")
        if (
            reference.risk_level == "HIGH"
            and reference.recommended_options
        ):
            issues.append("高风险仍推荐选项")
        return DecisionReferenceValidationResult(
            valid=not issues,
            issues=issues,
        )
