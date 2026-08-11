"""MaplePlayerContextBuilder:玩家上下文构建(仅参考数据)。"""

from __future__ import annotations

from maple_agent.environment.models import EnvironmentState
from maple_agent.maple_context.models import MaplePlayerContext


class MaplePlayerContextBuilder:
    """从环境状态构建玩家上下文;HP/MP/背包/任务为参考占位。"""

    def build(
        self,
        *,
        player_id: str = "",
        environment_state: EnvironmentState | None = None,
    ) -> MaplePlayerContext:
        location = (
            environment_state.location
            if environment_state is not None
            else ""
        )
        confidence = (
            environment_state.confidence
            if environment_state is not None
            else 0.0
        )
        return MaplePlayerContext(
            player_id=player_id,
            level=0,
            job="",
            location=location,
            current_hp_reference=None,
            current_mp_reference=None,
            inventory_reference=[],
            quest_reference=[],
            confidence=confidence,
        )
