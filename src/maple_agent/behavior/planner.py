"""BehaviorPlanner:目标/导航/状态/反射 -> BehaviorReference(只读)。"""

from __future__ import annotations

from maple_agent.behavior.goal import GoalMapper
from maple_agent.behavior.models import (
    BehaviorReference,
    BehaviorStep,
    BehaviorStepType,
)
from maple_agent.behavior.sequence import BehaviorSequenceBuilder
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.navigation.models import NavigationReference
from maple_agent.quest_reasoning.models import QuestGoalReference
from maple_agent.reflex.models import ReflexReference


class BehaviorPlanner:
    """把任务目标与上下文组合为高层行为参考。"""

    def __init__(
        self,
        *,
        goal_mapper: GoalMapper | None = None,
        sequence_builder: BehaviorSequenceBuilder | None = None,
    ) -> None:
        self.goal_mapper = goal_mapper or GoalMapper()
        self.sequence_builder = (
            sequence_builder or BehaviorSequenceBuilder()
        )
        self.last_reference: BehaviorReference | None = None

    def plan(
        self,
        *,
        quest_goal_reference: QuestGoalReference | None = None,
        navigation_reference: NavigationReference | None = None,
        game_state_reference: GameStateReference | None = None,
        reflex_reference: ReflexReference | None = None,
        target_hint: str = "",
    ) -> BehaviorReference:
        goal = (
            quest_goal_reference.recommended_goals[0]
            if (
                quest_goal_reference is not None
                and quest_goal_reference.recommended_goals
            )
            else None
        )
        goal_reference = (
            f"{goal.goal_type.value}: {goal.description}"
            if goal is not None
            else ""
        )
        types = self.goal_mapper.map(
            quest_goal_reference,
            target_hint=target_hint,
        )
        steps: list[BehaviorStep] = []
        for step_type in types:
            metadata: dict = {}
            if step_type is BehaviorStepType.NAVIGATE_REFERENCE:
                metadata = {
                    "route_available": bool(
                        navigation_reference is not None
                        and navigation_reference.route_steps
                    ),
                    "target": (
                        navigation_reference.target_location
                        if navigation_reference is not None
                        else ""
                    ),
                    "cost": (
                        navigation_reference.estimated_cost
                        if navigation_reference is not None
                        else 0.0
                    ),
                }
            steps.append(
                BehaviorStep(
                    step_type=step_type,
                    description=BehaviorPlanner._describe(
                        step_type,
                        goal.related_quest if goal is not None else "",
                    ),
                    metadata=metadata,
                )
            )
        if (
            reflex_reference is not None
            and reflex_reference.danger_events
        ):
            steps.append(
                BehaviorStep(
                    step_type=BehaviorStepType.WAIT_REFERENCE,
                    description="等待/恢复状态后再继续",
                    metadata={
                        "danger_events": [
                            event.event_type.value
                            for event in reflex_reference.danger_events
                        ]
                    },
                )
            )
        ordered = self.sequence_builder.order(steps)
        route_unavailable = (
            navigation_reference is None
            or not navigation_reference.route_steps
        )
        confidence = 0.9
        reasoning: list[str] = [
            f"目标: {goal_reference or '无'}",
            f"行为步骤: {len(ordered)}",
        ]
        if route_unavailable:
            confidence -= 0.1
            reasoning.append("导航路线不可用,置信度降低")
        if reflex_reference is not None and reflex_reference.danger_events:
            confidence -= 0.1
            reasoning.append("检测到危险事件,插入等待步骤")
        reference = BehaviorReference(
            behavior_id=new_id(),
            goal_reference=goal_reference,
            behavior_steps=ordered,
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            reasoning=reasoning,
            validation="",
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _describe(
        step_type: BehaviorStepType,
        quest_name: str,
    ) -> str:
        descriptions = {
            BehaviorStepType.QUEST_ANALYSIS: "分析任务状态",
            BehaviorStepType.NAVIGATE_REFERENCE: "前往目标位置",
            BehaviorStepType.INTERACT_REFERENCE: "与目标交互",
            BehaviorStepType.COMBAT_REFERENCE: "执行战斗行为",
            BehaviorStepType.COLLECT_REFERENCE: "收集目标道具",
            BehaviorStepType.VERIFY_REFERENCE: "验证任务进度",
            BehaviorStepType.WAIT_REFERENCE: "等待/恢复状态",
        }
        base = descriptions.get(step_type, step_type.value)
        return f"{base}: {quest_name}" if quest_name else base
