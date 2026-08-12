"""SafetyEvaluator:ActionProposal -> SafetyEvaluationReference(只读)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import ActionProposalReference
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.reflex.models import ReflexReference
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_gate.rules import SafetyRules


class SafetyEvaluator:
    """对动作建议执行安全审核。"""

    _CONFIDENCE = {
        SafetyDecisionType.ALLOW: 0.95,
        SafetyDecisionType.WARNING: 0.8,
        SafetyDecisionType.BLOCKED: 0.9,
    }

    def __init__(
        self,
        rules: SafetyRules | None = None,
    ) -> None:
        self.rules = rules or SafetyRules()
        self.last_evaluation: SafetyEvaluationReference | None = None

    def evaluate(
        self,
        action: ActionProposalReference,
        *,
        game_state_reference: GameStateReference | None = None,
        reflex_reference: ReflexReference | None = None,
        target_known: bool | None = None,
    ) -> SafetyEvaluationReference:
        decision, risk_factors, reasoning = self.rules.evaluate(
            action,
            game_state=game_state_reference,
            reflex=reflex_reference,
            target_known=target_known,
        )
        evaluation = SafetyEvaluationReference(
            evaluation_id=new_id(),
            source_action=(
                f"{getattr(action.action_type, 'value', action.action_type)}: "
                f"{action.target_reference}"
            ),
            decision=decision,
            risk_factors=risk_factors,
            reasoning=reasoning,
            confidence=self._CONFIDENCE[decision],
            validation="",
        )
        self.last_evaluation = evaluation
        return evaluation
