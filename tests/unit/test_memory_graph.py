"""Cognitive Memory Graph 单测。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.decision_reference.models import (
    DecisionReference,
    ReferenceOption,
)
from maple_agent.environment.models import EnvironmentState
from maple_agent.events import EventBus
from maple_agent.failure_intelligence.models import FailurePatternRecord
from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.human_alignment.preference import PreferenceMemory
from maple_agent.memory_graph import (
    MemoryConsolidator,
    MemoryGraphValidator,
    MemoryGraphVerdict,
    MemoryIndex,
    MemoryNode,
    MemoryRelation,
    MemoryRelationBuilder,
    MemoryRelationType,
    MemoryRetriever,
    MemoryType,
    save_memory_graph_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import LongHorizonGoal, Milestone
from maple_agent.webui.app import create_app
from maple_agent.world_model import EnvironmentHistoryManager


def _experience() -> GoalExperienceRecord:
    return GoalExperienceRecord(
        experience_id="exp-1",
        goal_type="QUEST",
        goal_description="完成新手任务链",
        successful_path=["task-1", "task-2"],
        task_pattern=["task-1", "task-2"],
        success=True,
        confidence=0.9,
    )


def _failure() -> FailurePatternRecord:
    return FailurePatternRecord(
        pattern_id="fp-1",
        failure_type="EXECUTION_FAILED",
        context_snapshot={},
        affected_tasks=["task-3"],
        root_cause="前置条件未满足",
        resolution_strategy="retry",
        success_rate=0.3,
        confidence=0.7,
    )


def _world_history():
    manager = EnvironmentHistoryManager(history_id="hist-1")
    manager.append(
        EnvironmentState(
            environment_id="env-1",
            location="射手村",
            visible_entities=["赫丽娜"],
            confidence=0.9,
        )
    )
    return manager.history


def _decision_reference() -> DecisionReference:
    return DecisionReference(
        recommended_options=[
            ReferenceOption(
                option_id="opt-1",
                action="TALK",
                target="NPC",
                recommendation="recommended",
                confidence=0.9,
                reason="NPC 交互",
            )
        ],
        alternative_options=[],
        risk_level="LOW",
        confidence=0.9,
        reasoning=["r"],
        environment_alignment=0.9,
        planning_alignment=0.8,
    )


def _preference_memory() -> PreferenceMemory:
    memory = PreferenceMemory()
    memory.record(option_id="opt-1", action="accept", reason="ok")
    return memory


def _goal() -> LongHorizonGoal:
    return LongHorizonGoal(
        goal_id="goal-1",
        description="完成新手任务链",
        priority=10,
        success_condition="ok",
        milestones=[
            Milestone(
                milestone_id="ms-1",
                title="任务",
                order=0,
                task_ids=["task-1"],
            )
        ],
    )


def test_memory_node_creation():
    node = MemoryNode(
        memory_id="mem-001",
        memory_type=MemoryType.FAILURE,
        source="failure_intelligence",
        content="task-3 failed",
        confidence=0.85,
        importance=0.9,
    )
    assert node.memory_id == "mem-001"
    assert node.memory_type is MemoryType.FAILURE
    assert node.confidence == 0.85
    assert node.timestamp


def test_memory_type_validation():
    assert set(MemoryType) == {
        MemoryType.EXPERIENCE,
        MemoryType.FAILURE,
        MemoryType.WORLD,
        MemoryType.PREFERENCE,
        MemoryType.DECISION,
    }


def test_relation_creation_and_auto_link():
    left = MemoryNode(
        memory_id="mem-a",
        memory_type=MemoryType.EXPERIENCE,
        context={"goal": "新手任务链"},
        confidence=0.9,
        importance=0.7,
    )
    right = MemoryNode(
        memory_id="mem-b",
        memory_type=MemoryType.FAILURE,
        context={"goal": "新手任务链"},
        confidence=0.7,
        importance=0.9,
    )
    linked = MemoryRelationBuilder().auto_link([left, right])
    assert any(
        relation.target_id == "mem-b"
        and relation.relation_type is MemoryRelationType.SIMILAR_TO
        for relation in linked[0].relations
    )
    assert MemoryRelation(
        relation_type=MemoryRelationType.CAUSED_BY,
        target_id="mem-x",
    ).relation_type is MemoryRelationType.CAUSED_BY


def test_consolidation_from_experience():
    nodes = MemoryConsolidator().consolidate(experiences=[_experience()])
    assert len(nodes) == 1
    assert nodes[0].memory_type is MemoryType.EXPERIENCE
    assert nodes[0].source == "goal_memory"
    assert "task-1" in nodes[0].content


def test_consolidation_from_failure():
    nodes = MemoryConsolidator().consolidate(failures=[_failure()])
    assert len(nodes) == 1
    assert nodes[0].memory_type is MemoryType.FAILURE
    assert nodes[0].source == "failure_intelligence"
    assert "前置条件未满足" in nodes[0].content


def test_consolidation_from_preference():
    nodes = MemoryConsolidator().consolidate(
        preferences=_preference_memory(),
    )
    assert len(nodes) == 1
    assert nodes[0].memory_type is MemoryType.PREFERENCE
    assert nodes[0].source == "human_alignment"


def test_consolidation_all_types():
    nodes = MemoryConsolidator().consolidate(
        experiences=[_experience()],
        failures=[_failure()],
        world_history=_world_history(),
        decision_reference=_decision_reference(),
        preferences=_preference_memory(),
    )
    types = {node.memory_type for node in nodes}
    assert MemoryType.EXPERIENCE in types
    assert MemoryType.FAILURE in types
    assert MemoryType.WORLD in types
    assert MemoryType.PREFERENCE in types
    assert MemoryType.DECISION in types


def test_retrieval_similarity_scoring():
    nodes = MemoryConsolidator().consolidate(
        experiences=[_experience()],
        failures=[_failure()],
        decision_reference=_decision_reference(),
        preferences=_preference_memory(),
    )
    index = MemoryIndex()
    index.add_many(nodes)
    retriever = MemoryRetriever(index)
    reference = retriever.retrieve(
        current_goal=_goal(),
        decision_reference=_decision_reference(),
    )
    assert reference.relevant_memories
    assert reference.similar_experiences
    assert reference.confidence > 0
    assert reference.reasoning


def test_validator_cases():
    validator = MemoryGraphValidator()
    valid = MemoryNode(
        memory_id="mem-valid",
        memory_type=MemoryType.WORLD,
        context={"location": "射手村"},
        relations=[
            MemoryRelation(
                relation_type=MemoryRelationType.SIMILAR_TO,
                target_id="mem-x",
            )
        ],
        confidence=0.9,
        importance=0.5,
    )
    assert (
        validator.validate_node(valid).verdict is MemoryGraphVerdict.VALID
    )
    warning = MemoryNode(
        memory_id="mem-warning",
        memory_type=MemoryType.WORLD,
        confidence=0.9,
        importance=0.5,
    )
    assert (
        validator.validate_node(warning).verdict
        is MemoryGraphVerdict.WARNING
    )
    blocked = MemoryNode.model_construct(
        memory_id="mem-blocked",
        memory_type=MemoryType.WORLD,
        confidence=1.5,
        importance=0.5,
    )
    assert (
        validator.validate_node(blocked).verdict
        is MemoryGraphVerdict.BLOCKED
    )


def test_replay_generation(tmp_path):
    nodes = MemoryConsolidator().consolidate(
        experiences=[_experience()],
        failures=[_failure()],
        preferences=_preference_memory(),
    )
    index = MemoryIndex()
    index.add_many(nodes)
    retriever = MemoryRetriever(index)
    reference = retriever.retrieve(current_goal=_goal())
    relations = [
        relation for node in nodes for relation in node.relations
    ]
    save_memory_graph_trace(
        tmp_path,
        "trace-replay",
        memory_nodes=nodes,
        relations=relations,
        retrieval=reference,
        validation="VALID",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "memory_graph_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert len(replay["memory_nodes"]) >= 2
    assert isinstance(replay["relations"], list)
    assert replay["retrieval"]["similar_experiences"]
    assert replay["validation"] == "VALID"


def test_context_integration():
    nodes = MemoryConsolidator().consolidate(
        experiences=[_experience()],
        failures=[_failure()],
    )
    index = MemoryIndex()
    index.add_many(nodes)
    reference = MemoryRetriever(index).retrieve(current_goal=_goal())
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        memory_reference=reference,
    )
    assert context.memory_reference is not None
    assert context.memory_reference.relevant_memories
    assert context.memory_reference.confidence > 0


def test_webui_memory_graph_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    nodes = MemoryConsolidator().consolidate(
        experiences=[_experience()],
        failures=[_failure()],
        preferences=_preference_memory(),
    )
    index = MemoryIndex()
    index.add_many(nodes)
    reference = MemoryRetriever(index).retrieve(current_goal=_goal())
    payload = {
        "memory_count": index.count(),
        "memory_types": sorted(
            {node.memory_type.value for node in nodes}
        ),
        "retrieval": reference.model_dump(mode="json"),
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, memory_graph=payload)
    with TestClient(app) as client:
        resp = client.get("/api/memory-graph/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["memory_count"] >= 3
    assert "EXPERIENCE" in data["memory_types"]
    assert data["retrieval"]["similar_experiences"]


def test_webui_memory_graph_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/memory-graph/state")
    assert resp.json()["enabled"] is False
