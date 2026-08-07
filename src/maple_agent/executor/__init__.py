"""Executor Contract Foundation(Phase 2-D):契约 + Safety Gate + Mock,不真实执行。"""

from maple_agent.executor.mock import MockExecutorProvider
from maple_agent.executor.models import (
    ExecutionResult,
    ExecutionStatus,
    ExecutionTask,
    SafetyResult,
)
from maple_agent.executor.provider import ExecutorProvider
from maple_agent.executor.safety import SafetyGate

__all__ = [
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionTask",
    "ExecutorProvider",
    "MockExecutorProvider",
    "SafetyGate",
    "SafetyResult",
]
