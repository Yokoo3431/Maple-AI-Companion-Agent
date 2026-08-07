"""Goal 状态机(严格迁移)。"""

from __future__ import annotations

from maple_agent.goal.models import Goal, GoalStatus


class GoalTransitionError(RuntimeError):
    """非法目标状态跳转。"""


_TRANSITIONS: dict[GoalStatus, frozenset[GoalStatus]] = {
    GoalStatus.CREATED: frozenset(),
    GoalStatus.ACTIVE: frozenset({GoalStatus.CREATED, GoalStatus.PAUSED}),
    GoalStatus.PAUSED: frozenset({GoalStatus.ACTIVE}),
    GoalStatus.COMPLETED: frozenset({GoalStatus.ACTIVE}),
    GoalStatus.FAILED: frozenset({GoalStatus.ACTIVE}),
    GoalStatus.CANCELLED: frozenset({GoalStatus.ACTIVE}),
}


class GoalStateMachine:
    """对 Goal 做严格状态迁移,返回新副本。"""

    def transition(self, goal: Goal, target: GoalStatus) -> Goal:
        allowed = _TRANSITIONS.get(target, frozenset())
        if goal.status not in allowed:
            raise GoalTransitionError(
                f"非法状态跳转: {goal.status.value} -> {target.value}"
            )
        return goal.model_copy(update={"status": target})
