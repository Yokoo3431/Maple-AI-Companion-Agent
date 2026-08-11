"""DecisionRiskIntegrator:环境与失败智能风险融合(只读)。"""

from __future__ import annotations

from maple_agent.decision_reference.models import DecisionRiskNotes
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.failure_intelligence.models import (
    FailurePreventionReference,
)


class DecisionRiskIntegrator:
    """融合环境参考与失败预防,生成风险提示/规避/备选。"""

    def integrate(
        self,
        *,
        environment_reference: EnvironmentPlanningReference,
        failure_prevention: FailurePreventionReference | None = None,
    ) -> DecisionRiskNotes:
        risk_notes = list(environment_reference.risk_notes)
        avoid_options: list[str] = []
        alternative_suggestions: list[str] = []
        if failure_prevention is not None:
            if failure_prevention.avoid_tasks:
                avoid_options = list(failure_prevention.avoid_tasks)
                risk_notes.append(
                    "应避免任务: "
                    + ", ".join(failure_prevention.avoid_tasks)
                )
            if failure_prevention.risk_warnings:
                risk_notes.extend(failure_prevention.risk_warnings)
            if failure_prevention.recovery_points:
                alternative_suggestions = list(
                    failure_prevention.recovery_points
                )
                risk_notes.append(
                    "备用恢复点: "
                    + ", ".join(failure_prevention.recovery_points)
                )
        risk_level = self._risk_level(
            environment_reference,
            failure_prevention,
        )
        return DecisionRiskNotes(
            risk_level=risk_level,
            risk_notes=risk_notes,
            avoid_options=avoid_options,
            alternative_suggestions=alternative_suggestions,
        )

    @staticmethod
    def _risk_level(
        environment_reference: EnvironmentPlanningReference,
        failure_prevention: FailurePreventionReference | None,
    ) -> str:
        if environment_reference.blocked_goals:
            return "HIGH"
        if (
            environment_reference.risk_notes
            or (
                failure_prevention is not None
                and failure_prevention.risk_warnings
            )
        ):
            return "MEDIUM"
        return "LOW"
