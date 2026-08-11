"""GoalSchedulingValidator:调度结果合法性校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.goal_scheduler.models import (
    GoalScheduleRecord,
    OptimizedGoalSchedule,
)


class GoalSchedulingValidationResult(BaseModel):
    """调度校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class GoalSchedulingValidator:
    """校验顺序 / 覆盖 / 选中 / 依赖顺序。"""

    def validate(
        self,
        *,
        schedule: OptimizedGoalSchedule,
        records: list[GoalScheduleRecord],
    ) -> GoalSchedulingValidationResult:
        issues: list[str] = []
        if not schedule.goal_order:
            issues.append("调度顺序为空")
        if len(set(schedule.goal_order)) != len(schedule.goal_order):
            issues.append("调度顺序重复")
        all_ids = {record.goal_id for record in records}
        if set(schedule.goal_order) != all_ids:
            issues.append("调度未覆盖全部目标")
        if (
            schedule.selected_goal
            and schedule.selected_goal not in schedule.goal_order
        ):
            issues.append("选中目标不在调度顺序中")
        by_id = {record.goal_id: record for record in records}
        index = {
            goal_id: position
            for position, goal_id in enumerate(schedule.goal_order)
        }
        for record in records:
            dependency = record.dependency
            if (
                dependency in by_id
                and dependency in index
                and record.goal_id in index
                and index[dependency] > index[record.goal_id]
            ):
                issues.append(
                    f"依赖顺序错误: {dependency} 应在 {record.goal_id} 前"
                )
        return GoalSchedulingValidationResult(
            valid=not issues,
            issues=issues,
        )
