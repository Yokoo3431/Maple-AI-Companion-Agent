"""QuestResolver:Goal → Quest(安全降级)。"""

from __future__ import annotations

import logging

from maple_agent.goal.models import Goal, GoalType
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.quest.models import Quest

logger = logging.getLogger("maple_agent.quest_planner")


class QuestResolver:
    """根据 Goal 解析对应 Quest;未找到时安全降级返回 None。"""

    def __init__(self, knowledge: KnowledgeProvider) -> None:
        self.knowledge = knowledge

    def resolve(
        self,
        goal: Goal | None,
        *,
        trace_id: str | None = None,
    ) -> Quest | None:
        with TraceContext(trace_id=trace_id):
            if goal is None or goal.goal_type is not GoalType.QUEST:
                logger.info("quest resolver: goal 非 QUEST,跳过")
                return None
            quest = self._from_source(goal) or self._by_title(goal)
            if quest is None:
                logger.info("quest resolver: 未找到任务,安全降级 goal=%s", goal.title)
            else:
                logger.info("quest resolver: goal=%s -> quest=%s", goal.title, quest.name)
            return quest

    def _from_source(self, goal: Goal) -> Quest | None:
        if not goal.source.startswith("quest:"):
            return None
        return self.knowledge.get_quest(goal.source.split(":", 1)[1])

    def _by_title(self, goal: Goal) -> Quest | None:
        return self.knowledge.get_quest(goal.title)
