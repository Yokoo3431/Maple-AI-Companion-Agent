"""Semantic Memory Association 单测:关系 / 关联 / 评分 / 校验 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.memory_association import (
    AssociationReasoner,
    SemanticAssociationEngine,
    SemanticAssociationValidator,
    SemanticMemoryVerdict,
    SemanticRelationType,
    save_semantic_memory_trace,
)
from maple_agent.memory_graph.models import MemoryNode, MemoryType
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _node(
    memory_id: str,
    memory_type: MemoryType,
    *,
    context: dict | None = None,
    content: str = "",
    confidence: float = 0.9,
    importance: float = 0.7,
) -> MemoryNode:
    return MemoryNode(
        memory_id=memory_id,
        memory_type=memory_type,
        source="test",
        content=content,
        context=context or {},
        confidence=confidence,
        importance=importance,
    )


def test_relation_creation():
    builder = SemanticAssociationEngine().relation_builder
    source = _node("mem-src", MemoryType.FAILURE)
    target = _node("mem-tgt", MemoryType.EXPERIENCE)
    relation = builder.build(
        relation_type=SemanticRelationType.FAILURE_PATTERN,
        source=source,
        target=target,
        confidence=0.85,
        reasoning="失败关联",
    )
    assert relation.source_memory == "mem-src"
    assert relation.target_memory == "mem-tgt"
    assert relation.relation_type is SemanticRelationType.FAILURE_PATTERN
    assert relation.confidence == 0.85
    assert relation.context["source_type"] == "FAILURE"


def test_failure_association():
    engine = SemanticAssociationEngine()
    failure = _node(
        "mem-fail",
        MemoryType.FAILURE,
        context={"tasks": ["task-3"]},
        content="task-3 failed because missing prerequisite",
    )
    experience = _node(
        "mem-exp",
        MemoryType.EXPERIENCE,
        context={"goal": "新手任务链", "success": True},
        content="success path includes task-3",
    )
    relations = engine.associate([failure, experience])
    assert any(
        relation.relation_type is SemanticRelationType.FAILURE_PATTERN
        for relation in relations
    )


def test_preference_association():
    engine = SemanticAssociationEngine()
    decision = _node(
        "mem-dec-opt-1",
        MemoryType.DECISION,
        context={"action": "TALK"},
        content="TALK -> NPC",
    )
    preference = _node(
        "mem-pref",
        MemoryType.PREFERENCE,
        context={"action": "TALK", "option_id": "opt-1"},
        content="accept option opt-1",
    )
    relations = engine.associate([decision, preference])
    assert any(
        relation.relation_type
        is SemanticRelationType.PREFERENCE_ALIGNMENT
        for relation in relations
    )


def test_world_association():
    engine = SemanticAssociationEngine()
    world = _node(
        "mem-world",
        MemoryType.WORLD,
        context={"location": "射手村"},
        content="location=射手村",
    )
    experience = _node(
        "mem-exp",
        MemoryType.EXPERIENCE,
        context={"goal": "新手任务链"},
        content="在射手村完成任务",
    )
    relations = engine.associate([world, experience])
    assert any(
        relation.relation_type is SemanticRelationType.WORLD_CONTEXT
        for relation in relations
    )


def test_similarity_association():
    engine = SemanticAssociationEngine()
    left = _node(
        "mem-exp-1",
        MemoryType.EXPERIENCE,
        context={"goal": "新手任务链"},
    )
    right = _node(
        "mem-exp-2",
        MemoryType.EXPERIENCE,
        context={"goal": "新手任务链"},
    )
    relations = engine.associate([left, right])
    assert any(
        relation.relation_type is SemanticRelationType.GOAL_SIMILARITY
        for relation in relations
    )


def test_scoring_formula():
    engine = SemanticAssociationEngine()
    source = _node(
        "mem-src",
        MemoryType.FAILURE,
        context={"goal": "新手任务链"},
        importance=0.9,
    )
    target = _node(
        "mem-tgt",
        MemoryType.EXPERIENCE,
        context={"goal": "新手任务链"},
        importance=0.7,
    )
    relation = engine.relation_builder.build(
        relation_type=SemanticRelationType.FAILURE_PATTERN,
        source=source,
        target=target,
        confidence=0.8,
        reasoning="test",
    )
    # context_match = 1/1 = 1.0, confidence 0.8, importance 0.9, recency ~1.0
    score = engine.score(relation, source=source, target=target)
    assert 0 <= score <= 1
    assert score > 0.8


def test_validation_cases():
    validator = SemanticAssociationValidator()
    engine = SemanticAssociationEngine()
    source = _node("mem-src", MemoryType.FAILURE)
    target = _node("mem-tgt", MemoryType.EXPERIENCE)
    strong = engine.relation_builder.build(
        relation_type=SemanticRelationType.FAILURE_PATTERN,
        source=source,
        target=target,
        confidence=0.85,
        reasoning="ok",
    )
    assert (
        validator.validate_relation(strong).verdict
        is SemanticMemoryVerdict.VALID
    )
    weak = strong.model_copy(update={"confidence": 0.2})
    assert (
        validator.validate_relation(weak).verdict
        is SemanticMemoryVerdict.WARNING
    )
    corrupted = strong.model_copy(
        update={"source_memory": "", "target_memory": ""}
    )
    assert (
        validator.validate_relation(corrupted).verdict
        is SemanticMemoryVerdict.BLOCKED
    )
    reference = AssociationReasoner.build_reference([strong])
    assert validator.validate_reference(reference).verdict is (
        SemanticMemoryVerdict.VALID
    )
    empty_reference = AssociationReasoner.build_reference([])
    assert (
        validator.validate_reference(empty_reference).verdict
        is SemanticMemoryVerdict.BLOCKED
    )


def test_reasoner_summary_and_reference():
    engine = SemanticAssociationEngine()
    nodes = [
        _node(
            "mem-fail",
            MemoryType.FAILURE,
            context={"tasks": ["task-3"]},
            content="task-3 failed",
        ),
        _node(
            "mem-exp",
            MemoryType.EXPERIENCE,
            context={"goal": "新手任务链", "success": True},
            content="success path includes task-3",
        ),
    ]
    relations = engine.associate(nodes)
    summary = AssociationReasoner.summarize(relations)
    assert summary.strong_relations >= 1
    assert summary.risk_patterns
    reference = AssociationReasoner.build_reference(relations)
    assert reference.failure_patterns
    assert reference.related_experiences
    assert reference.confidence > 0


def test_replay_generation(tmp_path):
    engine = SemanticAssociationEngine()
    nodes = [
        _node(
            "mem-fail",
            MemoryType.FAILURE,
            context={"tasks": ["task-3"]},
            content="task-3 failed",
        ),
        _node(
            "mem-exp",
            MemoryType.EXPERIENCE,
            context={"goal": "新手任务链", "success": True},
            content="success path includes task-3",
        ),
    ]
    relations = engine.associate(nodes)
    summary = AssociationReasoner.summarize(relations)
    save_semantic_memory_trace(
        tmp_path,
        "trace-replay",
        relations=relations,
        summary=summary.model_dump(mode="json"),
        validation="VALID",
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "semantic_memory_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["relations"]
    assert replay["relations"][0]["relation_type"] == "FAILURE_PATTERN"
    assert replay["summary"]["strong_relations"] >= 1
    assert replay["validation"] == "VALID"


def test_context_integration():
    engine = SemanticAssociationEngine()
    relations = engine.associate(
        [
            _node(
                "mem-fail",
                MemoryType.FAILURE,
                context={"tasks": ["task-3"]},
                content="task-3 failed",
            ),
            _node(
                "mem-exp",
                MemoryType.EXPERIENCE,
                context={"goal": "新手任务链", "success": True},
                content="success path includes task-3",
            ),
        ]
    )
    reference = AssociationReasoner.build_reference(relations)
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        semantic_memory_reference=reference,
    )
    assert context.semantic_memory_reference is not None
    assert context.semantic_memory_reference.failure_patterns
    assert context.semantic_memory_reference.confidence > 0


def test_webui_semantic_memory_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    engine = SemanticAssociationEngine()
    relations = engine.associate(
        [
            _node(
                "mem-fail",
                MemoryType.FAILURE,
                context={"tasks": ["task-3"]},
                content="task-3 failed",
            ),
            _node(
                "mem-exp",
                MemoryType.EXPERIENCE,
                context={"goal": "新手任务链", "success": True},
                content="success path includes task-3",
            ),
        ]
    )
    summary = AssociationReasoner.summarize(relations)
    reference = AssociationReasoner.build_reference(relations)
    payload = {
        "relation_count": len(relations),
        "summary": summary.model_dump(mode="json"),
        "reference": reference.model_dump(mode="json"),
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, semantic_memory=payload)
    with TestClient(app) as client:
        resp = client.get("/api/semantic-memory/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["relation_count"] >= 1
    assert data["summary"]["strong_relations"] >= 1
    assert data["reference"]["failure_patterns"]


def test_webui_semantic_memory_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/semantic-memory/state")
    assert resp.json()["enabled"] is False
