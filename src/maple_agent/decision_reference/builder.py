"""DecisionReferenceBuilder:环境/世界/规划/失败智能 -> 决策参考(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.decision_reference.models import (
    DecisionReference,
    DecisionScore,
    ReferenceOption,
)
from maple_agent.decision_reference.risk import DecisionRiskIntegrator
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.environment_reasoning.models import OpportunityType
from maple_agent.failure_intelligence.models import (
    FailurePreventionReference,
)
from maple_agent.planning_optimizer.models import PlanningQualityScore
from maple_agent.world_model.models import PredictedEnvironmentState


class DecisionReferenceBuilder:
    """组合环境参考/世界预测/失败预防/规划质量。"""

    _ACTION_MAP = {
        OpportunityType.NPC_INTERACTION: "TALK",
        OpportunityType.RESOURCE_AVAILABLE: "COLLECT",
        OpportunityType.TASK_PROGRESS: "OBSERVE",
        OpportunityType.SAFE_AREA: "OBSERVE",
        OpportunityType.NEW_DISCOVERY: "MOVE_HINT",
    }

    def __init__(
        self,
        *,
        risk_integrator: DecisionRiskIntegrator | None = None,
    ) -> None:
        self.risk_integrator = (
            risk_integrator or DecisionRiskIntegrator()
        )
        self.last_reference: DecisionReference | None = None

    def build(
        self,
        *,
        environment_reference: EnvironmentPlanningReference,
        world_prediction: PredictedEnvironmentState | None = None,
        failure_prevention: FailurePreventionReference | None = None,
        planning_quality: PlanningQualityScore | None = None,
        goal_id: str = "",
    ) -> DecisionReference:
        risk_notes = self.risk_integrator.integrate(
            environment_reference=environment_reference,
            failure_prevention=failure_prevention,
        )
        recommended, alternatives = self._options(
            environment_reference,
            risk_notes,
            goal_id,
        )
        environment_alignment = self._environment_alignment(
            environment_reference,
        )
        planning_alignment = self._planning_alignment(planning_quality)
        confidence = self._confidence(
            environment_alignment,
            planning_alignment,
            risk_notes.risk_level,
        )
        reasoning = self._reasoning(
            environment_reference,
            world_prediction,
            risk_notes,
            goal_id,
        )
        reference = DecisionReference(
            recommended_options=recommended,
            alternative_options=alternatives,
            risk_level=risk_notes.risk_level,
            confidence=confidence,
            reasoning=reasoning,
            environment_alignment=environment_alignment,
            planning_alignment=planning_alignment,
        )
        self.last_reference = reference
        return reference

    def _options(
        self,
        environment_reference: EnvironmentPlanningReference,
        risk_notes,
        goal_id: str,
    ) -> tuple[list[ReferenceOption], list[ReferenceOption]]:
        recommended: list[ReferenceOption] = []
        alternatives: list[ReferenceOption] = []
        if risk_notes.risk_level == "HIGH":
            for suggestion in risk_notes.alternative_suggestions:
                alternatives.append(
                    ReferenceOption(
                        option_id=f"alt-{len(alternatives) + 1}",
                        action="OBSERVE",
                        target=suggestion,
                        recommendation="alternative",
                        confidence=0.4,
                        reason="高风险下仅提供备选观察建议",
                    )
                )
            return recommended, alternatives
        for adjustment in environment_reference.priority_adjustments:
            opportunity_type = self._to_opportunity_type(
                adjustment.opportunity_type
            )
            if opportunity_type is None:
                continue
            action = self._ACTION_MAP.get(opportunity_type, "OBSERVE")
            recommended.append(
                ReferenceOption(
                    option_id=f"opt-{adjustment.opportunity_type}",
                    action=action,
                    target=goal_id,
                    recommendation="recommended",
                    confidence=adjustment.confidence,
                    reason=adjustment.reason,
                )
            )
        for avoid in risk_notes.avoid_options:
            alternatives.append(
                ReferenceOption(
                    option_id=f"avoid-{avoid}",
                    action="QUERY_KNOWLEDGE",
                    target=avoid,
                    recommendation="alternative",
                    confidence=0.3,
                    reason=f"规避历史失败点 {avoid}",
                )
            )
        return recommended, alternatives

    @staticmethod
    def _to_opportunity_type(value: str) -> OpportunityType | None:
        try:
            return OpportunityType(value)
        except ValueError:
            return None

    @staticmethod
    def _environment_alignment(
        environment_reference: EnvironmentPlanningReference,
    ) -> float:
        if environment_reference.confidence <= 0:
            return 0.0
        base = environment_reference.confidence
        if environment_reference.blocked_goals:
            base *= 0.3
        return round(min(1.0, base), 4)

    @staticmethod
    def _planning_alignment(
        planning_quality: PlanningQualityScore | None,
    ) -> float:
        if planning_quality is None:
            return 0.5
        return planning_quality.planning_score

    @staticmethod
    def _confidence(
        environment_alignment: float,
        planning_alignment: float,
        risk_level: str,
    ) -> float:
        base = (
            environment_alignment * 0.5
            + planning_alignment * 0.3
            + 0.2
        )
        if risk_level == "HIGH":
            base *= 0.5
        elif risk_level == "MEDIUM":
            base *= 0.8
        return round(min(1.0, base), 4)

    @staticmethod
    def _reasoning(
        environment_reference: EnvironmentPlanningReference,
        world_prediction: PredictedEnvironmentState | None,
        risk_notes,
        goal_id: str,
    ) -> list[str]:
        reasoning: list[str] = []
        if environment_reference.opportunity_notes:
            reasoning.extend(environment_reference.opportunity_notes)
        if world_prediction is not None and world_prediction.summary:
            reasoning.append(f"世界预测: {world_prediction.summary}")
        if risk_notes.risk_notes:
            reasoning.extend(risk_notes.risk_notes)
        if goal_id:
            reasoning.append(f"目标: {goal_id}")
        return reasoning or ["无参考依据"]


def save_decision_reference_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    decision_reference: DecisionReference,
    score: DecisionScore,
    risk_notes: list[str],
) -> None:
    """写入 decision_reference_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "decision_reference": decision_reference.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
        "risk_notes": risk_notes,
    }
    (directory / "decision_reference_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
