"""GoalSelector:候选目标选择(Phase 2-B 规则版,不用 LLM)。"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from maple_agent.goal.models import Goal, GoalStatus
from maple_agent.logging_setup import TraceContext

if TYPE_CHECKING:
    from maple_agent.context.models import AgentContext

logger = logging.getLogger("maple_agent.goal")


class RuleBasedGoalSelector:
    """规则:priority 高 > confidence 高 > 未完成。"""

    def select(
        self,
        context: AgentContext,
        candidates: list[Goal],
        *,
        trace_id: str | None = None,
    ) -> Goal | None:
        with TraceContext(trace_id=trace_id):
            eligible = [
                goal
                for goal in candidates
                if goal.status in (GoalStatus.CREATED, GoalStatus.ACTIVE)
            ]
            if not eligible:
                logger.info("goal selector: no eligible candidate")
                return None
            selected = sorted(
                eligible,
                key=lambda goal: (-goal.priority, -goal.confidence, goal.created_at),
            )[0]
            logger.info(
                "goal selector: selected=%s priority=%s confidence=%s",
                selected.title,
                selected.priority,
                selected.confidence,
            )
            return selected
