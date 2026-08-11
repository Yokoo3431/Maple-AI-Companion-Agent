"""EnvironmentRiskAdapter:环境风险 -> 规划约束(只读)。"""

from __future__ import annotations

from maple_agent.environment_planning.models import PlanningConstraint
from maple_agent.environment_reasoning.models import (
    EnvironmentRiskReference,
)


class EnvironmentRiskAdapter:
    """按风险等级生成规划约束。"""

    def adapt(
        self,
        *,
        risk_reference: EnvironmentRiskReference,
    ) -> PlanningConstraint:
        if risk_reference.risk_level == "HIGH":
            return PlanningConstraint(
                level="blocked",
                source_risk=risk_reference.risk_level,
                message=risk_reference.reason,
                recommendation="阻断推进,先重新观察环境",
            )
        if risk_reference.risk_level == "MEDIUM":
            return PlanningConstraint(
                level="warning",
                source_risk=risk_reference.risk_level,
                message=risk_reference.reason,
                recommendation="谨慎推进,执行前加强观察",
            )
        return PlanningConstraint(
            level="normal",
            source_risk=risk_reference.risk_level,
            message=risk_reference.reason,
            recommendation="可正常推进",
        )
