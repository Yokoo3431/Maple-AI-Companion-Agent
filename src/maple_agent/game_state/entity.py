"""EntityStateParser:ScreenObservation + Knowledge -> EntityStateReference(确定性)。"""

from __future__ import annotations

from maple_agent.game_state.models import EntityStateReference
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import MapleKnowledgeType
from maple_agent.vision_runtime.models import ScreenObservation


class EntityStateParser:
    """把可见实体与知识库类型绑定。"""

    _TYPE_MAPPING = {
        MapleKnowledgeType.NPC: "NPC",
        MapleKnowledgeType.MONSTER: "MONSTER",
        MapleKnowledgeType.ITEM: "ITEM",
        MapleKnowledgeType.MAP: "MAP",
    }

    def __init__(self, graph: MapleKnowledgeGraph | None = None) -> None:
        self.graph = graph

    def parse(
        self,
        observation: ScreenObservation,
    ) -> list[EntityStateReference]:
        entities: list[EntityStateReference] = []
        for name in observation.visible_entities:
            entity_type = "UNKNOWN"
            if self.graph is not None:
                entity = self.graph.find_by_name(name)
                if entity is not None:
                    entity_type = self._TYPE_MAPPING.get(
                        entity.knowledge_type,
                        "UNKNOWN",
                    )
            entities.append(
                EntityStateReference(
                    name=name,
                    type=entity_type,
                    position_reference={},
                    confidence=observation.confidence,
                )
            )
        return entities
