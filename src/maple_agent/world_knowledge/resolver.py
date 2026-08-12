"""WorldKnowledgeResolver:GameState + MapleKnowledge -> WorldKnowledgeReference。"""

from __future__ import annotations

from maple_agent.game_state.models import GameStateReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import WorldKnowledgeReference


class WorldKnowledgeResolver:
    """把当前游戏状态映射到世界知识参考(只读)。"""

    def __init__(self, graph: MapGraph) -> None:
        self.graph = graph
        self.last_reference: WorldKnowledgeReference | None = None

    def resolve(
        self,
        *,
        game_state_reference: GameStateReference | None = None,
        maple_knowledge_reference: MapleKnowledgeReference | None = None,
    ) -> WorldKnowledgeReference:
        current_map = ""
        if (
            game_state_reference is not None
            and game_state_reference.current_map is not None
        ):
            current_map = game_state_reference.current_map.map_name
        known_maps = self.graph.known_map_names()
        reachable = (
            self.graph.find_reachable_maps(current_map)
            if current_map
            else []
        )
        connections = (
            self.graph.find_connections(current_map)
            if current_map
            else []
        )
        related_npcs = (
            self.graph.find_related_npcs(current_map)
            if current_map
            else []
        )
        related_monsters = (
            self.graph.find_related_monsters(current_map)
            if current_map
            else []
        )
        related_quests = (
            self.graph.find_related_quests(current_map)
            if current_map
            else []
        )
        if not related_npcs and maple_knowledge_reference is not None:
            related_npcs = list(maple_knowledge_reference.related_npcs)
        if not related_quests and maple_knowledge_reference is not None:
            related_quests = list(
                maple_knowledge_reference.related_quests
            )
        node = self.graph.find_map(current_map) if current_map else None
        confidence = (
            node.confidence
            if node is not None
            else (
                game_state_reference.confidence
                if game_state_reference is not None
                else 0.0
            )
        )
        reasoning = [
            f"当前地图: {current_map or '未知'}",
            f"已知地图: {len(known_maps)}",
            f"可达地图: {', '.join(reachable) or '无'}",
        ]
        reference = WorldKnowledgeReference(
            current_map=current_map,
            known_maps=known_maps,
            reachable_maps=reachable,
            map_connections=connections,
            related_npcs=sorted(set(related_npcs)),
            related_monsters=sorted(set(related_monsters)),
            related_quests=sorted(set(related_quests)),
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference
