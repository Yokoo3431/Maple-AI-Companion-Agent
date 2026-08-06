"""知识库领域模型(Pydantic schema)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class MapInfo(BaseModel):
    """地图信息。"""

    map_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    region: str = ""
    version: str = ""


class NpcInfo(BaseModel):
    """NPC 信息。"""

    npc_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    map_id: int | str | None = None
    version: str = ""


class MonsterInfo(BaseModel):
    """怪物信息。"""

    monster_id: int | str
    name: str
    level: int | None = None
    hp: int | None = None
    map_id: int | str | None = None
    version: str = ""


class QuestTemplate(BaseModel):
    """任务模板。"""

    quest_id: int | str
    name: str
    npc_id: int | str | None = None
    map_id: int | str | None = None
    requirements: dict[str, str] = Field(default_factory=dict)
    rewards: dict[str, str] = Field(default_factory=dict)
    version: str = ""


class MapDictionary(BaseModel):
    """地图名 → 别名列表(OCR 纠错用)。"""

    entries: dict[str, list[str]] = Field(default_factory=dict)


class KnowledgeProfile(BaseModel):
    """知识档案元信息(profile.json)。"""

    game_profile: str
    version: str = ""
    maps: int = 0
    npcs: int = 0
    monsters: int = 0
    quests: int = 0
