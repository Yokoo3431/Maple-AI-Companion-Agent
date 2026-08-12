"""Spatial World Model 数据模型(Phase 11-D,空间认知参考,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class PortalReference(BaseModel):
    """地图传送门参考(仅空间信息,不是移动指令)。"""

    portal_id: str
    source_map: str
    target_map: str
    position_reference: dict = Field(default_factory=dict)
    direction_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class SpatialMapReference(BaseModel):
    """地图内部空间参考。"""

    map_id: str
    map_name: str
    width_reference: int = 0
    height_reference: int = 0
    platforms: list[dict] = Field(default_factory=list)
    portals: list[PortalReference] = Field(default_factory=list)
    npc_locations: list[dict] = Field(default_factory=list)
    monster_zones: list[dict] = Field(default_factory=list)
    quest_zones: list[dict] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class SpatialWorldReference(BaseModel):
    """空间世界参考(全部为 Reference,不是移动命令)。"""

    current_map: str = ""
    nearby_points: list[dict] = Field(default_factory=list)
    portals: list[PortalReference] = Field(default_factory=list)
    npc_positions: list[dict] = Field(default_factory=list)
    quest_targets: list[dict] = Field(default_factory=list)
    spatial_confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
