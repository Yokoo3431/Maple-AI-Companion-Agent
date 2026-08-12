"""Maple Game Knowledge 数据模型(Phase 9-D,领域知识层,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MapleKnowledgeType(StrEnum):
    """冒险岛知识类型。"""

    MAP = "MAP"
    NPC = "NPC"
    MONSTER = "MONSTER"
    ITEM = "ITEM"
    QUEST = "QUEST"
    JOB = "JOB"
    SKILL = "SKILL"
    GAME_RULE = "GAME_RULE"


class MapleKnowledgeEntity(BaseModel):
    """冒险岛知识实体。"""

    knowledge_id: str
    knowledge_type: MapleKnowledgeType
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    attributes: dict = Field(default_factory=dict)
    source: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class KnowledgeRelationType(StrEnum):
    """知识关系类型。"""

    LOCATED_IN = "LOCATED_IN"
    REQUIRES = "REQUIRES"
    REWARDS = "REWARDS"
    DROPS = "DROPS"
    BELONGS_TO = "BELONGS_TO"
    UNLOCKS = "UNLOCKS"
    RELATED_TO = "RELATED_TO"


class KnowledgeRelation(BaseModel):
    """知识实体关系。"""

    relation_id: str
    source_id: str
    target_id: str
    relation_type: KnowledgeRelationType
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapleKnowledgeReference(BaseModel):
    """知识检索参考(只读,非 Action)。"""

    related_npcs: list[str] = Field(default_factory=list)
    related_maps: list[str] = Field(default_factory=list)
    related_monsters: list[str] = Field(default_factory=list)
    related_items: list[str] = Field(default_factory=list)
    related_quests: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
