"""Maple Companion Context 单测:玩家/世界/目标/认知/整合/构建/置信/校验/replay/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.decision_reference.models import (
    DecisionReference,
    ReferenceOption,
)
from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.environment_reasoning.models import (
    EnvironmentRiskReference,
)
from maple_agent.events import EventBus
from maple_agent.failure_intelligence.models import (
    FailurePreventionReference,
)
from maple_agent.goal_scheduler.models import OptimizedGoalSchedule
from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.maple_context import (
    MapleCognitiveContextBuilder,
    MapleCompanionContextReference,
    MapleContextBuilder,
    MapleContextValidator,
    MapleContextVerdict,
    MapleGoalContextBuilder,
    MaplePlayerContextBuilder,
    MapleWorldContextBuilder,
    save_maple_context_trace,
)
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import LongHorizonGoal, Milestone
from maple_agent.webui.app import create_app
from maple_agent.world_model import (
    EnvironmentEvent,
    EnvironmentHistoryManager,
    WorldEventType,
)
from maple_agent.world_model.models import PredictedEnvironmentState


def _environment_state() -> EnvironmentState:
    return EnvironmentState(
        environment_id="env-1",
        location="射手村",
        visible_entities=["赫丽娜"],
        confidence=0.9,
        world_context="当前位于 射手村",
    )


def _world_prediction() -> PredictedEnvironmentState:
    return PredictedEnvironmentState(
        predicted_location="射手村",
        confidence=0.8,
        summary="预测位于 射手村",
    )


def _environment_history():
    manager = EnvironmentHistoryManager(history_id="hist-1")
    manager.append(_environment_state())
    manager.add_event(
        EnvironmentEvent(
            event_type=WorldEventType.LOCATION_CHANGED,
            detail="test",
        )
    )
    return manager.history


def _environment_risk() -> EnvironmentRiskReference:
    return EnvironmentRiskReference(
        risk_level="LOW",
        reason="环境稳定",
        recommendation="可正常推进",
    )


def _planning_reference() -> EnvironmentPlanningReference:
    return EnvironmentPlanningReference(
        recommended_goals=["goal-1"],
        blocked_goals=[],
        priority_adjustments=[],
        risk_notes=[],
        opportunity_notes=[],
        confidence=0.9,
    )


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


def _human_alignment() -> HumanAlignedDecisionReference:
    return HumanAlignedDecisionReference(
        preferred_options=[],
        rejected_options=[],
        alignment_score=0.78,
        adjustments=[],
        reasoning=[],
    )


def _memory_reference() -> RelevantMemoryReference:
    return RelevantMemoryReference(confidence=0.7, reasoning=[])


def _semantic_reference() -> SemanticMemoryReference:
    return SemanticMemoryReference(confidence=0.75)


def _failure_prevention() -> FailurePreventionReference:
    return FailurePreventionReference(
        avoid_tasks=[],
        risk_warnings=[],
        recovery_points=[],
        prevention_notes=[],
        summary="prevent",
    )


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
                task_ids=["task-1", "task-2"],
            )
        ],
    )


def _goal_schedule() -> OptimizedGoalSchedule:
    return OptimizedGoalSchedule(
        goal_order=["goal-1"],
        selected_goal="goal-1",
        deferred_goals=[],
        reasoning=[],
        summary="s",
    )


def _agent_context() -> AgentLoopContext:
    return AgentLoopContext(
        trace_id="trace-maple",
        status=AgentLoopStatus.COMPLETED,
        environment_state=_environment_state(),
        environment_prediction=_world_prediction(),
        environment_history=_environment_history(),
        environment_risk_reference=_environment_risk(),
        environment_planning_reference=_planning_reference(),
        decision_reference=_decision_reference(),
        human_alignment_reference=_human_alignment(),
        memory_reference=_memory_reference(),
        semantic_memory_reference=_semantic_reference(),
        failure_prevention_reference=_failure_prevention(),
        goal_state=_goal(),
        goal_schedule=_goal_schedule(),
    )


def test_player_context_creation():
    context = MaplePlayerContextBuilder().build(
        player_id="maple-player-001",
        environment_state=_environment_state(),
    )
    assert context.player_id == "maple-player-001"
    assert context.location == "射手村"
    assert context.confidence == 0.9
    assert context.inventory_reference == []


def test_world_context_aggregation():
    context = MapleWorldContextBuilder().build(
        environment_state=_environment_state(),
        world_prediction=_world_prediction(),
        world_events=_environment_history().timeline,
        environment_risk="LOW",
    )
    assert context.location == "射手村"
    assert context.visible_entities == ["赫丽娜"]
    assert context.world_events
    assert context.environment_risk == "LOW"
    assert context.confidence == 0.85


def test_goal_context_aggregation():
    context = MapleGoalContextBuilder().build(
        active_goal=_goal(),
        goal_schedule=_goal_schedule(),
        planning_reference=_planning_reference(),
        decision_reference=_decision_reference(),
    )
    assert context.active_goal == "完成新手任务链"
    assert context.priority == 10
    assert context.related_tasks == ["task-1", "task-2"]
    assert context.decision_reference == "opt-1"
    assert context.confidence > 0


def test_cognitive_context_aggregation():
    context = MapleCognitiveContextBuilder().build(
        decision_reference=_decision_reference(),
        human_alignment=_human_alignment(),
        memory_reference=_memory_reference(),
        semantic_memory_reference=_semantic_reference(),
        failure_reference=_failure_prevention(),
    )
    assert context.decision_reference == "opt-1"
    assert context.human_alignment_reference == "0.78"
    assert context.failure_reference == "prevent"
    assert context.confidence > 0


def test_context_builder():
    builder = MapleContextBuilder()
    reference = builder.build(
        agent_context=_agent_context(),
        player_id="maple-player-001",
        trace_id="trace-maple",
    )
    assert reference.player_context is not None
    assert reference.world_context is not None
    assert reference.goal_context is not None
    assert reference.cognitive_context is not None
    assert reference.summary
    assert reference.trace_id == "trace-maple"
    assert reference.confidence > 0


def test_confidence_calculation():
    reference = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-maple",
    )
    # player 0.9, world 0.85, goal >0, cognitive >0 的平均
    assert 0 < reference.confidence <= 0.9


def test_existing_module_integration():
    reference = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-maple",
    )
    assert reference.goal_context.active_goal == "完成新手任务链"
    assert reference.world_context.environment_state is not None
    assert reference.cognitive_context.semantic_memory_reference == "0.75"
    assert "射手村" in reference.summary


def test_validator():
    validator = MapleContextValidator()
    full = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-maple",
    )
    assert (
        validator.validate(full).verdict is MapleContextVerdict.VALID
    )
    no_goal = full.model_copy(update={"goal_context": None})
    assert (
        validator.validate(no_goal).verdict is MapleContextVerdict.WARNING
    )
    missing_world = full.model_copy(update={"world_context": None})
    assert (
        validator.validate(missing_world).verdict
        is MapleContextVerdict.BLOCKED
    )
    invalid_confidence = MapleCompanionContextReference.model_construct(
        confidence=1.5,
        trace_id="trace-maple",
    )
    assert (
        validator.validate(invalid_confidence).verdict
        is MapleContextVerdict.BLOCKED
    )


def test_replay_generation(tmp_path):
    reference = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-replay",
    )
    validation = MapleContextValidator().validate(reference)
    save_maple_context_trace(
        tmp_path,
        "trace-replay",
        reference=reference,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "maple_context_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["player_context"]["location"] == "射手村"
    assert replay["world_context"]["environment_risk"] == "LOW"
    assert replay["goal_context"]["active_goal"] == "完成新手任务链"
    assert "cognitive_context" in replay
    assert replay["confidence"] > 0
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    reference = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-maple",
    )
    context = AgentLoopContext(
        trace_id="trace-maple",
        status=AgentLoopStatus.COMPLETED,
        maple_context_reference=reference,
    )
    assert context.maple_context_reference is not None
    assert context.maple_context_reference.summary


def test_webui_maple_context_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    reference = MapleContextBuilder().build(
        agent_context=_agent_context(),
        trace_id="trace-webui",
    )
    validation = MapleContextValidator().validate(reference)
    payload = {
        "player": reference.player_context.model_dump(mode="json"),
        "world": reference.world_context.model_dump(mode="json"),
        "goal": reference.goal_context.model_dump(mode="json"),
        "cognitive": reference.cognitive_context.model_dump(mode="json"),
        "summary": reference.summary,
        "confidence": reference.confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, maple_context=payload)
    with TestClient(app) as client:
        resp = client.get("/api/maple-context/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["player"]["location"] == "射手村"
    assert data["goal"]["active_goal"] == "完成新手任务链"
    assert data["confidence"] > 0
    assert data["validation"] == "VALID"


def test_webui_maple_context_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/maple-context/state")
    assert resp.json()["enabled"] is False
