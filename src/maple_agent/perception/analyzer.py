"""ObservationAnalyzer:VisualObservation -> PerceivedEntity(确定性规则,无 AI)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import MapleKnowledgeType
from maple_agent.perception.models import (
    PerceivedEntity,
    PerceivedEntityType,
    VisualObservation,
)


class ObservationAnalyzer:
    """把观察元素按知识库类型归类为感知实体。"""

    _TYPE_MAPPING = {
        MapleKnowledgeType.NPC: PerceivedEntityType.NPC,
        MapleKnowledgeType.MONSTER: PerceivedEntityType.MONSTER,
        MapleKnowledgeType.ITEM: PerceivedEntityType.ITEM,
        MapleKnowledgeType.MAP: PerceivedEntityType.MAP_LABEL,
    }

    def analyze(
        self,
        observation: VisualObservation,
        knowledge: MapleKnowledgeGraph | None = None,
    ) -> list[PerceivedEntity]:
        entities: list[PerceivedEntity] = []
        location = observation.context.get("location", "")
        if location:
            entities.append(
                PerceivedEntity(
                    entity_id=new_id(),
                    entity_type=PerceivedEntityType.MAP_LABEL,
                    name=str(location),
                    confidence=observation.confidence,
                )
            )
        for element in observation.detected_elements:
            entities.append(
                PerceivedEntity(
                    entity_id=new_id(),
                    entity_type=self._classify(element, knowledge),
                    name=element,
                    confidence=observation.confidence,
                )
            )
        ui_state = observation.context.get("ui_state", "")
        if ui_state:
            entities.append(
                PerceivedEntity(
                    entity_id=new_id(),
                    entity_type=PerceivedEntityType.UI_ELEMENT,
                    name=str(ui_state),
                    confidence=observation.confidence,
                )
            )
        return entities

    def _classify(
        self,
        name: str,
        knowledge: MapleKnowledgeGraph | None,
    ) -> PerceivedEntityType:
        if knowledge is None:
            return PerceivedEntityType.UNKNOWN
        entity = knowledge.find_by_name(name)
        if entity is None:
            return PerceivedEntityType.UNKNOWN
        return self._TYPE_MAPPING.get(
            entity.knowledge_type,
            PerceivedEntityType.UNKNOWN,
        )
