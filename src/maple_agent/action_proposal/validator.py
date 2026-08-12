"""ActionProposalValidator:动作建议校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)


class ActionProposalVerdict(StrEnum):
    """动作建议校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class ActionProposalValidationResult(BaseModel):
    """动作建议校验结果。"""

    verdict: ActionProposalVerdict
    issues: list[str] = Field(default_factory=list)


class ActionProposalValidator:
    """检查动作对象 / 类型 / 目标 / 置信度。"""

    def validate(
        self,
        reference: ActionProposalReference,
    ) -> ActionProposalValidationResult:
        if not reference.action_id:
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.BLOCKED,
                issues=["missing action id"],
            )
        if not (0 <= reference.confidence <= 1):
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if reference.action_type not in set(ActionType):
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.BLOCKED,
                issues=["invalid action type"],
            )
        issues: list[str] = []
        if not reference.target_reference:
            issues.append("missing target reference")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            ActionProposalVerdict.VALID
            if not issues
            else ActionProposalVerdict.WARNING
        )
        return ActionProposalValidationResult(
            verdict=verdict,
            issues=issues,
        )

    def validate_many(
        self,
        actions: list[ActionProposalReference],
    ) -> ActionProposalValidationResult:
        if not actions:
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.WARNING,
                issues=["empty actions"],
            )
        verdicts = [self.validate(action) for action in actions]
        if any(
            result.verdict is ActionProposalVerdict.BLOCKED
            for result in verdicts
        ):
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.BLOCKED,
                issues=[
                    issue
                    for result in verdicts
                    for issue in result.issues
                ],
            )
        if any(
            result.verdict is ActionProposalVerdict.WARNING
            for result in verdicts
        ):
            return ActionProposalValidationResult(
                verdict=ActionProposalVerdict.WARNING,
                issues=[
                    issue
                    for result in verdicts
                    for issue in result.issues
                ],
            )
        return ActionProposalValidationResult(
            verdict=ActionProposalVerdict.VALID,
            issues=[],
        )
