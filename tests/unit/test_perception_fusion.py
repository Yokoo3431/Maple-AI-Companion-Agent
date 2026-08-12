"""Perception Fusion 单测:融合构建/置信度公式/一致性/冲突/缺失信号/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.maple_context.models import (
    MapleCompanionContextReference,
    MapleWorldContext,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    MapleKnowledgeRetriever,
    load_demo_knowledge,
)
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import (
    MemoryNode,
    MemoryType,
    RelevantMemoryReference,
)
from maple_agent.perception import MaplePerceptionBinder, MockVisionProvider
from maple_agent.perception.models import (
    MaplePerceptionReference,
    PerceivedEntity,
    PerceivedEntityType,
)
from maple_agent.perception_fusion import (
    ConflictDetector,
    PerceptionFusionEngine,
    PerceptionFusionReference,
    PerceptionFusionValidator,
    PerceptionFusionVerdict,
    save_perception_fusion_trace,
)
from maple_agent.quest_reasoning import (
    QuestPlanner,
    QuestProgressReference,
    QuestStateType,
)
from maple_agent.quest_reasoning.models import QuestGoalReference
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_demo_knowledge()
    graph = MapleKnowledgeGraph()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph


def _context(
    location: str = "射手村",
    visible: tuple[str, ...] = ("赫丽娜",),
) -> MapleCompanionContextReference:
    return MapleCompanionContextReference(
        world_context=MapleWorldContext(
            location=location,
            visible_entities=list(visible),
            confidence=0.9,
        ),
        confidence=0.9,
        trace_id="trace-fusion",
    )


def _knowledge_ref(
    graph: MapleKnowledgeGraph,
    context: MapleCompanionContextReference,
) -> MapleKnowledgeReference:
    return MapleKnowledgeRetriever(graph).retrieve(context=context)


def _perception_ref(
    graph: MapleKnowledgeGraph,
    *,
    location: str = "射手村",
    visible: tuple[str, ...] = ("赫丽娜",),
) -> MaplePerceptionReference:
    observation = MockVisionProvider(
        location=location,
        visible_entities=list(visible),
        ui_state="quest_available",
        confidence=0.9,
    ).capture()
    return MaplePerceptionBinder(knowledge=graph).bind(observation)


def _quest_ref(
    graph: MapleKnowledgeGraph,
    context: MapleCompanionContextReference,
    perception: MaplePerceptionReference,
) -> QuestGoalReference:
    return QuestPlanner(graph).plan(
        context=context,
        knowledge_reference=_knowledge_ref(graph, context),
        perception_reference=perception,
    )


def _memory() -> RelevantMemoryReference:
    return RelevantMemoryReference(
        relevant_memories=[
            MemoryNode(
                memory_id="m1",
                memory_type=MemoryType.EXPERIENCE,
                content="成功与赫丽娜交互",
                context={"map": "射手村"},
                confidence=0.85,
                importance=0.8,
            )
        ],
        confidence=0.8,
        reasoning=["相关记忆"],
    )


def _semantic() -> SemanticMemoryReference:
    return SemanticMemoryReference(
        related_experiences=["exp-1"],
        preference_alignment=["NPC_INTERACTION"],
        confidence=0.75,
    )


def _human_alignment() -> HumanAlignedDecisionReference:
    return HumanAlignedDecisionReference(
        alignment_score=0.8,
        reasoning=["用户偏好 NPC 交互"],
    )


def _fuse(graph: MapleKnowledgeGraph) -> PerceptionFusionReference:
    context = _context()
    perception = _perception_ref(graph)
    return PerceptionFusionEngine().fuse(
        perception_reference=perception,
        knowledge_reference=_knowledge_ref(graph, context),
        context_reference=context,
        quest_goal_reference=_quest_ref(graph, context, perception),
        memory_reference=_memory(),
        semantic_memory_reference=_semantic(),
        human_alignment_reference=_human_alignment(),
    )


def test_fusion_creation():
    graph = _graph()
    fusion = _fuse(graph)
    assert fusion.fusion_id
    assert len(fusion.source_inputs) == 7
    sources = {source.source for source in fusion.source_inputs}
    assert sources == {
        "perception",
        "knowledge",
        "world_context",
        "quest_reasoning",
        "memory",
        "semantic_memory",
        "human_alignment",
    }
    assert fusion.external_source_reference == []
    assert fusion.reasoning


def test_confidence_formula():
    graph = _graph()
    engine = PerceptionFusionEngine()
    context = _context()
    perception = _perception_ref(graph)
    knowledge = _knowledge_ref(graph, context)
    quest = _quest_ref(graph, context, perception)
    memory = _memory()
    semantic = _semantic()
    fusion = engine.fuse(
        perception_reference=perception,
        knowledge_reference=knowledge,
        context_reference=context,
        quest_goal_reference=quest,
        memory_reference=memory,
        semantic_memory_reference=semantic,
    )
    consistency = engine.consistency_scorer.score(
        perception=perception,
        knowledge=knowledge,
        context=context,
        quest=quest,
        memory=memory,
        semantic=semantic,
    )
    expected = round(
        min(
            1.0,
            0.30 * perception.confidence
            + 0.20 * knowledge.confidence
            + 0.20 * consistency
            + 0.20 * quest.confidence
            + 0.10 * memory.confidence,
        ),
        4,
    )
    assert fusion.fused_confidence == expected
    assert 0 <= fusion.fused_confidence <= 1


def test_consistency_scoring():
    graph = _graph()
    fusion = _fuse(graph)
    assert fusion.consistency_score >= 0.8
    mismatched = _perception_ref(graph, location="魔法密林", visible=("爱丽丝",))
    context = _context(location="魔法密林", visible=("爱丽丝",))
    knowledge = MapleKnowledgeReference(
        related_maps=["射手村"],
        related_npcs=["赫丽娜"],
        confidence=0.8,
    )
    engine = PerceptionFusionEngine()
    score = engine.consistency_scorer.score(
        perception=mismatched,
        knowledge=knowledge,
        context=context,
    )
    assert score < fusion.consistency_score


def test_conflict_detection():
    detector = ConflictDetector()
    conflicts = detector.detect(
        perception=MaplePerceptionReference(
            observation_id="obs-conflict",
            visible_map="未知地图",
            visible_entities=[
                PerceivedEntity(
                    entity_id="e1",
                    entity_type=PerceivedEntityType.NPC,
                    name="未知NPC",
                    confidence=0.8,
                )
            ],
            confidence=0.8,
        ),
        knowledge=MapleKnowledgeReference(
            related_maps=["射手村"],
            related_npcs=["赫丽娜"],
            confidence=0.8,
        ),
        quest=QuestGoalReference(
            quest_progress=[
                QuestProgressReference(
                    quest_id="q1",
                    quest_name="新手任务",
                    state=QuestStateType.BLOCKED,
                    progress_confidence=0.6,
                )
            ],
            confidence=0.6,
        ),
    )
    assert any("unknown map" in item for item in conflicts)
    assert any("entity mismatch" in item for item in conflicts)
    assert any("quest mismatch" in item for item in conflicts)


def test_conflict_knowledge_missing():
    detector = ConflictDetector()
    conflicts = detector.detect(
        perception=MaplePerceptionReference(
            observation_id="obs",
            visible_map="射手村",
            confidence=0.8,
        ),
        knowledge=MapleKnowledgeReference(confidence=0.0),
    )
    assert "knowledge missing" in conflicts


def test_missing_signals():
    graph = _graph()
    perception = _perception_ref(graph)
    fusion = PerceptionFusionEngine().fuse(
        perception_reference=perception,
        context_reference=_context(),
        quest_goal_reference=QuestGoalReference(confidence=0.0),
    )
    assert "knowledge missing" in fusion.missing_signals
    assert "quest reasoning missing" in fusion.missing_signals
    assert "memory missing" in fusion.missing_signals
    assert fusion.fused_confidence < 0.8


def test_validator_valid():
    graph = _graph()
    fusion = _fuse(graph)
    result = PerceptionFusionValidator().validate(fusion)
    assert result.verdict is PerceptionFusionVerdict.VALID
    assert result.issues == []
    assert fusion.fused_confidence >= 0.8
    assert fusion.consistency_score >= 0.8
    assert fusion.conflicts == []


def test_validator_warning():
    graph = _graph()
    perception = _perception_ref(graph)
    fusion = PerceptionFusionEngine().fuse(
        perception_reference=perception,
        context_reference=_context(),
        quest_goal_reference=QuestGoalReference(confidence=0.0),
    )
    result = PerceptionFusionValidator().validate(fusion)
    assert result.verdict is PerceptionFusionVerdict.WARNING
    assert result.issues


def test_validator_blocked():
    reference = PerceptionFusionReference(fusion_id="")
    result = PerceptionFusionValidator().validate(reference)
    assert result.verdict is PerceptionFusionVerdict.BLOCKED
    assert "missing fusion id" in result.issues


def test_replay_generation(tmp_path):
    graph = _graph()
    fusion = _fuse(graph)
    sources = {
        source.source: source.confidence for source in fusion.source_inputs
    }
    save_perception_fusion_trace(
        tmp_path,
        "trace-replay",
        sources=sources,
        fusion=fusion,
        conflicts=fusion.conflicts,
        validation="VALID",
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "perception_fusion_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["sources"]["perception"] > 0
    assert replay["fusion"]["fused_confidence"] >= 0.8
    assert replay["fusion"]["consistency_score"] >= 0.8
    assert replay["conflicts"] == []
    assert replay["validation"] == "VALID"


def test_context_integration():
    graph = _graph()
    fusion = _fuse(graph)
    context = AgentLoopContext(
        trace_id="trace-fusion",
        status=AgentLoopStatus.COMPLETED,
        perception_fusion_reference=fusion,
    )
    assert context.perception_fusion_reference is not None
    assert context.perception_fusion_reference.fused_confidence >= 0.8


def test_webui_perception_fusion_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph = _graph()
    fusion = _fuse(graph)
    payload = {
        "fusion_id": fusion.fusion_id,
        "source_inputs": [
            source.model_dump(mode="json") for source in fusion.source_inputs
        ],
        "fused_confidence": fusion.fused_confidence,
        "consistency_score": fusion.consistency_score,
        "conflicts": fusion.conflicts,
        "missing_signals": fusion.missing_signals,
        "focus_reference": fusion.focus_reference,
        "reasoning": fusion.reasoning,
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, perception_fusion=payload)
    with TestClient(app) as client:
        resp = client.get("/api/perception-fusion/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["fused_confidence"] >= 0.8
    assert data["consistency_score"] >= 0.8
    assert data["conflicts"] == []
    assert data["validation"] == "VALID"


def test_webui_perception_fusion_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/perception-fusion/state")
    assert resp.json()["enabled"] is False
