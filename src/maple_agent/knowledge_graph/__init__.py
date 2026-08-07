"""Knowledge Graph Foundation(Phase 4-A):地图/NPC/怪物/物品节点与关系查询。"""

from maple_agent.knowledge_graph.builder import build_graph
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import (
    ItemNode,
    MapNode,
    MonsterNode,
    NPCNode,
    Relation,
    RelationType,
)

__all__ = [
    "ItemNode",
    "KnowledgeGraph",
    "MapNode",
    "MonsterNode",
    "NPCNode",
    "Relation",
    "RelationType",
    "build_graph",
]
