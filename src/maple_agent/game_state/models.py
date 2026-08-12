"""Game State Understanding 数据模型(Phase 11-B,结构化 Maple 状态,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PlayerStateReference(BaseModel):
    """玩家状态参考。"""

    hp: float | None = Field(default=None, ge=0, le=1)
    mp: float | None = Field(default=None, ge=0, le=1)
    level_reference: int | None = None
    job_reference: str = ""
    position_reference: dict = Field(default_factory=dict)


class MapStateReference(BaseModel):
    """地图状态参考。"""

    map_name: str = ""
    known_map: bool = False
    exits_reference: list[str] = Field(default_factory=list)


class EntityStateReference(BaseModel):
    """可见实体状态参考。"""

    name: str
    type: str = "UNKNOWN"
    position_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class QuestStateSnapshot(BaseModel):
    """任务状态快照(参考)。"""

    active_quests: list[str] = Field(default_factory=list)
    available_quests: list[str] = Field(default_factory=list)
    completed_reference: list[str] = Field(default_factory=list)


class GameStateReference(BaseModel):
    """结构化 Maple 游戏状态(不是 Action)。"""

    state_id: str
    player_state: PlayerStateReference | None = None
    current_map: MapStateReference | None = None
    visible_entities: list[EntityStateReference] = Field(
        default_factory=list
    )
    quest_state: QuestStateSnapshot | None = None
    combat_state: str = "UNKNOWN"
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
