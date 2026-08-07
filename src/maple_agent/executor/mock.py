"""MockExecutorProvider:收到任务不执行,仅返回 ExecutionResult(测试闭环)。"""

from __future__ import annotations

import logging

from maple_agent.executor.models import ExecutionResult, ExecutionStatus, ExecutionTask
from maple_agent.executor.safety import SafetyGate
from maple_agent.logging_setup import TraceContext

logger = logging.getLogger("maple_agent.executor")


class MockExecutorProvider:
    """Mock 实现:经 SafetyGate 检查后返回 COMPLETED / BLOCKED。"""

    def __init__(self, safety_gate: SafetyGate | None = None) -> None:
        self.safety_gate = safety_gate or SafetyGate()
        self.call_count = 0
        self.last_result: ExecutionResult | None = None

    def execute(self, task: ExecutionTask) -> ExecutionResult:
        self.call_count += 1
        safety = self.safety_gate.check(task, trace_id=task.trace_id)
        if not safety.allowed:
            result = ExecutionResult(
                execution_id=task.execution_id,
                status=ExecutionStatus.BLOCKED,
                message=safety.reason,
                trace_id=task.trace_id,
            )
            self.last_result = result
            return result
        with TraceContext(trace_id=task.trace_id):
            logger.info(
                "mock executor: task=%s action=%s",
                task.execution_id,
                task.action,
            )
        result = ExecutionResult(
            execution_id=task.execution_id,
            status=ExecutionStatus.COMPLETED,
            message="mock execution only",
            trace_id=task.trace_id,
        )
        self.last_result = result
        return result
