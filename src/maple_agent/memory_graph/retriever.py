"""MemoryRetriever:相关记忆检索(只读,确定性评分,无 LLM)。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.decision_reference.models import DecisionReference
from maple_agent.environment.models import EnvironmentState
from maple_agent.memory_graph.index import MemoryIndex
from maple_agent.memory_graph.models import (
    MemoryNode,
    MemoryRelation,
    MemoryType,
    RelevantMemoryReference,
)
from maple_agent.task_planning.models import LongHorizonGoal


class MemoryRetriever:
    """按当前目标/环境/决策参考检索相关记忆。"""

    def __init__(self, index: MemoryIndex) -> None:
        self.index = index
        self.last_reference: RelevantMemoryReference | None = None

    def retrieve(
        self,
        *,
        current_goal: LongHorizonGoal | None = None,
        environment_state: EnvironmentState | None = None,
        decision_reference: DecisionReference | None = None,
        limit: int = 5,
    ) -> RelevantMemoryReference:
        query_context = self._query_context(
            current_goal,
            environment_state,
            decision_reference,
        )
        scored = [
            (self._score(node, query_context), node)
            for node in self.index.all()
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        relevant = [node for _, node in scored[:limit]]
        reference = RelevantMemoryReference(
            relevant_memories=relevant,
            similar_experiences=self._by_type(
                relevant,
                MemoryType.EXPERIENCE,
            ),
            related_failures=self._by_type(relevant, MemoryType.FAILURE),
            environment_history=self._by_type(relevant, MemoryType.WORLD),
            preference_hints=self._by_type(
                relevant,
                MemoryType.PREFERENCE,
            ),
            confidence=self._confidence(scored, limit),
            reasoning=[
                f"{node.memory_id} score={score:.2f}"
                for score, node in scored[:limit]
            ],
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _by_type(
        nodes: list[MemoryNode],
        memory_type: MemoryType,
    ) -> list[MemoryNode]:
        return [
            node for node in nodes if node.memory_type is memory_type
        ]

    @staticmethod
    def _score(node: MemoryNode, query_context: dict) -> float:
        context_similarity = MemoryRetriever._context_similarity(
            node.context,
            query_context,
        )
        recency = MemoryRetriever._recency(node.timestamp)
        score = round(
            0.3 * context_similarity
            + 0.25 * node.importance
            + 0.25 * node.confidence
            + 0.2 * recency,
            4,
        )
        return max(0.0, min(1.0, score))

    @staticmethod
    def _context_similarity(
        node_context: dict,
        query_context: dict,
    ) -> float:
        if not node_context or not query_context:
            return 0.0
        shared = set(node_context) & set(query_context)
        if not shared:
            return 0.0
        hits = sum(
            1
            for key in shared
            if node_context[key] == query_context[key]
        )
        return round(hits / len(query_context), 4)

    @staticmethod
    def _recency(timestamp: datetime) -> float:
        age_hours = (
            datetime.now(UTC) - timestamp
        ).total_seconds() / 3600
        return round(
            max(0.0, min(1.0, 1.0 - age_hours / 72)),
            4,
        )

    @staticmethod
    def _query_context(
        current_goal: LongHorizonGoal | None,
        environment_state: EnvironmentState | None,
        decision_reference: DecisionReference | None,
    ) -> dict:
        context: dict = {}
        if current_goal is not None:
            context["goal"] = current_goal.description
        if (
            environment_state is not None
            and environment_state.location
        ):
            context["location"] = environment_state.location
        if decision_reference is not None:
            for option in decision_reference.recommended_options:
                context.setdefault("action", option.action)
        return context

    @staticmethod
    def _confidence(
        scored: list[tuple[float, MemoryNode]],
        limit: int,
    ) -> float:
        top = [score for score, _ in scored[:limit]]
        if not top:
            return 0.0
        return round(sum(top) / len(top), 4)


def save_memory_graph_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    memory_nodes: list[MemoryNode],
    relations: list[MemoryRelation],
    retrieval: RelevantMemoryReference,
    validation: str,
) -> None:
    """写入 memory_graph_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "memory_nodes": [
            node.model_dump(mode="json") for node in memory_nodes
        ],
        "relations": [
            relation.model_dump(mode="json") for relation in relations
        ],
        "retrieval": retrieval.model_dump(mode="json"),
        "validation": validation,
    }
    (directory / "memory_graph_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
