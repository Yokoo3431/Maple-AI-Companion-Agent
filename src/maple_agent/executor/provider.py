"""ExecutorProvider 契约:只定义 execute(task)。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from maple_agent.executor.models import ExecutionResult, ExecutionTask


@runtime_checkable
class ExecutorProvider(Protocol):
    """执行器契约(Phase 2-D:不允许真实执行)。"""

    def execute(self, task: ExecutionTask) -> ExecutionResult: ...
