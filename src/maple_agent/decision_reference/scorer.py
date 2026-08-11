"""DecisionScorer:决策质量评分(只读)。"""

from __future__ import annotations

from maple_agent.decision_reference.models import (
    DecisionReference,
    DecisionScore,
)


class DecisionScorer:
    """DecisionScore = 0.3*Env + 0.3*Plan + 0.2*Risk + 0.2*Success。"""

    @staticmethod
    def score(
        *,
        reference: DecisionReference,
        historical_success: float = 0.5,
    ) -> DecisionScore:
        environment_alignment = reference.environment_alignment
        planning_alignment = reference.planning_alignment
        risk_awareness = DecisionScorer._risk_awareness(
            reference.risk_level,
        )
        decision_score = round(
            0.3 * environment_alignment
            + 0.3 * planning_alignment
            + 0.2 * risk_awareness
            + 0.2 * historical_success,
            4,
        )
        return DecisionScore(
            decision_score=decision_score,
            environment_alignment=environment_alignment,
            planning_alignment=planning_alignment,
            risk_awareness=risk_awareness,
            historical_success=historical_success,
            components={
                "environment_alignment": environment_alignment,
                "planning_alignment": planning_alignment,
                "risk_awareness": risk_awareness,
                "historical_success": historical_success,
            },
        )

    @staticmethod
    def _risk_awareness(risk_level: str) -> float:
        return {
            "LOW": 1.0,
            "MEDIUM": 0.6,
            "HIGH": 0.2,
        }.get(risk_level, 0.5)
