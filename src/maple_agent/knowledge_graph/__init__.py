"""Knowledge Graph Foundation(Phase 4-A):地图/NPC/怪物/物品节点与关系查询。"""

from maple_agent.knowledge_graph.builder import build_graph
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import (
    EquipmentNode,
    ItemNode,
    KnowledgeEntityProvenance,
    MapNode,
    MonsterNode,
    NPCNode,
    QuestNode,
    Relation,
    RelationType,
    StoryLoreNode,
)

__all__ = [
    "ItemNode",
    "EquipmentNode",
    "KnowledgeEntityProvenance",
    "KnowledgeGraph",
    "MapNode",
    "MonsterNode",
    "NPCNode",
    "QuestNode",
    "Relation",
    "RelationType",
    "StoryLoreNode",
    "build_graph",
]
