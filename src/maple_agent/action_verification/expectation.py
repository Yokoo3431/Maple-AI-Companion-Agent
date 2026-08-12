"""ActionExpectationBuilder:ActionProposal -> ExpectedOutcomeReference(确定性)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_verification.models import ExpectedOutcomeReference
from maple_agent.action_verification.timeout import OutcomeTimeoutPolicy
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.navigation.models import NavigationReference
from maple_agent.quest_reasoning.models import QuestGoalReference


class ActionExpectationBuilder:
    """按动作语义构建预期状态变化。"""

    def __init__(
        self,
        timeout_policy: OutcomeTimeoutPolicy | None = None,
    ) -> None:
        self.timeout_policy = timeout_policy or OutcomeTimeoutPolicy()
        self.last_expectation: ExpectedOutcomeReference | None = None

    def build(
        self,
        action: ActionProposalReference,
        *,
        game_state: GameStateReference | None = None,
        navigation: NavigationReference | None = None,
        quest_goal: QuestGoalReference | None = None,
    ) -> ExpectedOutcomeReference:
        action_type = action.action_type
        expected_map = ""
        expected_visible = False
        expected_absent = False
        expected_quests: list[str] = []
        expected_changes: list[str] = []
        expected_ui: list[str] = []
        cross_map = False
        reasoning: list[str] = []
        if action_type is ActionType.NAVIGATE:
            target = (
                navigation.target_location
                if navigation is not None
                else action.target_reference
            )
            cross_map = bool(
                navigation is not None
                and len(navigation.route_steps) >= 1
                and navigation.route_steps[0].step_type.value
                == "PORTAL_REFERENCE"
            )
            if cross_map and target:
                expected_map = target
                expected_changes = ["MAP_CHANGED"]
                reasoning.append(
                    f"跨地图导航,预期地图变化至 {target}"
                )
            else:
                expected_visible = True
                expected_changes = ["TARGET_VISIBLE"]
                reasoning.append("同地图导航,预期目标保持可解析")
        elif action_type is ActionType.INTERACT:
            expected_visible = True
            quest_name = ""
            if quest_goal is not None and quest_goal.recommended_goals:
                quest_name = quest_goal.recommended_goals[0].related_quest
            if quest_name:
                expected_quests = [quest_name]
            expected_changes = ["QUEST_PROGRESS_CHANGED"]
            expected_ui = ["dialog", "quest_ui"]
            reasoning.append("交互动作,预期任务状态或 UI 变化")
        elif action_type is ActionType.COMBAT:
            expected_absent = True
            expected_changes = ["MONSTER_COUNT_CHANGED"]
            reasoning.append(
                "战斗动作,预期目标消失/减少;HP 变化仅作为证据"
            )
        elif action_type is ActionType.COLLECT:
            expected_changes = ["ITEM_CHANGED"]
            reasoning.append(
                "收集动作,预期道具/库存或任务进度变化"
            )
        elif action_type is ActionType.VERIFY:
            expected_changes = ["OBSERVATION_VALID"]
            reasoning.append("验证动作,预期观察有效且状态可解析")
        elif action_type is ActionType.WAIT:
            expected_changes = ["OBSERVATION_CONTINUES"]
            reasoning.append("等待动作,预期观察正常继续")
        elif action_type is ActionType.OBSERVE:
            expected_changes = ["OBSERVATION_OBTAINED"]
            reasoning.append("观察动作,预期取得合法观察")
        timeout = self.timeout_policy.timeout_for(
            action_type.value,
            cross_map=cross_map,
        )
        expectation = ExpectedOutcomeReference(
            expectation_id=new_id(),
            action_id=action.action_id,
            action_reference=(
                f"{action_type.value}: {action.target_reference}"
            ),
            action_type=action_type.value,
            target_reference=action.target_reference,
            expected_map=expected_map,
            expected_target_visible=expected_visible,
            expected_target_absent=expected_absent,
            expected_quest_progress=expected_quests,
            expected_state_changes=expected_changes,
            expected_ui_signals=expected_ui,
            timeout_reference_seconds=timeout,
            confidence=0.8,
            reasoning=reasoning,
        )
        self.last_expectation = expectation
        return expectation
