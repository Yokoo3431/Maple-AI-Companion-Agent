"""PlanningOptimizationValidator:优化结果合法性校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.planning_optimizer.models import OptimizedPlanningReference
from maple_agent.task_planning.models import TaskGraph


class PlanningOptimizationValidationResult(BaseModel):
    """规划优化校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class PlanningOptimizationValidator:
    """校验优化顺序/移除/完整性。"""

    def validate(
        self,
        *,
        reference: OptimizedPlanningReference,
        graph: TaskGraph,
    ) -> PlanningOptimizationValidationResult:
        issues: list[str] = []
        if not reference.optimized_order:
            issues.append("优化顺序为空")
        if len(set(reference.optimized_order)) != len(
            reference.optimized_order
        ):
            issues.append("优化顺序重复")
        removed_set = set(reference.removed_tasks)
        overlap = removed_set & set(reference.optimized_order)
        if overlap:
            issues.append(
                "已移除任务仍出现在优化顺序: " + ", ".join(sorted(overlap))
            )
        expected = {task.task_id for task in graph.tasks} - removed_set
        if set(reference.optimized_order) != expected:
            issues.append("优化顺序与任务集不完整")
        return PlanningOptimizationValidationResult(
            valid=not issues,
            issues=issues,
        )
