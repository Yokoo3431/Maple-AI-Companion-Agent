"""Executor Contract 单测:schema / provider / safety / mock / replay / loop / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.agent import AgentLoop
from maple_agent.context import ContextBuilder
from maple_agent.events import Event, EventBus, EventType
from maple_agent.executor import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    ExecutorProvider,
    MockExecutorProvider,
    SafetyGate,
    SafetyResult,
)
from maple_agent.planner import MockPlannerProvider
from maple_agent.planner.models import PlanStep
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_execution_models_schema():
    task = ExecutionTask(
        execution_id="e1",
        plan_id="p1",
        step_id="s1",
        action="TALK",
        target="101",
        trace_id="t1",
    )
    assert task.status is ExecutionStatus.CREATED
    result = ExecutionResult(
        execution_id="e1",
        status=ExecutionStatus.COMPLETED,
        message="mock execution only",
    )
    assert result.status is ExecutionStatus.COMPLETED
    with pytest.raises(ValidationError):
        ExecutionTask(execution_id="e2", action="TALK", status="NOT_A_STATUS")
    safety = SafetyResult(allowed=True, mode="mock_only")
    assert safety.allowed is True


def test_mock_executor_satisfies_contract():
    provider = MockExecutorProvider()
    assert isinstance(provider, ExecutorProvider)


def test_safety_gate_blocks_physical_keywords():
    gate = SafetyGate()
    for action in ("CLICK", "SEND_KEY", "MOUSE_MOVE", "PRESS_KEY"):
        result = gate.check(
            ExecutionTask(execution_id="e", action=action, target="x")
        )
        assert result.allowed is False
        assert "物理动作关键字" in result.reason


def test_safety_gate_allows_semantic_action():
    gate = SafetyGate()
    result = gate.check(ExecutionTask(execution_id="e", action="TALK", target="101"))
    assert result.allowed is True
    assert result.mode == "mock_only"
    blocked = gate.check(
        ExecutionTask(execution_id="e2", action="FLY_TO_MOON", target="x")
    )
    assert blocked.allowed is False
    assert "动作不允许" in blocked.reason


def test_mock_executor_completed():
    provider = MockExecutorProvider()
    task = ExecutionTask(
        execution_id="e1",
        plan_id="p1",
        step_id="s1",
        action="TALK",
        target="101",
        trace_id="t1",
    )
    result = provider.execute(task)
    assert result.status is ExecutionStatus.COMPLETED
    assert result.message == "mock execution only"
    assert result.trace_id == "t1"
    assert provider.call_count == 1


def test_mock_executor_blocked():
    provider = MockExecutorProvider()
    task = ExecutionTask(
        execution_id="e2",
        action="SEND_KEY",
        target="ENTER",
        trace_id="t2",
    )
    result = provider.execute(task)
    assert result.status is ExecutionStatus.BLOCKED
    assert provider.last_result is result


@pytest.mark.asyncio
async def test_loop_execution_events_and_replay(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    planner = MockPlannerProvider(
        steps=[
            PlanStep(step_id="s1", action="observe", target="window"),
            PlanStep(step_id="s2", action="analyze", target="context"),
        ]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(),
        planner=planner,
        sessions_dir=tmp_path / "sessions",
        executor=MockExecutorProvider(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-exec-loop")
    await bus.wait_idle()
    assert loop.state.value == "IDLE"
    assert loop.last_execution is not None
    assert loop.last_execution.status is ExecutionStatus.COMPLETED
    assert len(loop.execution_history) == 2
    event_types = {event.event_type for event in events}
    assert EventType.EXECUTION_CREATED in event_types
    assert EventType.EXECUTION_COMPLETED in event_types
    completed_traces = {
        event.trace_id
        for event in events
        if event.event_type is EventType.EXECUTION_COMPLETED
    }
    assert completed_traces == {"trace-exec-loop"}
    replay = json.loads(
        (tmp_path / "sessions" / "trace-exec-loop" / "execution.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(replay["executions"]) == 2
    assert all(item["status"] == "COMPLETED" for item in replay["executions"])
    assert loop.last_context.execution_context is not None
    await bus.stop()


@pytest.mark.asyncio
async def test_loop_execution_blocked(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    planner = MockPlannerProvider(
        steps=[PlanStep(step_id="s1", action="execute", target="cmd")]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(),
        planner=planner,
        sessions_dir=tmp_path / "sessions",
        executor=MockExecutorProvider(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-exec-blocked")
    await bus.wait_idle()
    assert loop.last_execution.status is ExecutionStatus.BLOCKED
    blocked = [
        event
        for event in events
        if event.event_type is EventType.EXECUTION_BLOCKED
    ]
    assert blocked and blocked[0].trace_id == "trace-exec-blocked"
    await bus.stop()


def test_webui_execution_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(),
        planner=MockPlannerProvider(),
        executor=MockExecutorProvider(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-exec-web")
    app = create_app(runtime=runtime, bus=bus, agent_loop=loop)
    with TestClient(app) as client:
        resp = client.get("/api/execution/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["mode"] == "MOCK ONLY"
    assert data["status"] in {"COMPLETED", "BLOCKED"}
    assert data["history_count"] >= 1


def test_webui_execution_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/execution/state")
    assert resp.json()["enabled"] is False
