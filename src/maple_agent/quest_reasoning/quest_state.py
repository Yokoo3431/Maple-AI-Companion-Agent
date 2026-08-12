"""QuestStateAnalyzer:感知/上下文/知识 -> 任务状态(确定性规则,无 AI)。"""

from __future__ import annotations

from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import (
    KnowledgeRelationType,
    MapleKnowledgeReference,
    MapleKnowledgeType,
)
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.quest_reasoning.models import (
    QuestProgressReference,
    QuestReference,
    QuestStateType,
)


class QuestStateAnalyzer:
    """根据知识图谱与感知/上下文参考推断任务状态。"""

    def __init__(self, graph: MapleKnowledgeGraph) -> None:
        self.graph = graph
        self.last_quests: list[QuestReference] = []
        self.last_progress: list[QuestProgressReference] = []

    def analyze(
        self,
        *,
        context: MapleCompanionContextReference | None = None,
        knowledge_reference: MapleKnowledgeReference | None = None,
        perception_reference: MaplePerceptionReference | None = None,
    ) -> tuple[list[QuestReference], list[QuestProgressReference]]:
        quest_names = (
            list(knowledge_reference.related_quests)
            if knowledge_reference is not None
            else []
        )
        quests = [
            quest
            for name in quest_names
            if (quest := self._quest_reference(name)) is not None
        ]
        progress = [
            self._progress(quest, perception_reference, context)
            for quest in quests
        ]
        self.last_quests = quests
        self.last_progress = progress
        return quests, progress

    def _quest_reference(self, name: str) -> QuestReference | None:
        entity = self.graph.find_by_name(name)
        if entity is None:
            return None
        requirements: list[str] = []
        rewards: list[str] = []
        related: list[str] = []
        for relation, target in self.graph.find_related(
            entity.knowledge_id
        ):
            related.append(target.name)
            if relation.relation_type is KnowledgeRelationType.REQUIRES:
                requirements.append(target.name)
            elif relation.relation_type is KnowledgeRelationType.REWARDS:
                rewards.append(target.name)
        return QuestReference(
            quest_id=entity.knowledge_id,
            quest_name=entity.name,
            quest_type=entity.attributes.get("quest_type", "QUEST"),
            description=entity.description,
            requirements=sorted(set(requirements)),
            rewards=sorted(set(rewards)),
            related_entities=sorted(set(related)),
            confidence=entity.confidence,
        )

    def _progress(
        self,
        quest: QuestReference,
        perception: MaplePerceptionReference | None,
        context: MapleCompanionContextReference | None,
    ) -> QuestProgressReference:
        visible = self._visible_names(perception, context)
        satisfied = [
            requirement
            for requirement in quest.requirements
            if self._requirement_satisfied(
                requirement,
                visible,
            )
        ]
        pending = [
            requirement
            for requirement in quest.requirements
            if requirement not in satisfied
        ]
        quest_location = self._quest_location(quest.quest_id)
        current_map = self._current_map(perception, context)
        ui_keys = set((perception.ui_state_reference or {}).keys()) if (
            perception is not None
        ) else set()
        reasoning: list[str] = []

        if "quest_completed" in ui_keys:
            state = QuestStateType.COMPLETED
        elif "quest_in_progress" in ui_keys:
            state = QuestStateType.IN_PROGRESS
            reasoning.append("UI 显示任务进行中")
        elif "quest_accepted" in ui_keys:
            state = QuestStateType.ACCEPTED
            reasoning.append("UI 显示任务已接受")
        elif (
            quest_location
            and current_map
            and quest_location != current_map
        ):
            state = QuestStateType.BLOCKED
            reasoning.append(
                f"任务 {quest.quest_name} 需要位于 {quest_location},"
                f"当前在 {current_map}"
            )
        elif pending:
            state = QuestStateType.REQUIREMENT_PENDING
            reasoning.append("待满足: " + ", ".join(pending))
        elif satisfied or "quest_available" in ui_keys:
            state = QuestStateType.AVAILABLE
            reasoning.append("所需实体已检测到")
        else:
            state = QuestStateType.UNKNOWN
            reasoning.append("缺乏足够信息推断任务状态")

        confidence = self._progress_confidence(state, satisfied, ui_keys)
        return QuestProgressReference(
            quest_id=quest.quest_id,
            quest_name=quest.quest_name,
            state=state,
            completed_requirements=sorted(satisfied),
            pending_requirements=sorted(pending),
            progress_confidence=confidence,
            reasoning=reasoning,
        )

    def _visible_names(
        self,
        perception: MaplePerceptionReference | None,
        context: MapleCompanionContextReference | None,
    ) -> set[str]:
        names: set[str] = set()
        if perception is not None:
            names.update(
                entity.name for entity in perception.visible_entities
            )
            if perception.visible_map:
                names.add(perception.visible_map)
        if context is not None and context.world_context is not None:
            if context.world_context.location:
                names.add(context.world_context.location)
            names.update(context.world_context.visible_entities)
        return names

    def _requirement_satisfied(
        self,
        requirement_name: str,
        visible: set[str],
    ) -> bool:
        if requirement_name in visible:
            return True
        requirement = self.graph.find_by_name(requirement_name)
        if requirement is None:
            return False
        return any(
            matched is requirement
            for name in visible
            if (matched := self.graph.find_by_name(name)) is not None
        )

    def _quest_location(self, quest_id: str) -> str:
        for relation, target in self.graph.find_related(quest_id):
            if (
                relation.relation_type is KnowledgeRelationType.LOCATED_IN
                and target.knowledge_type is MapleKnowledgeType.MAP
            ):
                return target.name
        return ""

    @staticmethod
    def _current_map(
        perception: MaplePerceptionReference | None,
        context: MapleCompanionContextReference | None,
    ) -> str:
        if perception is not None and perception.visible_map:
            return perception.visible_map
        if context is not None and context.world_context is not None:
            return context.world_context.location
        return ""

    @staticmethod
    def _progress_confidence(
        state: QuestStateType,
        satisfied: list[str],
        ui_keys: set[str],
    ) -> float:
        base = 0.4 + 0.2  # 任务已入库
        if satisfied:
            base += 0.2
        if ui_keys:
            base += 0.1
        if state is QuestStateType.BLOCKED:
            base -= 0.1
        if state is QuestStateType.UNKNOWN:
            base -= 0.1
        return round(min(0.95, max(0.0, base)), 4)
