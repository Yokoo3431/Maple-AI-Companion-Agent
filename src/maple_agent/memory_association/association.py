"""SemanticAssociationEngine:记忆节点 -> 语义关联网络(只读)。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.memory_association.builder import SemanticRelationBuilder
from maple_agent.memory_association.models import (
    SemanticMemoryRelation,
    SemanticRelationType,
)
from maple_agent.memory_graph.models import MemoryNode, MemoryType


class SemanticAssociationEngine:
    """按语义规则关联记忆节点。"""

    def __init__(
        self,
        *,
        relation_builder: SemanticRelationBuilder | None = None,
    ) -> None:
        self.relation_builder = relation_builder or SemanticRelationBuilder()
        self.last_relations: list[SemanticMemoryRelation] = []

    def associate(
        self,
        nodes: list[MemoryNode],
    ) -> list[SemanticMemoryRelation]:
        relations: list[SemanticMemoryRelation] = []
        experiences = [
            node for node in nodes if node.memory_type is MemoryType.EXPERIENCE
        ]
        failures = [
            node for node in nodes if node.memory_type is MemoryType.FAILURE
        ]
        decisions = [
            node for node in nodes if node.memory_type is MemoryType.DECISION
        ]
        preferences = [
            node for node in nodes if node.memory_type is MemoryType.PREFERENCE
        ]
        worlds = [
            node for node in nodes if node.memory_type is MemoryType.WORLD
        ]
        for index, left in enumerate(experiences):
            for right in experiences[index + 1 :]:
                if self._same_goal(left, right):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=(
                                SemanticRelationType.GOAL_SIMILARITY
                            ),
                            source=left,
                            target=right,
                            confidence=0.8,
                            reasoning="相似目标经验",
                        )
                    )
        for failure in failures:
            for experience in experiences:
                if self._shared_task(failure, experience):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=(
                                SemanticRelationType.FAILURE_PATTERN
                            ),
                            source=failure,
                            target=experience,
                            confidence=0.85,
                            reasoning="失败任务与历史经验关联",
                        )
                    )
                if (
                    experience.context.get("success") is True
                    and self._same_goal(failure, experience)
                ):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=(
                                SemanticRelationType.SUCCESS_PATTERN
                            ),
                            source=experience,
                            target=failure,
                            confidence=0.75,
                            reasoning="成功经验可修复同目标失败",
                        )
                    )
        for decision in decisions:
            for preference in preferences:
                if self._action_match(decision, preference):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=(
                                SemanticRelationType.PREFERENCE_ALIGNMENT
                            ),
                            source=decision,
                            target=preference,
                            confidence=0.9,
                            reasoning="决策与用户偏好对齐",
                        )
                    )
            for failure in failures:
                if self._action_in_failure(decision, failure):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=(
                                SemanticRelationType.DECISION_IMPROVEMENT
                            ),
                            source=decision,
                            target=failure,
                            confidence=0.7,
                            reasoning="决策需规避历史失败",
                        )
                    )
        for world in worlds:
            for node in nodes:
                if node.memory_type is MemoryType.WORLD:
                    continue
                if self._location_match(world, node):
                    relations.append(
                        self.relation_builder.build(
                            relation_type=SemanticRelationType.WORLD_CONTEXT,
                            source=world,
                            target=node,
                            confidence=0.8,
                            reasoning="世界上下文关联",
                        )
                    )
        self.last_relations = relations
        return relations

    @staticmethod
    def _same_goal(left: MemoryNode, right: MemoryNode) -> bool:
        left_goal = left.context.get("goal")
        right_goal = right.context.get("goal")
        return bool(left_goal) and left_goal == right_goal

    @staticmethod
    def _shared_task(
        failure: MemoryNode,
        experience: MemoryNode,
    ) -> bool:
        tasks = failure.context.get("tasks") or []
        return any(str(task) in experience.content for task in tasks)

    @staticmethod
    def _action_match(
        decision: MemoryNode,
        preference: MemoryNode,
    ) -> bool:
        decision_action = decision.context.get("action")
        preference_action = preference.context.get("action")
        if decision_action and decision_action == preference_action:
            return True
        option_id = preference.context.get("option_id")
        return bool(option_id) and option_id in decision.memory_id

    @staticmethod
    def _action_in_failure(
        decision: MemoryNode,
        failure: MemoryNode,
    ) -> bool:
        decision_action = decision.context.get("action")
        if not decision_action:
            return False
        return decision_action.lower() in failure.content.lower()

    @staticmethod
    def _location_match(world: MemoryNode, node: MemoryNode) -> bool:
        location = world.context.get("location")
        if not location:
            return False
        node_context = str(node.context)
        return location in node.content or location in node_context

    def score(
        self,
        relation: SemanticMemoryRelation,
        *,
        source: MemoryNode,
        target: MemoryNode,
    ) -> float:
        """AssociationScore = 0.35*Context + 0.25*Confidence + 0.20*Importance + 0.20*Recency。"""
        context_match = self._context_match(source, target)
        importance = max(source.importance, target.importance)
        recency = self._recency(source, target)
        score = round(
            0.35 * context_match
            + 0.25 * relation.confidence
            + 0.20 * importance
            + 0.20 * recency,
            4,
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def _context_match(source: MemoryNode, target: MemoryNode) -> float:
        shared = set(source.context) & set(target.context)
        if not shared:
            return 0.0
        hits = sum(
            1
            for key in shared
            if source.context[key] == target.context[key]
        )
        return round(hits / max(1, len(source.context)), 4)

    @staticmethod
    def _recency(source: MemoryNode, target: MemoryNode) -> float:
        latest = max(source.timestamp, target.timestamp)
        age_hours = (
            datetime.now(UTC) - latest
        ).total_seconds() / 3600
        return round(
            max(0.0, min(1.0, 1.0 - age_hours / 72)),
            4,
        )


def save_semantic_memory_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    relations: list[SemanticMemoryRelation],
    summary: dict,
    validation: str,
) -> None:
    """写入 semantic_memory_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "relations": [
            relation.model_dump(mode="json") for relation in relations
        ],
        "summary": summary,
        "validation": validation,
    }
    (directory / "semantic_memory_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
