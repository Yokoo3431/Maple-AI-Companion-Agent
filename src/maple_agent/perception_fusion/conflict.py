"""ConflictDetector:多源冲突检测(确定性规则)。"""

from __future__ import annotations

from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.quest_reasoning.models import (
    QuestGoalReference,
    QuestStateType,
)


class ConflictDetector:
    """检测 未知地图/实体不匹配/任务不匹配/知识缺失。"""

    def detect(
        self,
        *,
        perception: MaplePerceptionReference | None = None,
        knowledge: MapleKnowledgeReference | None = None,
        context: MapleCompanionContextReference | None = None,
        quest: QuestGoalReference | None = None,
        memory: RelevantMemoryReference | None = None,
        semantic: SemanticMemoryReference | None = None,
    ) -> list[str]:
        conflicts: list[str] = []
        if knowledge is None or (
            knowledge.confidence == 0
            and not (
                knowledge.related_maps
                or knowledge.related_npcs
                or knowledge.related_monsters
                or knowledge.related_items
                or knowledge.related_quests
            )
        ):
            conflicts.append("knowledge missing")
        if (
            perception is not None
            and perception.visible_map
            and knowledge is not None
            and knowledge.related_maps
            and perception.visible_map not in knowledge.related_maps
        ):
            conflicts.append(f"unknown map: {perception.visible_map}")
        if perception is not None and knowledge is not None:
            known = set(
                knowledge.related_npcs
                + knowledge.related_monsters
                + knowledge.related_items
            )
            for entity in perception.visible_entities:
                if known and entity.name not in known:
                    conflicts.append(f"entity mismatch: {entity.name}")
        if quest is not None:
            for item in quest.quest_progress:
                if item.state in (
                    QuestStateType.BLOCKED,
                    QuestStateType.UNKNOWN,
                ):
                    conflicts.append(
                        f"quest mismatch: {item.quest_name} "
                        f"state={item.state.value}"
                    )
        return list(dict.fromkeys(conflicts))
