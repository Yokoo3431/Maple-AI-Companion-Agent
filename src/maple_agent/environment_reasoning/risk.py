"""EnvironmentRiskAnalyzer:环境风险评估(只读)。"""

from __future__ import annotations

from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_reasoning.models import (
    EnvironmentInterpretation,
    EnvironmentRiskReference,
)
from maple_agent.world_model.models import EnvironmentHistory


class EnvironmentRiskAnalyzer:
    """基于状态/解释/历史评估环境风险。"""

    _HIGH_RISK_LOCATIONS = ("危险区域", "未知区域")

    def analyze(
        self,
        *,
        environment_state: EnvironmentState,
        interpretation: EnvironmentInterpretation | None = None,
        history: EnvironmentHistory | None = None,
        goal_ids: list[str] | None = None,
    ) -> EnvironmentRiskReference:
        if environment_state.confidence < 0.5:
            return EnvironmentRiskReference(
                risk_level="HIGH",
                reason="环境置信度过低,状态不可靠",
                affected_goals=goal_ids or [],
                recommendation="重新观察环境后再决策",
            )
        if environment_state.location in self._HIGH_RISK_LOCATIONS:
            return EnvironmentRiskReference(
                risk_level="HIGH",
                reason=f"位于高风险区域: {environment_state.location}",
                affected_goals=goal_ids or [],
                recommendation="谨慎推进或先确认安全",
            )
        if environment_state.conditions.get("conflict") is True:
            return EnvironmentRiskReference(
                risk_level="MEDIUM",
                reason="环境条件冲突",
                affected_goals=goal_ids or [],
                recommendation="交叉验证环境信息",
            )
        if environment_state.confidence < 0.7:
            return EnvironmentRiskReference(
                risk_level="MEDIUM",
                reason="环境置信度中等",
                affected_goals=goal_ids or [],
                recommendation="执行前加强观察",
            )
        return EnvironmentRiskReference(
            risk_level="LOW",
            reason="环境稳定",
            affected_goals=goal_ids or [],
            recommendation="可正常推进",
        )
