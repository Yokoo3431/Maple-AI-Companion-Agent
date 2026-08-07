"""GoalProvider:候选获取与状态保存(暂不接数据库)。"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from maple_agent.goal.models import Goal, GoalStatus
from maple_agent.logging_setup import TraceContext

logger = logging.getLogger("maple_agent.goal")


@runtime_checkable
class GoalProvider(Protocol):
    """Goal 提供者契约。"""

    def get_candidate_goals(self, *, trace_id: str | None = None) -> list[Goal]: ...

    def get_active_goal(self, *, trace_id: str | None = None) -> Goal | None: ...

    def save_goal_status(self, goal: Goal, *, trace_id: str | None = None) -> None: ...

    def activate(self, goal: Goal, *, trace_id: str | None = None) -> None: ...


class MockGoalProvider:
    """内存实现:候选目标 + 当前激活目标。"""

    def __init__(self, goals: list[Goal] | None = None) -> None:
        self._goals: dict[str, Goal] = {
            goal.goal_id: goal for goal in (goals or [])
        }
        self._active_goal_id: str | None = None

    def get_candidate_goals(self, *, trace_id: str | None = None) -> list[Goal]:
        with TraceContext(trace_id=trace_id):
            logger.info("goal provider: candidates=%d", len(self._goals))
            return list(self._goals.values())

    def get_active_goal(self, *, trace_id: str | None = None) -> Goal | None:
        if self._active_goal_id is None:
            return None
        return self._goals.get(self._active_goal_id)

    def save_goal_status(self, goal: Goal, *, trace_id: str | None = None) -> None:
        with TraceContext(trace_id=trace_id):
            self._goals[goal.goal_id] = goal
            logger.info(
                "goal provider: saved status=%s goal=%s",
                goal.status.value,
                goal.goal_id,
            )

    def activate(self, goal: Goal, *, trace_id: str | None = None) -> None:
        with TraceContext(trace_id=trace_id):
            active = goal.model_copy(update={"status": GoalStatus.ACTIVE})
            self._goals[goal.goal_id] = active
            self._active_goal_id = goal.goal_id
            logger.info("goal provider: activated goal=%s", goal.goal_id)
