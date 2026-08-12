"""PlayerStateParser:ScreenObservation -> PlayerStateReference(确定性)。"""

from __future__ import annotations

from maple_agent.game_state.models import PlayerStateReference
from maple_agent.vision_runtime.models import ScreenObservation


class PlayerStateParser:
    """从屏幕观察提取玩家 HP/MP 参考。"""

    @staticmethod
    def parse(
        observation: ScreenObservation,
    ) -> PlayerStateReference:
        return PlayerStateReference(
            hp=observation.hp_reference,
            mp=observation.mp_reference,
            level_reference=None,
            job_reference="",
            position_reference={},
        )
