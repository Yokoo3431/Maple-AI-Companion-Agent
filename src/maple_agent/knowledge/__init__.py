"""Maple 游戏知识库基础层(Phase 1.3)。"""

from maple_agent.knowledge.loader import KnowledgeData, detect_profile, load_profile
from maple_agent.knowledge.models import (
    KnowledgeProfile,
    MapDictionary,
    MapInfo,
    MonsterInfo,
    NpcInfo,
    QuestTemplate,
)

__all__ = [
    "KnowledgeData",
    "KnowledgeProfile",
    "MapDictionary",
    "MapInfo",
    "MonsterInfo",
    "NpcInfo",
    "QuestTemplate",
    "detect_profile",
    "load_profile",
]
