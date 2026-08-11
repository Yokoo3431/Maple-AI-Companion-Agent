"""GoalPriorityCalculator:目标优先级评分(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.goal_scheduler.models import (
    GoalPriorityResult,
    GoalScheduleRecord,
)


class GoalPriorityCalculator:
    """PriorityScore = 0.35*Importance + 0.25*Urgency + 0.2*Success + 0.2*Efficiency。"""

    def calculate(
        self,
        record: GoalScheduleRecord,
    ) -> GoalPriorityResult:
        importance_score = record.importance
        urgency_score = self._urgency(record)
        success_probability = record.confidence
        resource_efficiency = round(1.0 - record.resource_cost, 4)
        score = round(
            0.35 * importance_score
            + 0.25 * urgency_score
            + 0.2 * success_probability
            + 0.2 * resource_efficiency,
            4,
        )
        reasoning = [
            f"importance={importance_score:.2f}",
            f"urgency={urgency_score:.2f}",
            f"success={success_probability:.2f}",
            f"efficiency={resource_efficiency:.2f}",
        ]
        return GoalPriorityResult(
            goal_id=record.goal_id,
            score=score,
            components={
                "importance": importance_score,
                "urgency": urgency_score,
                "success_probability": success_probability,
                "resource_efficiency": resource_efficiency,
            },
            reasoning=reasoning,
        )

    @staticmethod
    def _urgency(record: GoalScheduleRecord) -> float:
        if record.deadline is None:
            return record.urgency
        remaining = (
            record.deadline - datetime.now(UTC)
        ).total_seconds()
        if remaining <= 0:
            return 1.0
        deadline_urgency = round(
            max(0.0, min(1.0, 1.0 - remaining / 86400)),
            4,
        )
        return round(max(record.urgency, deadline_urgency), 4)
