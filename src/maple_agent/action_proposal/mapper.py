"""ActionProposalMapper:BehaviorReference -> ActionProposalReference 列表(确定性)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_proposal.resolver import ActionTargetResolver
from maple_agent.behavior.models import (
    BehaviorReference,
    BehaviorStepType,
)
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.navigation.models import NavigationReference
from maple_agent.reflex.models import ReflexReference


class ActionProposalMapper:
    """把行为步骤转换为语义动作建议。"""

    _MAPPING = {
        BehaviorStepType.QUEST_ANALYSIS: ActionType.OBSERVE,
        BehaviorStepType.NAVIGATE_REFERENCE: ActionType.NAVIGATE,
        BehaviorStepType.INTERACT_REFERENCE: ActionType.INTERACT,
        BehaviorStepType.COMBAT_REFERENCE: ActionType.COMBAT,
        BehaviorStepType.COLLECT_REFERENCE: ActionType.COLLECT,
        BehaviorStepType.VERIFY_REFERENCE: ActionType.VERIFY,
        BehaviorStepType.WAIT_REFERENCE: ActionType.WAIT,
    }

    def __init__(
        self,
        target_resolver: ActionTargetResolver | None = None,
    ) -> None:
        self.target_resolver = target_resolver or ActionTargetResolver()
        self.last_actions: list[ActionProposalReference] = []

    def map(
        self,
        behavior_reference: BehaviorReference,
        *,
        game_state_reference: GameStateReference | None = None,
        navigation_reference: NavigationReference | None = None,
        reflex_reference: ReflexReference | None = None,
    ) -> list[ActionProposalReference]:
        actions: list[ActionProposalReference] = []
        for step in behavior_reference.behavior_steps:
            action_type = self._MAPPING.get(
                step.step_type,
                ActionType.OBSERVE,
            )
            target, parameters = self.target_resolver.resolve(
                step,
                navigation_reference=navigation_reference,
                reflex_reference=reflex_reference,
            )
            actions.append(
                ActionProposalReference(
                    action_id=new_id(),
                    action_type=action_type,
                    source_behavior=step.step_type.value,
                    target_reference=target,
                    parameters_reference=parameters,
                    confidence=behavior_reference.confidence,
                    validation="",
                )
            )
        self.last_actions = actions
        return actions
