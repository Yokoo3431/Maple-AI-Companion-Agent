"""EnvironmentGoalAdapter:环境机会 -> 目标优先级参考(只读)。"""

from __future__ import annotations

from maple_agent.environment_planning.models import GoalPriorityReference
from maple_agent.environment_reasoning.models import (
    OpportunityReference,
    OpportunityType,
)


class EnvironmentGoalAdapter:
    """按机会类型调整目标优先级建议。"""

    _MAPPING = {
        OpportunityType.NPC_INTERACTION: (
            85,
            "环境有 NPC 可交互,适合推进对话类目标",
        ),
        OpportunityType.RESOURCE_AVAILABLE: (
            80,
            "环境资源可用,适合收集类目标",
        ),
        OpportunityType.TASK_PROGRESS: (
            75,
            "环境稳定,可推进任务进度",
        ),
        OpportunityType.SAFE_AREA: (
            70,
            "安全区域,适合低风险执行",
        ),
        OpportunityType.NEW_DISCOVERY: (
            65,
            "新发现区域,适合探索目标",
        ),
    }

    def adapt(
        self,
        *,
        opportunities: list[OpportunityReference],
        goal_id: str = "",
    ) -> list[GoalPriorityReference]:
        adjustments: list[GoalPriorityReference] = []
        for opportunity in opportunities:
            if opportunity.opportunity_type not in self._MAPPING:
                continue
            priority, reason = self._MAPPING[
                opportunity.opportunity_type
            ]
            adjustments.append(
                GoalPriorityReference(
                    goal_id=goal_id,
                    suggested_priority=priority,
                    reason=reason,
                    opportunity_type=opportunity.opportunity_type.value,
                    confidence=opportunity.confidence,
                )
            )
        return adjustments
