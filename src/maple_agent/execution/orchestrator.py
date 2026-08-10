"""ExecutionOrchestrator:ActionPlan → Task → Safety → Mock 执行 → Feedback(只读)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.action_plan.models import ActionPlan
from maple_agent.execution.feedback import build_mock_feedback
from maple_agent.execution.models import (
    ExecutionOrchestrationState,
    ExecutionStepRecord,
)
from maple_agent.execution.state_machine import (
    ExecutionStepStateMachine,
    ExecutionStepStatus,
)
from maple_agent.executor.mock import MockExecutorProvider
from maple_agent.executor.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
)
from maple_agent.executor.provider import ExecutorProvider
from maple_agent.executor.safety import SafetyGate
from maple_agent.logging_setup import TraceContext, new_id

logger = logging.getLogger("maple_agent.execution")


class ExecutionOrchestrator:
    """把 ActionPlan 展开为 ExecutionTask 并按步骤执行(Mock Only)。"""

    def __init__(
        self,
        *,
        executor: ExecutorProvider | None = None,
        safety_gate: SafetyGate | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.safety_gate = safety_gate or SafetyGate()
        self.executor = executor or MockExecutorProvider(self.safety_gate)
        self.sessions_dir = Path(sessions_dir)
        self.machine = ExecutionStepStateMachine()
        self.state: ExecutionOrchestrationState | None = None
        self.last_records: list[ExecutionStepRecord] = []

    def run(
        self,
        plan: ActionPlan,
        *,
        trace_id: str | None = None,
    ) -> ExecutionOrchestrationState:
        """顺序编排 ActionPlan 的每个步骤(仅 Mock 执行)。"""
        with TraceContext(trace_id=trace_id) as trace:
            tid = trace.trace_id
            if not plan.steps:
                self.state = ExecutionOrchestrationState(
                    plan_id=plan.plan_id,
                    total_steps=0,
                    current_step=0,
                    status="BLOCKED",
                    mode="MOCK ONLY",
                    last_result="空 ActionPlan: 无执行步骤",
                    trace_id=tid,
                )
                self.last_records = []
                self._write_replay(plan, [], tid)
                return self.state

            records: list[ExecutionStepRecord] = []
            stopped = False
            for index, step in enumerate(plan.steps):
                task = ExecutionTask(
                    execution_id=new_id(),
                    plan_id=plan.plan_id,
                    step_id=step.step_id,
                    step_index=index + 1,
                    action=plan.action,
                    target=plan.target,
                    required_observation=step.required_observation,
                    success_condition=step.success_condition,
                    max_retry=1,
                    trace_id=tid,
                )
                record = self._execute_task(task, tid)
                records.append(record)
                if record.status in (
                    ExecutionStepStatus.BLOCKED,
                    ExecutionStepStatus.FAILED,
                ):
                    stopped = True
                    break

            if stopped:
                last = records[-1]
                status = (
                    "BLOCKED"
                    if last.status is ExecutionStepStatus.BLOCKED
                    else "FAILED"
                )
                message = (
                    last.result.message
                    if last.result is not None
                    else last.status.value
                )
            else:
                status = "COMPLETED"
                message = (
                    records[-1].result.message
                    if records and records[-1].result is not None
                    else ""
                )
            self.state = ExecutionOrchestrationState(
                plan_id=plan.plan_id,
                total_steps=len(plan.steps),
                current_step=len(records),
                status=status,
                mode="MOCK ONLY",
                last_result=message,
                trace_id=tid,
            )
            self.last_records = records
            self._write_replay(plan, records, tid)
            logger.info(
                "orchestration: plan=%s status=%s steps=%d",
                plan.plan_id,
                status,
                len(records),
            )
            return self.state

    def _execute_task(
        self,
        task: ExecutionTask,
        tid: str,
    ) -> ExecutionStepRecord:
        """单个步骤:状态机推进 + SafetyGate + Mock 执行 + Feedback。"""
        current = ExecutionStepStatus.CREATED
        transitions: list[dict] = []

        def go(target: ExecutionStepStatus) -> None:
            nonlocal current
            self.machine.transition(current, target)
            transitions.append({"from": current.value, "to": target.value})
            current = target

        go(ExecutionStepStatus.VALIDATING)
        if not task.target:
            go(ExecutionStepStatus.BLOCKED)
            task.status = ExecutionStatus.BLOCKED
            result = ExecutionResult(
                execution_id=task.execution_id,
                status=ExecutionStatus.BLOCKED,
                message="缺少 target",
                trace_id=tid,
            )
            return ExecutionStepRecord(
                step_id=task.step_id,
                step_index=task.step_index,
                task=task,
                status=current,
                transitions=transitions,
                result=result,
            )

        safety = self.safety_gate.check(task, trace_id=tid)
        if not safety.allowed:
            go(ExecutionStepStatus.BLOCKED)
            task.status = ExecutionStatus.BLOCKED
            result = ExecutionResult(
                execution_id=task.execution_id,
                status=ExecutionStatus.BLOCKED,
                message=safety.reason,
                trace_id=tid,
            )
            return ExecutionStepRecord(
                step_id=task.step_id,
                step_index=task.step_index,
                task=task,
                status=current,
                safety=safety,
                transitions=transitions,
                result=result,
            )

        go(ExecutionStepStatus.READY)
        go(ExecutionStepStatus.RUNNING)
        while True:
            try:
                result = self.executor.execute(task)
            except Exception as exc:
                result = ExecutionResult(
                    execution_id=task.execution_id,
                    status=ExecutionStatus.FAILED,
                    message=str(exc),
                    trace_id=tid,
                )
            if result.status is ExecutionStatus.FAILED:
                if task.retry_count < task.max_retry:
                    task.retry_count += 1
                    go(ExecutionStepStatus.FAILED)
                    go(ExecutionStepStatus.READY)
                    go(ExecutionStepStatus.RUNNING)
                    logger.warning(
                        "execution retry: task=%s attempt=%d",
                        task.execution_id,
                        task.retry_count,
                    )
                    continue
                go(ExecutionStepStatus.FAILED)
                task.status = ExecutionStatus.FAILED
                return ExecutionStepRecord(
                    step_id=task.step_id,
                    step_index=task.step_index,
                    task=task,
                    status=current,
                    safety=safety,
                    transitions=transitions,
                    result=result,
                )
            if result.status is ExecutionStatus.BLOCKED:
                go(ExecutionStepStatus.BLOCKED)
                task.status = ExecutionStatus.BLOCKED
                return ExecutionStepRecord(
                    step_id=task.step_id,
                    step_index=task.step_index,
                    task=task,
                    status=current,
                    safety=safety,
                    transitions=transitions,
                    result=result,
                )
            break

        # 成功:模拟执行后重新观察世界 → Feedback → COMPLETED
        go(ExecutionStepStatus.WAITING_OBSERVATION)
        feedback = build_mock_feedback(task, result)
        go(feedback.next_state)
        task.status = ExecutionStatus.COMPLETED
        logger.info(
            "execution feedback: task=%s success=%s reason=%s",
            task.execution_id,
            feedback.success,
            feedback.reason,
        )
        return ExecutionStepRecord(
            step_id=task.step_id,
            step_index=task.step_index,
            task=task,
            status=current,
            safety=safety,
            transitions=transitions,
            result=result,
            feedback=feedback,
        )

    def _write_replay(
        self,
        plan: ActionPlan,
        records: list[ExecutionStepRecord],
        trace_id: str,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "plan_id": plan.plan_id,
            "plan": {
                "action": plan.action,
                "target": plan.target,
                "steps": len(plan.steps),
            },
            "steps": [
                {
                    "step_id": record.step_id,
                    "step_index": record.step_index,
                    "task": record.task.model_dump(mode="json"),
                    "safety": (
                        record.safety.model_dump(mode="json")
                        if record.safety is not None
                        else None
                    ),
                    "transitions": record.transitions,
                    "status": record.status.value,
                    "result": (
                        {
                            **record.result.model_dump(mode="json"),
                            "mode": "MOCK_ONLY",
                        }
                        if record.result is not None
                        else None
                    ),
                    "feedback": (
                        record.feedback.model_dump(mode="json")
                        if record.feedback is not None
                        else None
                    ),
                }
                for record in records
            ],
            "feedback": [
                record.feedback.model_dump(mode="json")
                for record in records
                if record.feedback is not None
            ],
            "state": (
                self.state.model_dump(mode="json")
                if self.state is not None
                else None
            ),
        }
        (directory / "execution_orchestration.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
