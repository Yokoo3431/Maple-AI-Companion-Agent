"""FeedbackProcessor:HumanFeedback -> PreferenceUpdateReference(只读)。"""

from __future__ import annotations

from maple_agent.human_alignment.models import (
    FeedbackAction,
    HumanFeedback,
    PreferenceUpdateReference,
)
from maple_agent.human_alignment.preference import PreferenceMemory


class FeedbackProcessor:
    """把用户反馈写入偏好记忆并返回更新参考。"""

    def __init__(
        self,
        memory: PreferenceMemory | None = None,
    ) -> None:
        self.memory = memory or PreferenceMemory()

    def process(
        self,
        *,
        feedback: HumanFeedback,
    ) -> PreferenceUpdateReference:
        self.memory.record(
            option_id=feedback.option_id,
            action=feedback.action.value,
            reason=feedback.comment,
            trace_id=feedback.trace_id,
        )
        updates: list[str] = []
        if feedback.action is FeedbackAction.ACCEPT:
            updates.append(f"接受选项 {feedback.option_id}")
        elif feedback.action is FeedbackAction.REJECT:
            updates.append(f"拒绝选项 {feedback.option_id}")
        elif feedback.action is FeedbackAction.CORRECT:
            updates.append(
                f"手动纠正选项 {feedback.option_id}: {feedback.comment}"
            )
        return PreferenceUpdateReference(
            feedback_id=feedback.feedback_id,
            updates=updates,
            applied=True,
        )
