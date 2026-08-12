"""QuestReasoningValidator:任务智能参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.quest_reasoning.models import (
    QuestGoalReference,
    QuestStateType,
)


class QuestReasoningVerdict(StrEnum):
    """任务推理校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class QuestReasoningValidationResult(BaseModel):
    """任务推理校验结果。"""

    verdict: QuestReasoningVerdict
    issues: list[str] = Field(default_factory=list)


class QuestReasoningValidator:
    """检查任务存在 / 目标有效 / 依赖可达 / 状态合法。"""

    def validate(
        self,
        reference: QuestGoalReference,
    ) -> QuestReasoningValidationResult:
        if not (0 <= reference.confidence <= 1):
            return QuestReasoningValidationResult(
                verdict=QuestReasoningVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        for dependency in reference.dependencies:
            if (
                not dependency.goal_id
                or not dependency.depends_on
                or not dependency.dependency_type
            ):
                return QuestReasoningValidationResult(
                    verdict=QuestReasoningVerdict.BLOCKED,
                    issues=["impossible dependency"],
                )
        issues: list[str] = []
        for progress in reference.quest_progress:
            if progress.state is QuestStateType.UNKNOWN:
                issues.append(
                    f"quest state unknown: {progress.quest_name}"
                )
        if not reference.active_quests:
            issues.append("no active quests")
        for quest in reference.active_quests:
            if not quest.requirements:
                issues.append(
                    f"incomplete requirements: {quest.quest_name}"
                )
        if not reference.recommended_goals and not reference.blocked_goals:
            issues.append("no goal reference")
        verdict = (
            QuestReasoningVerdict.VALID
            if not issues
            else QuestReasoningVerdict.WARNING
        )
        return QuestReasoningValidationResult(
            verdict=verdict,
            issues=issues,
        )
