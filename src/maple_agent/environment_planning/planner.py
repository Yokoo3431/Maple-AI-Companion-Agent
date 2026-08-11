"""EnvironmentAwarePlanner:环境机会+风险 -> 规划参考(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.environment_planning.goal_adapter import EnvironmentGoalAdapter
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
    GoalPriorityReference,
    PlanningConstraint,
)
from maple_agent.environment_planning.risk_adapter import EnvironmentRiskAdapter
from maple_agent.environment_reasoning.models import (
    EnvironmentRiskReference,
    OpportunityReference,
)


class EnvironmentAwarePlanner:
    """组合机会与风险,生成环境规划参考。"""

    def __init__(
        self,
        *,
        goal_adapter: EnvironmentGoalAdapter | None = None,
        risk_adapter: EnvironmentRiskAdapter | None = None,
    ) -> None:
        self.goal_adapter = goal_adapter or EnvironmentGoalAdapter()
        self.risk_adapter = risk_adapter or EnvironmentRiskAdapter()
        self.last_reference: EnvironmentPlanningReference | None = None

    def build_reference(
        self,
        *,
        opportunities: list[OpportunityReference],
        risk_reference: EnvironmentRiskReference,
        goal_id: str = "",
    ) -> EnvironmentPlanningReference:
        adjustments = self.goal_adapter.adapt(
            opportunities=opportunities,
            goal_id=goal_id,
        )
        constraint = self.risk_adapter.adapt(
            risk_reference=risk_reference,
        )
        recommended: list[str] = []
        blocked: list[str] = []
        if constraint.level == "blocked":
            if goal_id:
                blocked.append(goal_id)
        elif goal_id:
            recommended.append(goal_id)
        risk_notes: list[str] = []
        if constraint.level != "normal":
            risk_notes.append(f"[{constraint.level}] {constraint.message}")
        opportunity_notes = [
            f"{adjustment.opportunity_type}: {adjustment.reason}"
            for adjustment in adjustments
        ]
        confidence = self._confidence(opportunities, risk_reference)
        reference = EnvironmentPlanningReference(
            recommended_goals=recommended,
            blocked_goals=blocked,
            priority_adjustments=adjustments,
            risk_notes=risk_notes,
            opportunity_notes=opportunity_notes,
            confidence=confidence,
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _confidence(
        opportunities: list[OpportunityReference],
        risk_reference: EnvironmentRiskReference,
    ) -> float:
        base = min(
            (opportunity.confidence for opportunity in opportunities),
            default=0.5,
        )
        if risk_reference.risk_level == "HIGH":
            base *= 0.5
        elif risk_reference.risk_level == "MEDIUM":
            base *= 0.8
        return round(min(1.0, base), 4)


def save_environment_planning_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    environment_reference: EnvironmentPlanningReference,
    goal_adjustments: list[GoalPriorityReference],
    risk_constraints: list[PlanningConstraint],
) -> None:
    """写入 environment_planning_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "environment_reference": environment_reference.model_dump(
            mode="json"
        ),
        "goal_adjustments": [
            adjustment.model_dump(mode="json")
            for adjustment in goal_adjustments
        ],
        "risk_constraints": [
            constraint.model_dump(mode="json")
            for constraint in risk_constraints
        ],
    }
    (directory / "environment_planning_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
