"""Maple World Knowledge 数据模型(Phase 11-C,世界知识图谱参考,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class MapConnectionType(StrEnum):
    """地图连接类型。"""

    PORTAL = "PORTAL"
    WALKABLE = "WALKABLE"
    TELEPORT = "TELEPORT"
    QUEST_UNLOCK = "QUEST_UNLOCK"


class MapNodeReference(BaseModel):
    """地图节点参考。"""

    map_id: str
    map_name: str
    aliases: list[str] = Field(default_factory=list)
    region: str = ""
    map_type: str = ""
    description: str = ""
    npc_references: list[str] = Field(default_factory=list)
    monster_references: list[str] = Field(default_factory=list)
    quest_references: list[str] = Field(default_factory=list)
    portal_references: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapConnectionReference(BaseModel):
    """地图连接参考(仅图信息,不是导航指令)。"""

    source_map: str
    target_map: str
    connection_type: MapConnectionType = MapConnectionType.PORTAL
    direction_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class WorldKnowledgeReference(BaseModel):
    """世界知识参考(不是 Action / Navigation 指令)。"""

    current_map: str = ""
    known_maps: list[str] = Field(default_factory=list)
    reachable_maps: list[str] = Field(default_factory=list)
    map_connections: list[MapConnectionReference] = Field(
        default_factory=list
    )
    related_npcs: list[str] = Field(default_factory=list)
    related_monsters: list[str] = Field(default_factory=list)
    related_quests: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
