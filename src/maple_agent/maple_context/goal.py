"""MapleGoalContextBuilder:目标上下文聚合(只读)。"""

from __future__ import annotations

from maple_agent.decision_reference.models import DecisionReference
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.goal_scheduler.models import OptimizedGoalSchedule
from maple_agent.maple_context.models import MapleGoalContext
from maple_agent.task_planning.models import LongHorizonGoal


class MapleGoalContextBuilder:
    """聚合目标 / 调度 / 规划参考 / 决策参考。"""

    def build(
        self,
        *,
        active_goal: LongHorizonGoal | None = None,
        goal_schedule: OptimizedGoalSchedule | None = None,
        planning_reference: EnvironmentPlanningReference | None = None,
        decision_reference: DecisionReference | None = None,
    ) -> MapleGoalContext:
        related_tasks = (
            [
                task_id
                for milestone in active_goal.milestones
                for task_id in milestone.task_ids
            ]
            if active_goal is not None
            else []
        )
        planning_text = (
            ", ".join(
                adjustment.opportunity_type
                for adjustment in planning_reference.priority_adjustments
            )
            if planning_reference is not None
            else ""
        )
        decision_text = (
            ", ".join(
                option.option_id
                for option in decision_reference.recommended_options
            )
            if decision_reference is not None
            else ""
        )
        confidence = self._confidence(
            active_goal,
            goal_schedule,
            decision_reference,
        )
        return MapleGoalContext(
            active_goal=(
                active_goal.description if active_goal is not None else ""
            ),
            goal_type="LONG_HORIZON",
            priority=active_goal.priority if active_goal is not None else 0,
            related_tasks=related_tasks,
            planning_reference=planning_text,
            decision_reference=decision_text,
            confidence=confidence,
        )

    @staticmethod
    def _confidence(
        active_goal: LongHorizonGoal | None,
        goal_schedule: OptimizedGoalSchedule | None,
        decision_reference: DecisionReference | None,
    ) -> float:
        values: list[float] = []
        if active_goal is not None:
            values.append(0.8)
        if goal_schedule is not None and goal_schedule.selected_goal:
            values.append(0.8)
        if decision_reference is not None:
            values.append(decision_reference.confidence)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
