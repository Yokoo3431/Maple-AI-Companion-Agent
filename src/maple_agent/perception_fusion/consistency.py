"""ConsistencyScorer:多源一致性评分(确定性,无 LLM)。"""

from __future__ import annotations

from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.quest_reasoning.models import (
    QuestGoalReference,
    QuestStateType,
)


class ConsistencyScorer:
    """评估 视觉/知识/位置/任务/记忆 的一致性。"""

    def score(
        self,
        *,
        perception: MaplePerceptionReference | None = None,
        knowledge: MapleKnowledgeReference | None = None,
        context: MapleCompanionContextReference | None = None,
        quest: QuestGoalReference | None = None,
        memory: RelevantMemoryReference | None = None,
        semantic: SemanticMemoryReference | None = None,
        human_alignment: HumanAlignedDecisionReference | None = None,
    ) -> float:
        vision_knowledge = self._vision_knowledge(perception, knowledge)
        location = self._location_consistency(perception, context)
        quest_consistency = self._quest_consistency(quest)
        memory_consistency = self._memory_consistency(
            memory,
            semantic,
            human_alignment,
        )
        score = (
            0.35 * vision_knowledge
            + 0.30 * location
            + 0.20 * quest_consistency
            + 0.15 * memory_consistency
        )
        return round(min(1.0, max(0.0, score)), 4)

    @staticmethod
    def _vision_knowledge(
        perception: MaplePerceptionReference | None,
        knowledge: MapleKnowledgeReference | None,
    ) -> float:
        if perception is None or knowledge is None:
            return 0.5
        matches = 0
        checks = 0
        if perception.visible_map:
            checks += 1
            if perception.visible_map in knowledge.related_maps:
                matches += 1
        known = set(
            knowledge.related_npcs
            + knowledge.related_monsters
            + knowledge.related_items
        )
        for entity in perception.visible_entities:
            checks += 1
            if entity.name in known:
                matches += 1
        if checks == 0:
            return 0.5
        return matches / checks

    @staticmethod
    def _location_consistency(
        perception: MaplePerceptionReference | None,
        context: MapleCompanionContextReference | None,
    ) -> float:
        perception_map = (
            perception.visible_map if perception is not None else ""
        )
        context_map = ""
        if context is not None and context.world_context is not None:
            context_map = context.world_context.location
        if not perception_map or not context_map:
            return 0.5
        return 1.0 if perception_map == context_map else 0.0

    @staticmethod
    def _quest_consistency(
        quest: QuestGoalReference | None,
    ) -> float:
        if quest is None or not quest.quest_progress:
            return 0.0
        score = quest.confidence
        if any(
            item.state in (QuestStateType.BLOCKED, QuestStateType.UNKNOWN)
            for item in quest.quest_progress
        ):
            score -= 0.2
        return round(min(1.0, max(0.0, score)), 4)

    @staticmethod
    def _memory_consistency(
        memory: RelevantMemoryReference | None,
        semantic: SemanticMemoryReference | None,
        human_alignment: HumanAlignedDecisionReference | None,
    ) -> float:
        values: list[float] = []
        if memory is not None:
            values.append(memory.confidence)
            if memory.relevant_memories:
                values.append(min(1.0, memory.confidence + 0.1))
        if semantic is not None:
            values.append(semantic.confidence)
        if human_alignment is not None:
            values.append(human_alignment.alignment_score)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
