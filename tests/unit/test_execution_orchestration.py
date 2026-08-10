"""Execution Orchestration 单测:Task 生成 / 顺序执行 / 状态机 / 安全 / 异常 / Replay / WebUI。"""

from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from maple_agent.action_plan.models import ActionPlan, ActionPlanStatus, ActionStep
from maple_agent.events import EventBus
from maple_agent.execution import (
    ExecutionOrchestrator,
    ExecutionStepStatus,
    IllegalTransitionError,
    validate_transition,
)
from maple_agent.executor.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _plan(
    *,
    action: str = "TALK",
    target: str = "赫丽娜",
    steps: int = 3,
) -> ActionPlan:
    return ActionPlan(
        plan_id="plan-1",
        decision_id="d1",
        goal_id="goal-1",
        action=action,
        target=target,
        prerequisites=["地图: 射手村"],
        validation_conditions=["目标可达"],
        expected_result="任务已接受(语义)",
        confidence=0.9,
        status=ActionPlanStatus.READY,
        steps=[
            ActionStep(
                step_id=f"step-{index + 1}",
                description=f"步骤 {index + 1}",
                required_observation=f"观察 {index + 1}",
                success_condition=f"条件 {index + 1}",
            )
            for index in range(steps)
        ],
    )


class FlakyExecutor:
    """第一次失败,重试后成功。"""

    def __init__(self) -> None:
        self.calls = 0

    def execute(self, task: ExecutionTask) -> ExecutionResult:
        self.calls += 1
        if self.calls == 1:
            return ExecutionResult(
                execution_id=task.execution_id,
                status=ExecutionStatus.FAILED,
                message="transient failure",
                trace_id=task.trace_id,
            )
        return ExecutionResult(
            execution_id=task.execution_id,
            status=ExecutionStatus.COMPLETED,
            message="mock execution only",
            trace_id=task.trace_id,
        )


class AlwaysFailExecutor:
    """始终失败。"""

    def execute(self, task: ExecutionTask) -> ExecutionResult:
        return ExecutionResult(
            execution_id=task.execution_id,
            status=ExecutionStatus.FAILED,
            message="always fail",
            trace_id=task.trace_id,
        )


def test_plan_to_tasks_mapping():
    orchestrator = ExecutionOrchestrator()
    orchestrator.run(_plan(), trace_id="trace-map")
    records = orchestrator.last_records
    assert len(records) == 3
    first = records[0]
    assert first.task.plan_id == "plan-1"
    assert first.task.step_id == "step-1"
    assert first.task.step_index == 1
    assert first.task.action == "TALK"
    assert first.task.target == "赫丽娜"
    assert first.task.required_observation == "观察 1"
    assert first.task.success_condition == "条件 1"
    assert first.task.max_retry == 1


def test_multi_step_sequential_execution():
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(_plan(), trace_id="trace-seq")
    assert state.status == "COMPLETED"
    assert state.total_steps == 3
    assert state.current_step == 3
    assert state.mode == "MOCK ONLY"
    assert len(orchestrator.last_records) == 3
    for record in orchestrator.last_records:
        assert record.status is ExecutionStepStatus.COMPLETED
        assert record.feedback is not None
        assert record.feedback.success is True


def test_state_machine_valid_transitions():
    assert (
        validate_transition(
            ExecutionStepStatus.CREATED,
            ExecutionStepStatus.VALIDATING,
        )
        is None
    )
    assert (
        validate_transition(
            ExecutionStepStatus.VALIDATING,
            ExecutionStepStatus.READY,
        )
        is None
    )
    assert (
        validate_transition(
            ExecutionStepStatus.READY,
            ExecutionStepStatus.RUNNING,
        )
        is None
    )
    assert (
        validate_transition(
            ExecutionStepStatus.RUNNING,
            ExecutionStepStatus.WAITING_OBSERVATION,
        )
        is None
    )
    assert (
        validate_transition(
            ExecutionStepStatus.WAITING_OBSERVATION,
            ExecutionStepStatus.COMPLETED,
        )
        is None
    )
    # retry: FAILED -> READY 允许
    assert (
        validate_transition(
            ExecutionStepStatus.FAILED,
            ExecutionStepStatus.READY,
        )
        is None
    )


def test_state_machine_illegal_transitions():
    with pytest.raises(IllegalTransitionError):
        validate_transition(
            ExecutionStepStatus.FAILED,
            ExecutionStepStatus.RUNNING,
        )
    with pytest.raises(IllegalTransitionError):
        validate_transition(
            ExecutionStepStatus.COMPLETED,
            ExecutionStepStatus.RUNNING,
        )
    with pytest.raises(IllegalTransitionError):
        validate_transition(
            ExecutionStepStatus.BLOCKED,
            ExecutionStepStatus.READY,
        )


def test_safety_gate_reject():
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(
        _plan(action="ATTACK"),
        trace_id="trace-safety",
    )
    assert state.status == "BLOCKED"
    assert state.current_step == 1
    first = orchestrator.last_records[0]
    assert first.status is ExecutionStepStatus.BLOCKED
    assert first.safety is not None
    assert first.safety.allowed is False


def test_mock_only_results():
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(_plan(), trace_id="trace-mock")
    assert state.mode == "MOCK ONLY"
    for record in orchestrator.last_records:
        assert record.result is not None
        assert record.result.status is ExecutionStatus.COMPLETED
        assert record.result.message == "mock execution only"
        assert record.feedback is not None
        assert record.feedback.reason == "mock observation"


def test_empty_plan_blocked():
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(_plan(steps=0), trace_id="trace-empty")
    assert state.status == "BLOCKED"
    assert "空 ActionPlan" in state.last_result
    assert state.total_steps == 0
    assert orchestrator.last_records == []


def test_missing_target_blocked():
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(_plan(target=""), trace_id="trace-notarget")
    assert state.status == "BLOCKED"
    assert state.last_result == "缺少 target"
    assert orchestrator.last_records[0].status is ExecutionStepStatus.BLOCKED


def test_executor_failure_retry_recovers():
    flaky = FlakyExecutor()
    orchestrator = ExecutionOrchestrator(executor=flaky)
    state = orchestrator.run(_plan(steps=1), trace_id="trace-flaky")
    assert state.status == "COMPLETED"
    record = orchestrator.last_records[0]
    assert record.task.retry_count == 1
    assert record.status is ExecutionStepStatus.COMPLETED
    assert flaky.calls == 2


def test_executor_failure_exhausted():
    orchestrator = ExecutionOrchestrator(executor=AlwaysFailExecutor())
    state = orchestrator.run(_plan(steps=1), trace_id="trace-fail")
    assert state.status == "FAILED"
    record = orchestrator.last_records[0]
    assert record.status is ExecutionStepStatus.FAILED
    assert record.task.retry_count == 1
    assert record.result is not None
    assert record.result.message == "always fail"


def test_replay_generation(tmp_path):
    orchestrator = ExecutionOrchestrator(sessions_dir=tmp_path)
    orchestrator.run(_plan(), trace_id="trace-replay")
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "execution_orchestration.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["trace_id"] == "trace-replay"
    assert replay["plan_id"] == "plan-1"
    assert len(replay["steps"]) == 3
    first = replay["steps"][0]
    assert first["task"]["action"] == "TALK"
    assert first["task"]["target"] == "赫丽娜"
    assert first["task"]["step_index"] == 1
    assert first["status"] == "COMPLETED"
    assert first["result"]["mode"] == "MOCK_ONLY"
    assert first["safety"]["allowed"] is True
    assert first["transitions"]
    assert replay["feedback"][0]["success"] is True
    assert replay["feedback"][0]["reason"] == "mock observation"
    assert replay["state"]["status"] == "COMPLETED"


def test_webui_execution_orchestration_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    orchestrator = ExecutionOrchestrator()
    state = orchestrator.run(_plan(), trace_id="trace-webui")
    payload = {
        "plan": "TALK 赫丽娜",
        "state": state.model_dump(mode="json"),
    }
    app = create_app(
        runtime=runtime,
        bus=bus,
        execution_orchestration=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/execution/orchestration/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["plan"] == "TALK 赫丽娜"
    assert data["state"]["status"] == "COMPLETED"
    assert data["state"]["current_step"] == 3


def test_webui_execution_orchestration_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/execution/orchestration/state")
    assert resp.json()["enabled"] is False
