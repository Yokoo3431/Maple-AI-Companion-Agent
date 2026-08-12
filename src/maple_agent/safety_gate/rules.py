"""SafetyRules:确定性安全规则(无 LLM)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.game_state.models import GameStateReference
from maple_agent.reflex.models import ReflexReference, ReflexStateType
from maple_agent.safety_gate.models import SafetyDecisionType


class SafetyRules:
    """HP 风险 / 死亡风险 / 未知目标 / 非法动作 判定。"""

    @staticmethod
    def evaluate(
        action: ActionProposalReference,
        *,
        game_state: GameStateReference | None = None,
        reflex: ReflexReference | None = None,
        target_known: bool | None = None,
    ) -> tuple[SafetyDecisionType, list[str], list[str]]:
        risk_factors: list[str] = []
        reasoning: list[str] = []
        if action.action_type not in set(ActionType):
            return (
                SafetyDecisionType.BLOCKED,
                ["invalid action"],
                ["动作类型不存在,直接阻止"],
            )
        if reflex is not None and reflex.state is ReflexStateType.DEATH:
            return (
                SafetyDecisionType.BLOCKED,
                ["death risk"],
                ["检测到死亡状态,任何动作均阻止"],
            )
        decision = SafetyDecisionType.ALLOW
        hp = (
            game_state.player_state.hp
            if game_state is not None
            and game_state.player_state is not None
            else None
        )
        if (
            hp is not None
            and hp < 0.3
            and action.action_type is ActionType.COMBAT
        ):
            decision = SafetyDecisionType.WARNING
            risk_factors.append("hp low combat risk")
            reasoning.append("HP 低于 0.3 且为战斗动作,降级为警告")
        known = (
            bool(action.target_reference)
            if target_known is None
            else target_known
        )
        if not known:
            decision = SafetyDecisionType.WARNING
            risk_factors.append("unknown target")
            reasoning.append("目标未知,降级为警告")
        if decision is SafetyDecisionType.ALLOW:
            reasoning.append("未命中安全风险规则")
        return decision, list(dict.fromkeys(risk_factors)), reasoning
