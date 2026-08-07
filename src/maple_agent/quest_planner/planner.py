"""QuestPlanner:Quest → QuestPlan(只生成文本计划)。"""

from __future__ import annotations

import logging

from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal
from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.quest.graph import QuestGraph
from maple_agent.quest.models import Quest
from maple_agent.quest_planner.models import (
    QuestPlan,
    QuestPlanAction,
    QuestPlanStep,
)

logger = logging.getLogger("maple_agent.quest_planner")

_ACTION_BY_OBJECTIVE = {
    "kill": QuestPlanAction.DEFEAT,
    "collect": QuestPlanAction.COLLECT,
    "talk": QuestPlanAction.TALK,
    "deliver": QuestPlanAction.DELIVER,
}


class QuestPlanner:
    """根据 Quest + QuestGraph + WorldState 生成结构化 QuestPlan。"""

    def __init__(self, knowledge: KnowledgeProvider) -> None:
        self.knowledge = knowledge
        self._graph = QuestGraph(knowledge.data.quests_domain)

    def plan(
        self,
        quest: Quest,
        *,
        world_state: WorldState | None = None,
        goal: Goal | None = None,
        goal_id: str = "",
        trace_id: str | None = None,
    ) -> QuestPlan:
        with TraceContext(trace_id=trace_id) as trace:
            steps = self._build_steps(quest)
            plan = QuestPlan(
                plan_id=new_id(),
                goal_id=goal_id or (goal.goal_id if goal else ""),
                quest_id=quest.quest_id,
                title=quest.name,
                steps=steps,
                confidence=goal.confidence if goal else 0.8,
                trace_id=trace.trace_id,
            )
            logger.info(
                "quest planner: quest=%s steps=%d",
                quest.name,
                len(steps),
            )
            return plan

    def _build_steps(self, quest: Quest) -> list[QuestPlanStep]:
        steps: list[QuestPlanStep] = []
        index = 0

        def add_step(
            action: QuestPlanAction,
            description: str,
            *,
            target: str = "",
            related_map=None,
            related_npc=None,
            related_monster=None,
            prerequisite=None,
            expected_result: str = "",
        ) -> None:
            nonlocal index
            index += 1
            steps.append(
                QuestPlanStep(
                    step_id=f"s{index}",
                    action=action,
                    description=description,
                    target=target,
                    related_map=related_map,
                    related_npc=related_npc,
                    related_monster=related_monster,
                    prerequisite=prerequisite,
                    expected_result=expected_result,
                )
            )

        prereqs = self._graph.prerequisites_of(quest.quest_id)
        if prereqs:
            add_step(
                QuestPlanAction.ANALYZE,
                "检查前置任务",
                target=",".join(str(item.quest_id) for item in prereqs),
                prerequisite=prereqs[0].quest_id,
                expected_result="前置任务满足",
            )
        if quest.map_id is not None:
            add_step(
                QuestPlanAction.MOVE_HINT,
                "前往相关地图",
                target=str(quest.map_id),
                related_map=quest.map_id,
                expected_result="到达目标地图",
            )
        if quest.npc_id is not None:
            add_step(
                QuestPlanAction.TALK,
                "找到 NPC 接受任务",
                target=str(quest.npc_id),
                related_npc=quest.npc_id,
                expected_result="任务已接受(语义)",
            )
        monster_ids = {str(item) for item in quest.monster_ids}
        for objective in quest.objectives:
            action = _ACTION_BY_OBJECTIVE.get(objective.kind, QuestPlanAction.ANALYZE)
            related_monster = (
                objective.target if str(objective.target) in monster_ids else None
            )
            add_step(
                action,
                objective.description,
                target=str(objective.target),
                related_map=quest.map_id,
                related_monster=related_monster,
                expected_result=f"完成 {objective.quantity} 次",
            )
        if quest.npc_id is not None:
            add_step(
                QuestPlanAction.DELIVER,
                "返回 NPC 提交",
                target=str(quest.npc_id),
                related_npc=quest.npc_id,
                expected_result="交付完成",
            )
        add_step(
            QuestPlanAction.COMPLETE,
            "完成任务",
            target=str(quest.quest_id),
            expected_result="任务完成",
        )
        return steps
