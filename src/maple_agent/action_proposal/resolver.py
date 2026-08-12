"""ActionTargetResolver:行为步骤 -> 动作目标参考(确定性)。"""

from __future__ import annotations

from maple_agent.behavior.models import BehaviorStep, BehaviorStepType
from maple_agent.navigation.models import NavigationReference
from maple_agent.reflex.models import ReflexReference


class ActionTargetResolver:
    """把行为步骤解析为动作目标与参数参考。"""

    def resolve(
        self,
        step: BehaviorStep,
        *,
        navigation_reference: NavigationReference | None = None,
        reflex_reference: ReflexReference | None = None,
    ) -> tuple[str, dict]:
        step_type = step.step_type
        if step_type is BehaviorStepType.NAVIGATE_REFERENCE:
            target = (
                navigation_reference.target_location
                if navigation_reference is not None
                and navigation_reference.target_location
                else step.target
            )
            parameters = {
                "route_reference": (
                    [
                        {
                            "type": route.step_type.value,
                            "source": route.source,
                            "target": route.target,
                        }
                        for route in navigation_reference.route_steps
                    ]
                    if navigation_reference is not None
                    else []
                ),
                "cost": (
                    navigation_reference.estimated_cost
                    if navigation_reference is not None
                    else 0.0
                ),
            }
            return target, parameters
        if step_type is BehaviorStepType.INTERACT_REFERENCE:
            return step.target, {"npc_reference": step.target}
        if step_type is BehaviorStepType.COMBAT_REFERENCE:
            return step.target, {
                "monster_reference": step.target,
                "note": "not attack command",
            }
        if step_type is BehaviorStepType.COLLECT_REFERENCE:
            return step.target, {"item_reference": step.target}
        if step_type is BehaviorStepType.QUEST_ANALYSIS:
            return (
                step.target or "quest_state",
                {"observe_target": "quest"},
            )
        if step_type is BehaviorStepType.VERIFY_REFERENCE:
            return (
                step.target or "quest_progress",
                {"verify_target": step.target},
            )
        if step_type is BehaviorStepType.WAIT_REFERENCE:
            danger = (
                [
                    event.event_type.value
                    for event in reflex_reference.danger_events
                ]
                if reflex_reference is not None
                else []
            )
            return "recovery", {"reason": danger}
        return step.target, {}
