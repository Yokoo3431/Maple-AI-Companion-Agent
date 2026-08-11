"""HumanAlignmentValidator:对齐结果校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.human_alignment.models import (
    AlignmentScore,
    HumanAlignedDecisionReference,
)


class HumanAlignmentValidationResult(BaseModel):
    """对齐校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class HumanAlignmentValidator:
    """检查评分一致性 / 分数范围 / 拒绝项冲突。"""

    def validate(
        self,
        *,
        reference: HumanAlignedDecisionReference,
        alignment: AlignmentScore,
    ) -> HumanAlignmentValidationResult:
        issues: list[str] = []
        if reference.alignment_score != alignment.alignment_score:
            issues.append("对齐分数不一致")
        if not (0 <= alignment.alignment_score <= 1):
            issues.append("对齐分数越界")
        rejected_set = set(reference.rejected_options)
        preferred_ids = {
            option.option_id for option in reference.preferred_options
        }
        overlap = rejected_set & preferred_ids
        if overlap:
            issues.append(
                "已拒绝选项仍在首选: " + ", ".join(sorted(overlap))
            )
        return HumanAlignmentValidationResult(
            valid=not issues,
            issues=issues,
        )
