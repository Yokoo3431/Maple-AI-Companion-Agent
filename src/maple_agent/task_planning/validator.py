"""LongHorizonValidator:里程碑顺序 / 前置 / 循环依赖 / 完整性 / recovery。"""

from __future__ import annotations

from collections import defaultdict

from pydantic import BaseModel, Field

from maple_agent.task_planning.models import TaskExecutionState, TaskGraph
from maple_agent.task_planning.recovery import RecoveryAction, RecoveryPlan


class LongHorizonValidationResult(BaseModel):
    """长程规划校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class LongHorizonValidator:
    """校验任务图与执行状态(只读)。"""

    def validate(
        self,
        graph: TaskGraph,
        *,
        state: TaskExecutionState | None = None,
        recovery: RecoveryPlan | None = None,
    ) -> LongHorizonValidationResult:
        issues: list[str] = []
        orders = [milestone.order for milestone in graph.milestones]
        if orders != sorted(orders):
            issues.append("milestone 顺序非法")
        if not graph.tasks:
            issues.append("任务图为空")
        if self._has_cycle(graph):
            issues.append("存在循环依赖")
        if state is not None:
            self._validate_state(graph, state, issues)
        if recovery is not None and recovery.action not in set(RecoveryAction):
            issues.append("recovery 动作非法")
        return LongHorizonValidationResult(
            valid=not issues,
            issues=issues,
        )

    def _validate_state(
        self,
        graph: TaskGraph,
        state: TaskExecutionState,
        issues: list[str],
    ) -> None:
        for task_id in state.pending_tasks:
            task = next(
                (task for task in graph.tasks if task.task_id == task_id),
                None,
            )
            if task is None:
                continue
            if (
                task.prerequisite
                and not task.prerequisite.startswith("milestone:")
                and task.prerequisite in state.pending_tasks
            ):
                issues.append(
                    f"前置任务未完成: {task.prerequisite} -> {task_id}"
                )
        known = (
            set(state.completed_tasks)
            | set(state.pending_tasks)
            | set(state.failed_tasks)
        )
        all_ids = {task.task_id for task in graph.tasks}
        if known != all_ids:
            issues.append("任务状态不完整")

    @staticmethod
    def _has_cycle(graph: TaskGraph) -> bool:
        task_ids = {task.task_id for task in graph.tasks}
        adjacency: dict[str, list[str]] = defaultdict(list)
        for task in graph.tasks:
            if (
                task.prerequisite
                and not task.prerequisite.startswith("milestone:")
                and task.prerequisite in task_ids
            ):
                adjacency[task.prerequisite].append(task.task_id)
        white: set[str] = set(task_ids)
        gray: set[str] = set()
        black: set[str] = set()

        def dfs(node: str) -> bool:
            if node in gray:
                return True
            if node in black:
                return False
            white.discard(node)
            gray.add(node)
            for neighbor in adjacency.get(node, []):
                if dfs(neighbor):
                    return True
            gray.discard(node)
            black.add(node)
            return False

        return any(dfs(node) for node in list(task_ids))
