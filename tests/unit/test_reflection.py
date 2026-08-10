"""Reflection 单测:成功反思 / 执行失败 / 世界不一致 / 触发重规划 / Replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.context.models import AgentContext
from maple_agent.events import EventBus
from maple_agent.execution.feedback import ExecutionFeedback
from maple_agent.executor.models import ExecutionResult, ExecutionStatus
from maple_agent.fusion.models import WorldState
from maple_agent.knowledge.models import MapInfo
from maple_agent.reflection import (
    FailureType,
    ReflectionEngine,
    ReflectionMemory,
    ReflectionTrigger,
    TriggerDecision,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _execution(
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
    message: str = "mock execution only",
) -> ExecutionResult:
    return ExecutionResult(
        execution_id="exec-1",
        status=status,
        message=message,
        trace_id="trace-reflect",
    )


def _feedback(
    *,
    success: bool = True,
    observed: dict | None = None,
    reason: str = "mock observation",
) -> ExecutionFeedback:
    return ExecutionFeedback(
        execution_id="exec-1",
        observed=observed or {},
        success=success,
        reason=reason,
        trace_id="trace-reflect",
    )


def _world(confidence: float = 0.9) -> WorldState:
    return WorldState(
        current_map=MapInfo(map_id=1, name="射手村"),
        confidence=confidence,
    )


def test_success_reflection():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(),
        world_state=_world(),
        expected_result="任务已接受(语义)",
        trace_id="trace-success",
    )
    assert result.success is True
    assert result.failure_type is None
    assert result.state_update == "accepted"
    assert result.next_action == "continue"
    assert result.expected_result == "任务已接受(语义)"
    assert result.actual_result == "mock execution only"
    assert result.confidence == 0.9
    assert engine.trigger.evaluate(result) is TriggerDecision.NO_ACTION


def test_execution_failed():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(status=ExecutionStatus.FAILED, message="always fail"),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-failed",
    )
    assert result.success is False
    assert result.failure_type is FailureType.EXECUTION_FAILED
    assert result.failure_reason == "always fail"
    assert result.next_action == "replan"
    assert result.state_update == "rejected"


def test_world_mismatch():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(observed={"world_mismatch": True}),
        world_state=_world(),
        trace_id="trace-mismatch",
    )
    assert result.success is False
    assert result.failure_type is FailureType.WORLD_MISMATCH
    assert "世界状态与预期不一致" in result.failure_reason


def test_knowledge_error():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(observed={"knowledge_error": True}),
        world_state=_world(),
        trace_id="trace-knowledge",
    )
    assert result.success is False
    assert result.failure_type is FailureType.KNOWLEDGE_ERROR


def test_low_confidence():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(),
        world_state=_world(confidence=0.2),
        trace_id="trace-lowconf",
    )
    assert result.success is False
    assert result.failure_type is FailureType.LOW_CONFIDENCE
    assert "置信度过低" in result.failure_reason


def test_observation_failed():
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(success=False, reason="观察失败"),
        world_state=_world(),
        trace_id="trace-observation",
    )
    assert result.success is False
    assert result.failure_type is FailureType.OBSERVATION_FAILED


def test_trigger_replan_rules():
    trigger = ReflectionTrigger()
    success = _success_result()
    assert trigger.evaluate(success) is TriggerDecision.NO_ACTION
    assert (
        trigger.evaluate(success, execution_failed=True)
        is TriggerDecision.REPLAN_REQUIRED
    )
    assert (
        trigger.evaluate(success, feedback_success=False)
        is TriggerDecision.REPLAN_REQUIRED
    )
    assert (
        trigger.evaluate(success, world_mismatch=True)
        is TriggerDecision.REPLAN_REQUIRED
    )


def test_memory_records_failure():
    memory = ReflectionMemory()
    engine = ReflectionEngine(memory=memory)
    engine.reflect(
        _execution(status=ExecutionStatus.FAILED, message="fail 1"),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-mem-1",
    )
    engine.reflect(
        _execution(status=ExecutionStatus.FAILED, message="fail 2"),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-mem-2",
    )
    state = memory.state
    assert state.retry_count == 2
    assert len(state.failure_history) == 2
    assert state.last_reflection is not None
    assert state.last_reflection.failure_reason == "fail 2"


def test_context_mounts_reflection_state():
    memory = ReflectionMemory()
    engine = ReflectionEngine(memory=memory)
    engine.reflect(
        _execution(status=ExecutionStatus.FAILED),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-context",
    )
    context = AgentContext(
        runtime_state="READY",
        reflection_state=memory.state,
        trace_id="trace-context",
    )
    assert context.reflection_state is not None
    assert context.reflection_state.retry_count == 1
    assert context.reflection_state.last_reflection is not None


def test_replay_generation(tmp_path):
    engine = ReflectionEngine(sessions_dir=tmp_path)
    engine.reflect(
        _execution(),
        feedback=_feedback(),
        world_state=_world(),
        expected_result="任务已接受(语义)",
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "reflection_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["trace_id"] == "trace-replay"
    assert replay["execution"]["status"] == "COMPLETED"
    assert replay["expected"] == "任务已接受(语义)"
    assert replay["actual"] == "mock execution only"
    assert replay["analysis"]["success"] is True
    assert replay["analysis"]["failure_type"] is None
    assert replay["trigger"] == "NO_ACTION"
    assert replay["next_plan"] == "continue"
    assert replay["reflection"]["reflection_id"]


def test_webui_reflection_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    engine = ReflectionEngine()
    result = engine.reflect(
        _execution(),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-webui",
    )
    payload = {
        "result": result.model_dump(mode="json"),
        "trigger": TriggerDecision.NO_ACTION.value,
        "state": engine.memory.state.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, reflection=payload)
    with TestClient(app) as client:
        resp = client.get("/api/reflection/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["result"]["success"] is True
    assert data["trigger"] == "NO_ACTION"
    assert data["state"]["retry_count"] == 0


def test_webui_reflection_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/reflection/state")
    assert resp.json()["enabled"] is False


def _success_result():
    engine = ReflectionEngine()
    return engine.reflect(
        _execution(),
        feedback=_feedback(),
        world_state=_world(),
        trace_id="trace-trigger",
    )
