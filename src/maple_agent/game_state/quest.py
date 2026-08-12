"""QuestStateParser:ScreenObservation + Knowledge -> QuestStateSnapshot(确定性)。"""

from __future__ import annotations

from maple_agent.game_state.models import QuestStateSnapshot
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import (
    KnowledgeRelationType,
    MapleKnowledgeType,
)
from maple_agent.vision_runtime.models import ScreenObservation


class QuestStateParser:
    """区分进行中 / 可接取 / 完成参考。"""

    def __init__(self, graph: MapleKnowledgeGraph | None = None) -> None:
        self.graph = graph

    def parse(
        self,
        observation: ScreenObservation,
    ) -> QuestStateSnapshot:
        active = list(observation.quest_reference)
        available: list[str] = []
        if self.graph is not None and observation.visible_entities:
            visible_names = set(observation.visible_entities)
            for entity in self.graph.find_by_type(
                MapleKnowledgeType.QUEST
            ):
                if entity.name in active:
                    continue
                for relation, target in self.graph.find_related(
                    entity.knowledge_id
                ):
                    if (
                        relation.relation_type
                        is KnowledgeRelationType.REQUIRES
                        and target.name in visible_names
                    ):
                        available.append(entity.name)
                        break
        return QuestStateSnapshot(
            active_quests=sorted(set(active)),
            available_quests=sorted(set(available)),
            completed_reference=[],
        )
