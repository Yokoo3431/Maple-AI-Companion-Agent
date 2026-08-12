"""GoalDependencyBuilder:任务依赖图(仅图信息,无动作链)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import (
    KnowledgeRelationType,
    MapleKnowledgeType,
)
from maple_agent.quest_reasoning.models import (
    GoalDependency,
    QuestProgressReference,
)


class GoalDependencyBuilder:
    """构建 Quest -> NPC/Item -> Location 依赖关系图。"""

    def __init__(self, graph: MapleKnowledgeGraph) -> None:
        self.graph = graph
        self.last_dependencies: list[GoalDependency] = []

    def build(
        self,
        progress: list[QuestProgressReference],
    ) -> list[GoalDependency]:
        dependencies: list[GoalDependency] = []
        for item in progress:
            quest = self.graph.find_by_name(item.quest_name)
            if quest is None:
                continue
            for relation, target in self.graph.find_related(
                quest.knowledge_id
            ):
                if relation.relation_type not in (
                    KnowledgeRelationType.REQUIRES,
                    KnowledgeRelationType.LOCATED_IN,
                ):
                    continue
                dependency = GoalDependency(
                    dependency_id=new_id(),
                    goal_id=f"quest:{item.quest_name}",
                    depends_on=(
                        f"{target.knowledge_type.value.lower()}:"
                        f"{target.name}"
                    ),
                    dependency_type=target.knowledge_type.value,
                    confidence=relation.confidence,
                    reasoning=(
                        f"任务 {item.quest_name} 依赖 {target.name}"
                    ),
                )
                if not self._exists(dependencies, dependency):
                    dependencies.append(dependency)
                if target.knowledge_type is MapleKnowledgeType.NPC:
                    self._append_npc_location(dependencies, target.name)
        self.last_dependencies = dependencies
        return dependencies

    def _append_npc_location(
        self,
        dependencies: list[GoalDependency],
        npc_name: str,
    ) -> None:
        npc = self.graph.find_by_name(npc_name)
        if npc is None:
            return
        for relation, target in self.graph.find_related(
            npc.knowledge_id
        ):
            if relation.relation_type is not KnowledgeRelationType.LOCATED_IN:
                continue
            dependency = GoalDependency(
                dependency_id=new_id(),
                goal_id=f"npc:{npc_name}",
                depends_on=f"map:{target.name}",
                dependency_type="LOCATION",
                confidence=relation.confidence,
                reasoning=f"{npc_name} 位于 {target.name}",
            )
            if not self._exists(dependencies, dependency):
                dependencies.append(dependency)

    @staticmethod
    def _exists(
        dependencies: list[GoalDependency],
        candidate: GoalDependency,
    ) -> bool:
        return any(
            dependency.goal_id == candidate.goal_id
            and dependency.depends_on == candidate.depends_on
            for dependency in dependencies
        )
