"""CostCalculator:路径成本计算(确定性)。"""

from __future__ import annotations

from maple_agent.navigation.models import RouteStep


class CostCalculator:
    """按步骤类型计算参考成本。"""

    STEP_COST = {
        "MAP_TRANSITION": 1.0,
        "PORTAL_REFERENCE": 1.0,
        "LOCAL_MOVE_REFERENCE": 1.0,
        "NPC_REFERENCE": 1.0,
        "QUEST_TARGET_REFERENCE": 1.0,
    }

    def calculate(self, steps: list[RouteStep]) -> float:
        total = sum(
            self.STEP_COST.get(step.step_type.value, 1.0)
            for step in steps
        )
        return round(total, 4)
