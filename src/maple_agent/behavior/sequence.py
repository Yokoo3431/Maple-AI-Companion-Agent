"""BehaviorSequenceBuilder:行为步骤排序/组合(确定性)。"""

from __future__ import annotations

from maple_agent.behavior.models import BehaviorStep, BehaviorStepType


class BehaviorSequenceBuilder:
    """确保导航在前、验证在最后,等待优先。"""

    _ORDER = {
        BehaviorStepType.WAIT_REFERENCE: 0,
        BehaviorStepType.NAVIGATE_REFERENCE: 1,
        BehaviorStepType.QUEST_ANALYSIS: 2,
        BehaviorStepType.INTERACT_REFERENCE: 3,
        BehaviorStepType.COMBAT_REFERENCE: 3,
        BehaviorStepType.COLLECT_REFERENCE: 3,
        BehaviorStepType.VERIFY_REFERENCE: 4,
    }

    def order(self, steps: list[BehaviorStep]) -> list[BehaviorStep]:
        return sorted(
            steps,
            key=lambda step: self._ORDER.get(step.step_type, 2),
        )
