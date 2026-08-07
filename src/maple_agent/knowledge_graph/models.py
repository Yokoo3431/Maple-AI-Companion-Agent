"""Knowledge Graph 节点与关系模型(Phase 4-A)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RelationType(StrEnum):
    """关系类型。"""

    CONTAINS = "CONTAINS"
    LOCATED_AT = "LOCATED_AT"
    SPAWNS = "SPAWNS"
    REQUIRES = "REQUIRES"
    REWARD = "REWARD"
    DROPS = "DROPS"
    CONNECTED_TO = "CONNECTED_TO"


class MapNode(BaseModel):
    """地图节点。"""

    map_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    region: str = ""
    parent_region: str = ""
    connections: list[int | str] = Field(default_factory=list)


class NPCNode(BaseModel):
    """NPC 节点。"""

    npc_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    location: int | str | None = None
    description: str = ""


class MonsterNode(BaseModel):
    """怪物节点。"""

    monster_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    location: int | str | None = None
    level: int | None = None
    drops: list[int | str] = Field(default_factory=list)


class ItemNode(BaseModel):
    """物品节点。"""

    item_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)


class Relation(BaseModel):
    """实体关系。"""

    source: str
    source_id: int | str
    target: str
    target_id: int | str
    relation_type: RelationType
