"""TaskDecomposer:LongHorizonGoal -> TaskGraph(只读拆解)。"""

from __future__ import annotations

from maple_agent.task_planning.models import (
    LongHorizonGoal,
    Milestone,
    TaskGraph,
    TaskNode,
)


class TaskDecomposer:
    """把长程目标按里程碑拆解为任务图。"""

    def decompose(self, goal: LongHorizonGoal) -> TaskGraph:
        milestones: list[Milestone] = []
        tasks: list[TaskNode] = []
        for milestone_index, milestone in enumerate(goal.milestones):
            task_ids = list(milestone.task_ids)
            milestones.append(
                Milestone(
                    milestone_id=milestone.milestone_id,
                    title=milestone.title,
                    order=milestone.order,
                    task_ids=task_ids,
                )
            )
            for task_index, task_id in enumerate(task_ids):
                prerequisite = ""
                if task_index > 0:
                    prerequisite = task_ids[task_index - 1]
                elif milestone_index > 0:
                    previous_tasks = goal.milestones[
                        milestone_index - 1
                    ].task_ids
                    prerequisite = (
                        previous_tasks[-1]
                        if previous_tasks
                        else (
                            "milestone:"
                            f"{goal.milestones[milestone_index - 1].milestone_id}"
                        )
                    )
                tasks.append(
                    TaskNode(
                        task_id=task_id,
                        milestone_index=milestone_index,
                        objective=f"{milestone.title}: {task_id}",
                        prerequisite=prerequisite,
                        expected_result=f"完成 {task_id}",
                        failure_condition=f"{task_id} 执行失败",
                    )
                )
        return TaskGraph(
            goal_id=goal.goal_id,
            milestones=milestones,
            tasks=tasks,
        )
