"""PerceptionFusionEngine:多源只读参考融合(确定性,无 LLM)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.logging_setup import new_id
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.perception_fusion.conflict import ConflictDetector
from maple_agent.perception_fusion.consistency import ConsistencyScorer
from maple_agent.perception_fusion.models import (
    FusionSourceInput,
    PerceptionFusionReference,
)
from maple_agent.quest_reasoning.models import QuestGoalReference


class PerceptionFusionEngine:
    """消费既有只读参考,输出统一感知融合参考。"""

    def __init__(
        self,
        *,
        consistency_scorer: ConsistencyScorer | None = None,
        conflict_detector: ConflictDetector | None = None,
    ) -> None:
        self.consistency_scorer = consistency_scorer or ConsistencyScorer()
        self.conflict_detector = conflict_detector or ConflictDetector()
        self.last_reference: PerceptionFusionReference | None = None

    def fuse(
        self,
        *,
        perception_reference: MaplePerceptionReference | None = None,
        knowledge_reference: MapleKnowledgeReference | None = None,
        context_reference: MapleCompanionContextReference | None = None,
        quest_goal_reference: QuestGoalReference | None = None,
        memory_reference: RelevantMemoryReference | None = None,
        semantic_memory_reference: SemanticMemoryReference | None = None,
        human_alignment_reference: HumanAlignedDecisionReference | None = None,
    ) -> PerceptionFusionReference:
        sources = self._sources(
            perception=perception_reference,
            knowledge=knowledge_reference,
            context=context_reference,
            quest=quest_goal_reference,
            memory=memory_reference,
            semantic=semantic_memory_reference,
            human_alignment=human_alignment_reference,
        )
        consistency = self.consistency_scorer.score(
            perception=perception_reference,
            knowledge=knowledge_reference,
            context=context_reference,
            quest=quest_goal_reference,
            memory=memory_reference,
            semantic=semantic_memory_reference,
            human_alignment=human_alignment_reference,
        )
        conflicts = self.conflict_detector.detect(
            perception=perception_reference,
            knowledge=knowledge_reference,
            context=context_reference,
            quest=quest_goal_reference,
            memory=memory_reference,
            semantic=semantic_memory_reference,
        )
        missing = self._missing_signals(
            perception=perception_reference,
            knowledge=knowledge_reference,
            context=context_reference,
            quest=quest_goal_reference,
            memory=memory_reference,
            semantic=semantic_memory_reference,
        )
        perception_conf = (
            perception_reference.confidence
            if perception_reference is not None
            else 0.0
        )
        knowledge_conf = (
            knowledge_reference.confidence
            if knowledge_reference is not None
            else 0.0
        )
        quest_conf = (
            quest_goal_reference.confidence
            if quest_goal_reference is not None
            else 0.0
        )
        memory_conf = self._memory_confidence(
            memory_reference,
            semantic_memory_reference,
        )
        fused = round(
            min(
                1.0,
                max(
                    0.0,
                    0.30 * perception_conf
                    + 0.20 * knowledge_conf
                    + 0.20 * consistency
                    + 0.20 * quest_conf
                    + 0.10 * memory_conf,
                ),
            ),
            4,
        )
        focus = self._focus(quest_goal_reference)
        reasoning = [
            f"来源数量: {len(sources)}",
            f"一致性: {consistency}",
            f"冲突: {len(conflicts)}",
        ]
        if missing:
            reasoning.append("缺失信号: " + ", ".join(missing))
        reference = PerceptionFusionReference(
            fusion_id=new_id(),
            source_inputs=sources,
            fused_confidence=fused,
            consistency_score=consistency,
            conflicts=conflicts,
            missing_signals=missing,
            focus_reference=focus,
            reasoning=reasoning,
            external_source_reference=[],
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _sources(
        *,
        perception: MaplePerceptionReference | None = None,
        knowledge: MapleKnowledgeReference | None = None,
        context: MapleCompanionContextReference | None = None,
        quest: QuestGoalReference | None = None,
        memory: RelevantMemoryReference | None = None,
        semantic: SemanticMemoryReference | None = None,
        human_alignment: HumanAlignedDecisionReference | None = None,
    ) -> list[FusionSourceInput]:
        sources: list[FusionSourceInput] = []
        if perception is not None:
            sources.append(
                FusionSourceInput(
                    source="perception",
                    confidence=perception.confidence,
                    summary=(
                        f"地图={perception.visible_map},"
                        f"实体={len(perception.visible_entities)}"
                    ),
                )
            )
        if knowledge is not None:
            sources.append(
                FusionSourceInput(
                    source="knowledge",
                    confidence=knowledge.confidence,
                    summary=f"任务={knowledge.related_quests}",
                )
            )
        if context is not None:
            location = (
                context.world_context.location
                if context.world_context is not None
                else ""
            )
            sources.append(
                FusionSourceInput(
                    source="world_context",
                    confidence=context.confidence,
                    summary=f"位置={location}",
                )
            )
        if quest is not None:
            sources.append(
                FusionSourceInput(
                    source="quest_reasoning",
                    confidence=quest.confidence,
                    summary=(
                        "任务="
                        + ", ".join(
                            item.quest_name for item in quest.active_quests
                        )
                    ),
                )
            )
        if memory is not None:
            sources.append(
                FusionSourceInput(
                    source="memory",
                    confidence=memory.confidence,
                    summary=(
                        f"相关记忆={len(memory.relevant_memories)}"
                    ),
                )
            )
        if semantic is not None:
            sources.append(
                FusionSourceInput(
                    source="semantic_memory",
                    confidence=semantic.confidence,
                    summary=(
                        f"经验={len(semantic.related_experiences)}"
                    ),
                )
            )
        if human_alignment is not None:
            sources.append(
                FusionSourceInput(
                    source="human_alignment",
                    confidence=human_alignment.alignment_score,
                    summary=(
                        f"偏好={len(human_alignment.preferred_options)}"
                    ),
                )
            )
        return sources

    @staticmethod
    def _missing_signals(
        *,
        perception: MaplePerceptionReference | None = None,
        knowledge: MapleKnowledgeReference | None = None,
        context: MapleCompanionContextReference | None = None,
        quest: QuestGoalReference | None = None,
        memory: RelevantMemoryReference | None = None,
        semantic: SemanticMemoryReference | None = None,
    ) -> list[str]:
        missing: list[str] = []
        if perception is None:
            missing.append("perception missing")
        if knowledge is None:
            missing.append("knowledge missing")
        if context is None:
            missing.append("world context missing")
        if quest is None or not quest.active_quests:
            missing.append("quest reasoning missing")
        if memory is None and semantic is None:
            missing.append("memory missing")
        return missing

    @staticmethod
    def _memory_confidence(
        memory: RelevantMemoryReference | None,
        semantic: SemanticMemoryReference | None,
    ) -> float:
        values: list[float] = []
        if memory is not None:
            values.append(memory.confidence)
        if semantic is not None:
            values.append(semantic.confidence)
        return round(max(values), 4) if values else 0.0

    @staticmethod
    def _focus(
        quest: QuestGoalReference | None,
    ) -> str:
        if quest is not None and quest.recommended_goals:
            goal = quest.recommended_goals[0]
            return f"{goal.goal_type.value}: {goal.description}"
        return "待补充感知信息"


def save_perception_fusion_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    sources: dict,
    fusion: PerceptionFusionReference,
    conflicts: list[str],
    validation: str,
) -> None:
    """写入 perception_fusion_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "sources": sources,
        "fusion": fusion.model_dump(mode="json"),
        "conflicts": conflicts,
        "validation": validation,
    }
    (directory / "perception_fusion_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
