"""LLM Planner Adapter 单测:动作枚举 / validator / mock LLM / trace / Replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient

from maple_agent.context import ContextBuilder
from maple_agent.events import EventBus
from maple_agent.logging_setup import setup_logging
from maple_agent.planner import (
    LLMPlannerProvider,
    PlannerAction,
    PlanValidationError,
    PlanValidator,
    serialize_for_planner,
)
from maple_agent.planner.models import Constraint, PlanResult, PlanStep
from maple_agent.providers.llm import MockLLMProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app

VALID_PLAN_JSON = (
    '{"plan_id":"p1","summary":"观察并分析","confidence":0.9,'
    '"steps":[{"step_id":"s1","action":"observe","target":"window",'
    '"expected_outcome":"frame"},{"step_id":"s2","action":"analyze",'
    '"target":"context","expected_outcome":"world state"}]}'
)


def _planner_input(trace_id: str = "trace-llm-1") -> object:
    builder = ContextBuilder()
    context = builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="RUNNING",
        trace_id=trace_id,
    )
    return serialize_for_planner(context)


def test_planner_action_enum():
    assert {action.value for action in PlannerAction} == {
        "observe",
        "analyze",
        "query_knowledge",
        "wait",
        "pause",
    }


def test_validator_rejects_invalid_action():
    validator = PlanValidator()
    result = PlanResult(plan_id="p1", steps=[PlanStep(step_id="s1", action="move")])
    with pytest.raises(PlanValidationError, match="非法动作"):
        validator.validate(result)


def test_validator_rejects_constraint_conflict():
    validator = PlanValidator()
    result = PlanResult(plan_id="p1", steps=[PlanStep(step_id="s1", action="pause")])
    constraints = [Constraint(kind="forbidden_actions", value="pause")]
    with pytest.raises(PlanValidationError, match="约束冲突"):
        validator.validate(result, constraints=constraints)


def test_validator_accepts_valid_plan():
    validator = PlanValidator()
    result = PlanResult(
        plan_id="p1",
        steps=[PlanStep(step_id="s1", action="observe")],
    )
    validator.validate(result)


def test_llm_planner_returns_parsed_plan(tmp_path):
    llm = MockLLMProvider(reply=VALID_PLAN_JSON)
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir=tmp_path / "sessions")
    planner_input = _planner_input()
    result = planner.plan(planner_input)
    assert isinstance(result, PlanResult)
    assert [step.action for step in result.steps] == ["observe", "analyze"]
    assert result.summary == "观察并分析"
    assert result.trace_id == "trace-llm-1"
    assert llm.call_count == 1
    assert planner.last_result is result
    assert planner.last_error is None


def test_llm_planner_rejects_invalid_action(tmp_path):
    llm = MockLLMProvider(
        reply='{"plan_id":"p1","summary":"x","confidence":0.5,'
        '"steps":[{"step_id":"s1","action":"attack"}]}'
    )
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir=tmp_path / "sessions")
    with pytest.raises(PlanValidationError):
        planner.plan(_planner_input())
    assert planner.last_error is not None
    assert planner.last_result is None


def test_llm_planner_invalid_json(tmp_path):
    llm = MockLLMProvider(reply="这不是 JSON")
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir=tmp_path / "sessions")
    with pytest.raises(PlanValidationError):
        planner.plan(_planner_input())
    assert planner.last_error is not None


def test_llm_planner_writes_replay(tmp_path):
    llm = MockLLMProvider(reply=VALID_PLAN_JSON)
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir=tmp_path / "sessions")
    planner_input = _planner_input()
    planner.plan(planner_input)
    replay_dir = tmp_path / "sessions" / "trace-llm-1"
    assert (replay_dir / "planner_input.json").exists()
    assert (replay_dir / "planner_result.json").exists()
    saved = json.loads((replay_dir / "planner_result.json").read_text(encoding="utf-8"))
    assert saved["steps"][0]["action"] == "observe"


def test_llm_planner_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    llm = MockLLMProvider(reply=VALID_PLAN_JSON)
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir=tmp_path / "sessions")
    planner.plan(_planner_input("trace-llm-log"))
    log = (tmp_path / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "llm planner plan ok" in log
    assert "trace=trace-llm-log" in log


def test_webui_planner_runtime_status():
    from maple_agent.planner.provider import MockPlannerProvider

    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    planner = MockPlannerProvider()
    planner.plan(
        serialize_for_planner(
            ContextBuilder().build(
                vision_state=None,
                world_state=None,
                runtime_state="READY",
                trace_id="trace-web",
            )
        )
    )
    app = create_app(runtime=runtime, bus=bus, planner=planner)
    with TestClient(app) as client:
        resp = client.get("/api/planner/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["status"] == "ok"
    assert data["steps"] == 2
