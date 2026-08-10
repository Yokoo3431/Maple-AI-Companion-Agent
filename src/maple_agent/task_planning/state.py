"""TaskExecutionStateManager:长程执行状态与中断恢复(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.task_planning.models import (
    LongHorizonGoal,
    TaskExecutionState,
    TaskGraph,
    TaskNode,
)
from maple_agent.task_planning.recovery import RecoveryPlan


class TaskExecutionStateManager:
    """维护任务进度,支持标记完成/失败与恢复。"""

    def __init__(self, graph: TaskGraph) -> None:
        self.graph = graph
        self.state = TaskExecutionState(
            goal_id=graph.goal_id,
            current_goal=graph.goal_id,
            pending_tasks=[task.task_id for task in graph.tasks],
            next_action=graph.tasks[0].task_id if graph.tasks else "",
        )

    def mark_completed(self, task_id: str) -> None:
        if task_id in self.state.pending_tasks:
            self.state.pending_tasks.remove(task_id)
        if task_id in self.state.failed_tasks:
            self.state.failed_tasks.remove(task_id)
        if task_id not in self.state.completed_tasks:
            self.state.completed_tasks.append(task_id)
        self.state.next_action = self._next_pending_id()

    def mark_failed(self, task_id: str) -> None:
        if task_id in self.state.pending_tasks:
            self.state.pending_tasks.remove(task_id)
        if task_id not in self.state.failed_tasks:
            self.state.failed_tasks.append(task_id)
        self.state.retry_count += 1
        self.state.next_action = self._next_pending_id()

    def current_task(self) -> TaskNode | None:
        """第一个满足前置条件且未完成的任务。"""
        for task in self.graph.tasks:
            if task.task_id in self.state.completed_tasks:
                continue
            if task.task_id in self.state.failed_tasks:
                continue
            prerequisite_ok = self._prerequisite_ok(task)
            if prerequisite_ok:
                return task
        return None

    def progress(self) -> float:
        total = len(self.graph.tasks)
        if total == 0:
            return 0.0
        return round(len(self.state.completed_tasks) / total, 4)

    def snapshot(self) -> TaskExecutionState:
        return self.state.model_copy(deep=True)

    def _prerequisite_ok(self, task: TaskNode) -> bool:
        if not task.prerequisite:
            return True
        if task.prerequisite.startswith("milestone:"):
            return True
        return task.prerequisite in self.state.completed_tasks

    def _next_pending_id(self) -> str:
        current = self.current_task()
        return current.task_id if current is not None else ""


def save_task_planning_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    goal: LongHorizonGoal,
    graph: TaskGraph,
    state: TaskExecutionState,
    recovery: RecoveryPlan | None = None,
) -> None:
    """写入 task_planning_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "goal_id": goal.goal_id,
        "milestones": [
            {
                "milestone_id": milestone.milestone_id,
                "title": milestone.title,
                "order": milestone.order,
                "tasks": milestone.task_ids,
            }
            for milestone in graph.milestones
        ],
        "current_task": state.next_action,
        "progress": round(
            len(state.completed_tasks) / len(graph.tasks), 4
        )
        if graph.tasks
        else 0.0,
        "recovery": (
            [recovery.model_dump(mode="json")] if recovery is not None else []
        ),
        "task_graph": graph.model_dump(mode="json"),
        "state": state.model_dump(mode="json"),
    }
    (directory / "task_planning_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
