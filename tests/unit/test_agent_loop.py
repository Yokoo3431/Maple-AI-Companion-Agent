"""Agent Loop 单测:状态迁移 / retry / 异常恢复 / trace / replay。"""

import json

import pytest
from fastapi.testclient import TestClient

from maple_agent.agent import AgentLoop, AgentLoopState, IllegalTransitionError
from maple_agent.agent.loop import validate_transition
from maple_agent.context import ContextBuilder
from maple_agent.events import Event, EventBus, EventType
from maple_agent.logging_setup import setup_logging
from maple_agent.planner import MockPlannerProvider
from maple_agent.planner.models import PlannerInput, PlanResult, PlanStep
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_transition_table_strict():
    validate_transition(AgentLoopState.IDLE, AgentLoopState.OBSERVING)
    with pytest.raises(IllegalTransitionError):
        validate_transition(AgentLoopState.IDLE, AgentLoopState.PLANNING)


def _build_loop(bus: EventBus, planner=None, tmp_path=None):
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    return AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge),
        planner=planner or MockPlannerProvider(),
        sessions_dir=tmp_path / "sessions" if tmp_path else "sessions",
    )


@pytest.mark.asyncio
async def test_loop_full_run_publishes_events_and_replay(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    loop = _build_loop(bus, tmp_path=tmp_path)
    plan = loop.run_once(
        runtime_state="RUNNING",
        trace_id="trace-loop-1",
    )
    await bus.wait_idle()
    assert loop.state is AgentLoopState.IDLE
    assert plan is not None
    assert loop.last_plan is plan
    assert loop.last_error is None
    event_types = {e.event_type for e in events}
    assert EventType.OBSERVE_STARTED in event_types
    assert EventType.CONTEXT_READY in event_types
    assert EventType.LOOP_PLAN_CREATED in event_types
    assert EventType.PLAN_VALIDATED in event_types
    traces = {e.trace_id for e in events}
    assert traces == {"trace-loop-1"}
    assert [e.event_type for e in events if e.event_type is EventType.LOOP_PLAN_CREATED]

    replay = json.loads(
        (tmp_path / "sessions" / "trace-loop-1" / "agent_loop.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["final_state"] == "IDLE"
    assert replay["context"]["runtime_state"] == "RUNNING"
    assert replay["planner_result"]["steps"]
    assert replay["errors"] == []
    assert "IDLE" in [t["from"] for t in replay["transitions"]]
    await bus.stop()


def test_loop_retries_once_then_succeeds(tmp_path):
    class FlakyPlanner:
        def __init__(self) -> None:
            self.calls = 0

        def plan(self, context: PlannerInput) -> PlanResult:
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("boom once")
            return PlanResult(
                plan_id="p1",
                steps=[PlanStep(step_id="s1", action="observe")],
                trace_id=context.trace_id,
            )

    bus = EventBus()
    flaky = FlakyPlanner()
    loop = _build_loop(bus, planner=flaky, tmp_path=tmp_path)
    plan = loop.run_once(runtime_state="READY", trace_id="trace-retry")
    assert flaky.calls == 2
    assert loop.state is AgentLoopState.IDLE
    assert loop.last_error is None
    assert plan.steps[0].action == "observe"


def test_loop_retry_exhausted_goes_error_and_recovers(tmp_path):
    class AlwaysFailPlanner:
        def plan(self, context: PlannerInput) -> PlanResult:
            raise RuntimeError("always fails")

    bus = EventBus()
    loop = _build_loop(bus, planner=AlwaysFailPlanner(), tmp_path=tmp_path)
    with pytest.raises(RuntimeError):
        loop.run_once(runtime_state="READY", trace_id="trace-fail")
    assert loop.state is AgentLoopState.ERROR
    assert loop.last_error is not None
    replay = json.loads(
        (tmp_path / "sessions" / "trace-fail" / "agent_loop.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["errors"] == ["always fails"]
    assert replay["final_state"] == "ERROR"
    loop.reset()
    assert loop.state is AgentLoopState.IDLE
    assert loop.last_error is None


@pytest.mark.asyncio
async def test_loop_error_event_published():
    class AlwaysFailPlanner:
        def plan(self, context: PlannerInput) -> PlanResult:
            raise RuntimeError("loop boom")

    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    loop = _build_loop(bus, planner=AlwaysFailPlanner())
    with pytest.raises(RuntimeError):
        loop.run_once(runtime_state="READY", trace_id="trace-err-event")
    await bus.wait_idle()
    error_events = [
        e for e in events if e.event_type is EventType.LOOP_ERROR
    ]
    assert error_events
    assert error_events[0].trace_id == "trace-err-event"
    await bus.stop()


def test_loop_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    bus = EventBus()
    loop = _build_loop(bus, tmp_path=tmp_path)
    loop.run_once(runtime_state="READY", trace_id="trace-loop-log")
    log = (tmp_path / "logs" / "agent.log").read_text(encoding="utf-8")
    assert "agent loop state: IDLE -> OBSERVING" in log
    assert "trace=trace-loop-log" in log


def test_webui_loop_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    loop = _build_loop(bus)
    loop.run_once(runtime_state="OFFLINE", trace_id="trace-web-loop")
    app = create_app(runtime=runtime, bus=bus, agent_loop=loop)
    with TestClient(app) as client:
        resp = client.get("/api/loop/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["state"] == "IDLE"
    assert data["steps"] == 2


def test_webui_loop_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/loop/state")
    assert resp.json()["enabled"] is False
