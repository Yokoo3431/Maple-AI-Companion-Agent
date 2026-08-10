"""PlanningOptimizer:历史经验 -> 优化 TaskGraph(只读规划参考)。"""

from __future__ import annotations

from maple_agent.goal_memory.models import (
    GoalExperienceRecord,
    OptimizedTaskGraph,
)
from maple_agent.task_planning.models import TaskGraph


class PlanningOptimizer:
    """推荐成功路径 / 移除失败节点 / 调整顺序 / 恢复提示。"""

    def optimize(
        self,
        *,
        graph: TaskGraph,
        experience: GoalExperienceRecord | None = None,
    ) -> OptimizedTaskGraph:
        removed: list[str] = []
        hints: list[str] = []
        reordered = False
        tasks = list(graph.tasks)
        if experience is not None:
            failed = set(experience.failed_points)
            for task in list(tasks):
                if task.task_id in failed:
                    tasks.remove(task)
                    removed.append(task.task_id)
            if experience.successful_path:
                order = {
                    task_id: index
                    for index, task_id in enumerate(
                        experience.successful_path
                    )
                }
                tasks.sort(
                    key=lambda task: order.get(task.task_id, len(order))
                )
                original = [task.task_id for task in graph.tasks]
                new_order = [task.task_id for task in tasks]
                reordered = new_order != original
                hints.append(
                    "参考成功路径: "
                    + " -> ".join(experience.successful_path)
                )
            if experience.failed_points:
                hints.append(
                    "历史失败点: "
                    + ", ".join(experience.failed_points)
                    + "(已移除)"
                )
            if experience.success:
                hints.append("历史目标成功,降低失败概率")
        optimized_graph = graph.model_copy(update={"tasks": tasks})
        return OptimizedTaskGraph(
            graph=optimized_graph,
            removed_tasks=removed,
            reordered=reordered,
            recovery_hints=hints,
            summary="; ".join(hints) or "无优化",
        )
