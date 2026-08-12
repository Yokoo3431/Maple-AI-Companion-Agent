"""QuestPlanner:任务智能编排,输出 QuestGoalReference(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.quest_reasoning.dependency import GoalDependencyBuilder
from maple_agent.quest_reasoning.goal_reasoner import GoalReasoner
from maple_agent.quest_reasoning.models import (
    GoalDependency,
    GoalReference,
    QuestGoalReference,
    QuestProgressReference,
    QuestReference,
)
from maple_agent.quest_reasoning.quest_state import QuestStateAnalyzer


class QuestPlanner:
    """编排状态分析 / 目标推理 / 依赖图,输出统一任务智能参考。"""

    def __init__(
        self,
        graph: MapleKnowledgeGraph,
        *,
        analyzer: QuestStateAnalyzer | None = None,
        reasoner: GoalReasoner | None = None,
        dependency_builder: GoalDependencyBuilder | None = None,
    ) -> None:
        self.graph = graph
        self.analyzer = analyzer or QuestStateAnalyzer(graph)
        self.reasoner = reasoner or GoalReasoner()
        self.dependency_builder = (
            dependency_builder or GoalDependencyBuilder(graph)
        )
        self.last_reference: QuestGoalReference | None = None

    def plan(
        self,
        *,
        context: MapleCompanionContextReference | None = None,
        knowledge_reference: MapleKnowledgeReference | None = None,
        perception_reference: MaplePerceptionReference | None = None,
    ) -> QuestGoalReference:
        quests, progress = self.analyzer.analyze(
            context=context,
            knowledge_reference=knowledge_reference,
            perception_reference=perception_reference,
        )
        recommended, blocked = self.reasoner.reason(progress)
        dependencies = self.dependency_builder.build(progress)
        all_goals = recommended + blocked
        confidence = (
            round(
                sum(goal.confidence for goal in all_goals)
                / len(all_goals),
                4,
            )
            if all_goals
            else 0.0
        )
        reasoning = [
            f"任务数量: {len(quests)}",
            f"推荐目标: {len(recommended)}",
        ]
        if blocked:
            reasoning.append(f"受阻目标: {len(blocked)}")
        reference = QuestGoalReference(
            active_quests=quests,
            quest_progress=progress,
            recommended_goals=recommended,
            blocked_goals=blocked,
            dependencies=dependencies,
            confidence=confidence,
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference


def save_quest_reasoning_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    quests: list[QuestReference],
    progress: list[QuestProgressReference],
    goals: list[GoalReference],
    dependencies: list[GoalDependency],
    validation: str,
) -> None:
    """写入 quest_reasoning_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "quests": [quest.model_dump(mode="json") for quest in quests],
        "progress": [
            item.model_dump(mode="json") for item in progress
        ],
        "goals": [goal.model_dump(mode="json") for goal in goals],
        "dependencies": [
            dependency.model_dump(mode="json")
            for dependency in dependencies
        ],
        "validation": validation,
    }
    (directory / "quest_reasoning_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
