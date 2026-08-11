"""MemoryConsolidator:分散记忆 -> 统一 MemoryNode[]。"""

from __future__ import annotations

from maple_agent.decision_reference.models import DecisionReference
from maple_agent.failure_intelligence.models import FailurePatternRecord
from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.human_alignment.preference import PreferenceMemory
from maple_agent.memory_graph.models import MemoryNode, MemoryType
from maple_agent.world_model.models import EnvironmentHistory


class MemoryConsolidator:
    """把既有记忆系统映射为统一记忆节点。"""

    def consolidate(
        self,
        *,
        experiences: list[GoalExperienceRecord] | None = None,
        failures: list[FailurePatternRecord] | None = None,
        world_history: EnvironmentHistory | None = None,
        decision_reference: DecisionReference | None = None,
        preferences: PreferenceMemory | None = None,
    ) -> list[MemoryNode]:
        nodes: list[MemoryNode] = []
        for experience in experiences or []:
            nodes.append(self._experience_node(experience))
        for failure in failures or []:
            nodes.append(self._failure_node(failure))
        if world_history is not None:
            nodes.extend(self._world_nodes(world_history))
        if decision_reference is not None:
            nodes.extend(self._decision_nodes(decision_reference))
        if preferences is not None:
            nodes.extend(self._preference_nodes(preferences))
        return nodes

    @staticmethod
    def _experience_node(
        experience: GoalExperienceRecord,
    ) -> MemoryNode:
        path = " -> ".join(experience.successful_path)
        return MemoryNode(
            memory_id=f"mem-exp-{experience.experience_id}",
            memory_type=MemoryType.EXPERIENCE,
            source="goal_memory",
            content=f"{experience.goal_description}: {path}",
            context={
                "goal": experience.goal_description,
                "success": experience.success,
            },
            confidence=experience.confidence,
            importance=0.7 if experience.success else 0.8,
        )

    @staticmethod
    def _failure_node(failure: FailurePatternRecord) -> MemoryNode:
        return MemoryNode(
            memory_id=f"mem-fail-{failure.pattern_id}",
            memory_type=MemoryType.FAILURE,
            source="failure_intelligence",
            content=f"{failure.failure_type}: {failure.root_cause}",
            context={
                "failure_type": failure.failure_type,
                "tasks": failure.affected_tasks,
            },
            confidence=failure.confidence,
            importance=0.9,
        )

    @staticmethod
    def _world_nodes(history: EnvironmentHistory) -> list[MemoryNode]:
        nodes: list[MemoryNode] = []
        for index, snapshot in enumerate(history.snapshots[-5:]):
            nodes.append(
                MemoryNode(
                    memory_id=(
                        f"mem-world-{history.history_id}-{index}"
                    ),
                    memory_type=MemoryType.WORLD,
                    source="world_model",
                    content=(
                        f"location={snapshot.location}, "
                        f"entities={snapshot.visible_entities}"
                    ),
                    context={
                        "location": snapshot.location,
                        "history": history.history_id,
                    },
                    confidence=snapshot.confidence,
                    importance=0.5,
                )
            )
        return nodes

    @staticmethod
    def _decision_nodes(
        decision_reference: DecisionReference,
    ) -> list[MemoryNode]:
        nodes: list[MemoryNode] = []
        for option in decision_reference.recommended_options:
            nodes.append(
                MemoryNode(
                    memory_id=f"mem-dec-{option.option_id}",
                    memory_type=MemoryType.DECISION,
                    source="decision_reference",
                    content=(
                        f"{option.action} -> {option.target}: "
                        f"{option.reason}"
                    ),
                    context={
                        "action": option.action,
                        "recommendation": option.recommendation,
                    },
                    confidence=option.confidence,
                    importance=0.6,
                )
            )
        return nodes

    @staticmethod
    def _preference_nodes(
        preferences: PreferenceMemory,
    ) -> list[MemoryNode]:
        nodes: list[MemoryNode] = []
        for record in preferences.history():
            nodes.append(
                MemoryNode(
                    memory_id=f"mem-pref-{record.record_id}",
                    memory_type=MemoryType.PREFERENCE,
                    source="human_alignment",
                    content=(
                        f"{record.action} option {record.option_id}: "
                        f"{record.reason}"
                    ),
                    context={
                        "option_id": record.option_id,
                        "action": record.action,
                    },
                    confidence=0.9,
                    importance=0.8,
                )
            )
        return nodes
