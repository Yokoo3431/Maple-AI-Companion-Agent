"""Goal System 单测:model / state / selector / provider / context / planner / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.agent import AgentLoop
from maple_agent.context import AgentContext, ContextBuilder, GoalContext
from maple_agent.events import Event, EventBus, EventType
from maple_agent.goal import (
    Goal,
    GoalStateMachine,
    GoalStatus,
    GoalTransitionError,
    GoalType,
    MockGoalProvider,
    RuleBasedGoalSelector,
)
from maple_agent.planner import MockPlannerProvider, serialize_for_planner
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_goal_model_schema():
    goal = Goal(goal_id="g1", goal_type="QUEST", title="新手教学", priority=10)
    assert goal.goal_type is GoalType.QUEST
    assert goal.status is GoalStatus.CREATED
    with pytest.raises(ValidationError):
        Goal(goal_id="g2", title="x", priority=0)
    with pytest.raises(ValidationError):
        Goal(goal_id="g3", title="x", goal_type="BAD_TYPE")


def test_state_machine_legal_transitions():
    machine = GoalStateMachine()
    goal = Goal(goal_id="g1", title="x")
    goal = machine.transition(goal, GoalStatus.ACTIVE)
    goal = machine.transition(goal, GoalStatus.PAUSED)
    goal = machine.transition(goal, GoalStatus.ACTIVE)
    goal = machine.transition(goal, GoalStatus.COMPLETED)
    assert goal.status is GoalStatus.COMPLETED
    goal = Goal(goal_id="g2", title="x")
    goal = machine.transition(goal, GoalStatus.ACTIVE)
    assert machine.transition(goal, GoalStatus.FAILED).status is GoalStatus.FAILED
    goal = Goal(goal_id="g3", title="x")
    goal = machine.transition(goal, GoalStatus.ACTIVE)
    assert machine.transition(goal, GoalStatus.CANCELLED).status is GoalStatus.CANCELLED


def test_state_machine_illegal_transitions():
    machine = GoalStateMachine()
    completed = Goal(goal_id="g1", title="x", status=GoalStatus.COMPLETED)
    with pytest.raises(GoalTransitionError):
        machine.transition(completed, GoalStatus.ACTIVE)
    created = Goal(goal_id="g2", title="x")
    with pytest.raises(GoalTransitionError):
        machine.transition(created, GoalStatus.COMPLETED)


def test_selector_priority_and_confidence():
    selector = RuleBasedGoalSelector()
    context = AgentContext(runtime_state="READY")
    goals = [
        Goal(goal_id="a", title="A", priority=5),
        Goal(goal_id="b", title="B", priority=10),
    ]
    assert selector.select(context, goals).goal_id == "b"
    goals = [
        Goal(goal_id="a", title="A", priority=10, confidence=0.7),
        Goal(goal_id="b", title="B", priority=10, confidence=0.9),
    ]
    assert selector.select(context, goals).goal_id == "b"


def test_selector_excludes_completed():
    selector = RuleBasedGoalSelector()
    context = AgentContext(runtime_state="READY")
    goals = [
        Goal(goal_id="a", title="A", priority=10, status=GoalStatus.COMPLETED),
        Goal(goal_id="b", title="B", priority=5),
    ]
    assert selector.select(context, goals).goal_id == "b"
    assert selector.select(context, []) is None


def test_mock_goal_provider():
    provider = MockGoalProvider(
        goals=[Goal(goal_id="g1", title="A", priority=10)]
    )
    assert len(provider.get_candidate_goals()) == 1
    provider.activate(provider.get_candidate_goals()[0])
    assert provider.get_active_goal().status is GoalStatus.ACTIVE
    provider.save_goal_status(
        provider.get_active_goal().model_copy(update={"status": GoalStatus.COMPLETED})
    )
    assert provider.get_candidate_goals()[0].status is GoalStatus.COMPLETED


def test_context_goal_fusion():
    goal = Goal(
        goal_id="g1",
        goal_type="QUEST",
        title="新手教学",
        priority=10,
        status=GoalStatus.ACTIVE,
    )
    context = AgentContext(
        runtime_state="READY",
        goal_context=GoalContext(
            active_goal=goal,
            candidate_goals=[goal],
            goal_history=[goal],
            trace_id="t1",
        ),
    )
    assert context.goal_context.active_goal.title == "新手教学"
    assert len(context.goal_context.candidate_goals) == 1
    assert context.world_state is None  # WorldState 不变


def test_planner_serializes_current_goal():
    goal = Goal(goal_id="g1", goal_type="QUEST", title="新手教学", priority=10)
    context = AgentContext(
        runtime_state="READY",
        goal_context=GoalContext(active_goal=goal, trace_id="t1"),
    )
    planner_input = serialize_for_planner(context)
    assert planner_input.current_goal is goal


@pytest.mark.asyncio
async def test_loop_goal_selection_events_and_replay(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockGoalProvider(
        goals=[
            Goal(goal_id="g1", goal_type="QUEST", title="新手教学", priority=10),
            Goal(goal_id="g2", goal_type="LEVELING", title="升级", priority=5),
        ]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(),
        planner=MockPlannerProvider(),
        sessions_dir=tmp_path / "sessions",
        goal_provider=provider,
        goal_selector=RuleBasedGoalSelector(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-goal-loop")
    await bus.wait_idle()
    assert provider.get_active_goal().goal_id == "g1"
    assert provider.get_active_goal().status is GoalStatus.ACTIVE
    event_types = {event.event_type for event in events}
    assert EventType.GOAL_SELECTED in event_types
    assert EventType.GOAL_CHANGED in event_types
    selected_traces = {
        event.trace_id
        for event in events
        if event.event_type is EventType.GOAL_SELECTED
    }
    assert selected_traces == {"trace-goal-loop"}
    replay = json.loads(
        (tmp_path / "sessions" / "trace-goal-loop" / "goal_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["selected"]["goal_id"] == "g1"
    assert len(replay["candidates"]) == 2
    await bus.stop()


@pytest.mark.asyncio
async def test_loop_mark_goal_completed_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockGoalProvider(goals=[Goal(goal_id="g1", title="A", priority=10)])
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(),
        planner=MockPlannerProvider(),
        goal_provider=provider,
        goal_selector=RuleBasedGoalSelector(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-gc")
    loop.mark_goal_completed("g1", trace_id="trace-gc")
    await bus.wait_idle()
    assert provider.get_active_goal().status is GoalStatus.COMPLETED
    completed = [
        event
        for event in events
        if event.event_type is EventType.GOAL_COMPLETED
    ]
    assert completed and completed[0].trace_id == "trace-gc"
    await bus.stop()


def test_webui_goal_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    provider = MockGoalProvider(
        goals=[Goal(goal_id="g1", goal_type="QUEST", title="新手教学", priority=10)]
    )
    provider.activate(provider.get_candidate_goals()[0])
    app = create_app(runtime=runtime, bus=bus, goal_provider=provider)
    with TestClient(app) as client:
        resp = client.get("/api/goal/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["active_goal"]["title"] == "新手教学"
    assert data["active_goal"]["priority"] == 10
    assert data["candidate_count"] == 1


def test_webui_goal_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/goal/state")
    assert resp.json()["enabled"] is False
