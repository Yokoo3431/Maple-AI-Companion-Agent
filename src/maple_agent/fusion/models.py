"""WorldState 领域模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.knowledge.models import MapInfo, MonsterInfo, NpcInfo


class WorldState(BaseModel):
    """当前游戏世界状态的融合摘要(Vision × Knowledge)。"""

    current_map: MapInfo | None = None
    known_npcs: list[NpcInfo] = Field(default_factory=list)
    known_monsters: list[MonsterInfo] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    trace_id: str = ""
