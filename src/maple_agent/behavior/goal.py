"""GoalMapper:QuestGoalReference -> 行为步骤模板(确定性规则,无 LLM)。"""

from __future__ import annotations

from maple_agent.behavior.models import BehaviorStepType
from maple_agent.quest_reasoning.models import GoalType, QuestGoalReference


class GoalMapper:
    """把任务目标映射为语义行为序列。"""

    @staticmethod
    def map(
        quest_goal_reference: QuestGoalReference | None,
        *,
        target_hint: str = "",
    ) -> list[BehaviorStepType]:
        if (
            quest_goal_reference is None
            or not quest_goal_reference.recommended_goals
        ):
            return [BehaviorStepType.QUEST_ANALYSIS]
        goal = quest_goal_reference.recommended_goals[0]
        text = (
            f"{goal.description} {goal.related_quest} {target_hint}"
        )
        if goal.goal_type is GoalType.NPC_INTERACTION_REFERENCE:
            return [
                BehaviorStepType.NAVIGATE_REFERENCE,
                BehaviorStepType.INTERACT_REFERENCE,
                BehaviorStepType.VERIFY_REFERENCE,
            ]
        if goal.goal_type is GoalType.QUEST_PROGRESS:
            if any(
                keyword in text
                for keyword in ("击杀", "击败", "猎杀", "战斗")
            ):
                return [
                    BehaviorStepType.NAVIGATE_REFERENCE,
                    BehaviorStepType.COMBAT_REFERENCE,
                    BehaviorStepType.VERIFY_REFERENCE,
                ]
            if any(
                keyword in text for keyword in ("收集", "采集", "获取")
            ):
                return [
                    BehaviorStepType.NAVIGATE_REFERENCE,
                    BehaviorStepType.COLLECT_REFERENCE,
                    BehaviorStepType.VERIFY_REFERENCE,
                ]
            return [
                BehaviorStepType.QUEST_ANALYSIS,
                BehaviorStepType.VERIFY_REFERENCE,
            ]
        if goal.goal_type is GoalType.EXPLORATION_REFERENCE:
            return [
                BehaviorStepType.NAVIGATE_REFERENCE,
                BehaviorStepType.QUEST_ANALYSIS,
                BehaviorStepType.VERIFY_REFERENCE,
            ]
        if goal.goal_type is GoalType.KNOWLEDGE_QUERY:
            return [
                BehaviorStepType.QUEST_ANALYSIS,
                BehaviorStepType.WAIT_REFERENCE,
            ]
        return [BehaviorStepType.QUEST_ANALYSIS]
