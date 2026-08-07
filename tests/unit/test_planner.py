"""Planner 契约单测:schema / serialization / mock planner / trace / WebUI。"""

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.context import AgentContext, ContextBuilder
from maple_agent.events import EventBus
from maple_agent.logging_setup import setup_logging
from maple_agent.planner import (
    Goal,
    MockPlannerProvider,
    PlannerInput,
    PlanResult,
    PlanStep,
    serialize_for_planner,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_planner_schema_validation():
    planner_input = PlannerInput(
        context=AgentContext(runtime_state="READY"),
        trace_id="t-1",
    )
    assert planner_input.context.runtime_state == "READY"
    step = PlanStep(step_id="s1", action="observe")
    result = PlanResult(
        plan_id="p1",
        steps=[step],
        summary="ok",
        confidence=0.9,
        trace_id="t-1",
    )
    assert result.steps[0].action == "observe"
    with pytest.raises(ValidationError):
        PlanResult(plan_id="p1", steps=[step], confidence=1.5)


def test_serialize_for_planner():
    builder = ContextBuilder()
    context = builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="READY",
        trace_id="trace-ser",
    )
    goals = [Goal(goal_id="g1", description="观察地图")]
    planner_input = serialize_for_planner(context, goals=goals)
    assert planner_input.context is context
    assert planner_input.trace_id == "trace-ser"
    assert planner_input.goals[0].goal_id == "g1"
    assert any(item.kind == "safety" for item in planner_input.constraints)


def test_mock_planner_returns_plan():
    builder = ContextBuilder()
    context = builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="RUNNING",
        trace_id="trace-plan-1",
    )
    planner_input = serialize_for_planner(context)
    planner = MockPlannerProvider()
    result = planner.plan(planner_input)
    assert isinstance(result, PlanResult)
    assert result.trace_id == "trace-plan-1"
    assert len(result.steps) == 2
    assert result.summary == "plan for RUNNING"
    assert planner.call_count == 1


def test_mock_planner_failure():
    planner = MockPlannerProvider(raise_on_plan=True)
    planner_input = PlannerInput(context=AgentContext(runtime_state="READY"))
    with pytest.raises(RuntimeError):
        planner.plan(planner_input)


def test_mock_planner_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    planner = MockPlannerProvider()
    planner_input = PlannerInput(
        context=AgentContext(runtime_state="READY"),
        trace_id="trace-plan-log",
    )
    planner.plan(planner_input)
    log = (tmp_path / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "planner plan:" in log
    assert "trace=trace-plan-log" in log


def test_webui_planner_state_enabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus, planner=MockPlannerProvider())
    with TestClient(app) as client:
        resp = client.get("/api/planner/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["planner"] == "MockPlannerProvider"


def test_webui_planner_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/planner/state")
    assert resp.json()["enabled"] is False
