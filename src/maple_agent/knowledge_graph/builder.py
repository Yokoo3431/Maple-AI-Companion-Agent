"""从 KnowledgeProvider 构建 KnowledgeGraph。"""

from __future__ import annotations

from typing import TYPE_CHECKING

from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import (
    MapNode,
    MonsterNode,
    NPCNode,
    Relation,
    RelationType,
)

if TYPE_CHECKING:
    from maple_agent.providers.knowledge import KnowledgeProvider


def build_graph(knowledge: KnowledgeProvider) -> KnowledgeGraph:
    """把知识库数据转成图谱节点与关系。"""
    dataset = knowledge.dataset
    if dataset is not None and (dataset.maps or dataset.relations):
        return KnowledgeGraph(
            maps=dataset.maps,
            npcs=dataset.npcs,
            monsters=dataset.monsters,
            items=dataset.items,
            relations=dataset.relations,
        )
    maps = [
        MapNode(
            map_id=item.map_id,
            name=item.name,
            aliases=item.aliases,
            region=item.region,
            parent_region=item.region,
        )
        for item in knowledge.data.maps
    ]
    npcs = [
        NPCNode(
            npc_id=item.npc_id,
            name=item.name,
            aliases=item.aliases,
            location=item.map_id,
        )
        for item in knowledge.data.npcs
    ]
    monsters = [
        MonsterNode(
            monster_id=item.monster_id,
            name=item.name,
            aliases=[],
            location=item.map_id,
            level=item.level,
        )
        for item in knowledge.data.monsters
    ]
    relations: list[Relation] = []
    for npc in npcs:
        if npc.location is not None:
            relations.append(
                Relation(
                    source="map",
                    source_id=npc.location,
                    target="npc",
                    target_id=npc.npc_id,
                    relation_type=RelationType.CONTAINS,
                )
            )
            relations.append(
                Relation(
                    source="npc",
                    source_id=npc.npc_id,
                    target="map",
                    target_id=npc.location,
                    relation_type=RelationType.LOCATED_AT,
                )
            )
    for monster in monsters:
        if monster.location is not None:
            relations.append(
                Relation(
                    source="map",
                    source_id=monster.location,
                    target="monster",
                    target_id=monster.monster_id,
                    relation_type=RelationType.SPAWNS,
                )
            )
    for quest in knowledge.data.quests_domain:
        for requirement in quest.requirements:
            relations.append(
                Relation(
                    source="quest",
                    source_id=quest.quest_id,
                    target="item",
                    target_id=requirement.target,
                    relation_type=RelationType.REQUIRES,
                )
            )
        for reward in quest.rewards:
            relations.append(
                Relation(
                    source="quest",
                    source_id=quest.quest_id,
                    target="item",
                    target_id=reward.target,
                    relation_type=RelationType.REWARD,
                )
            )
    return KnowledgeGraph(
        maps=maps,
        npcs=npcs,
        monsters=monsters,
        items=[],
        relations=relations,
    )
