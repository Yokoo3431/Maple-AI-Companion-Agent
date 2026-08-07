"""SafetyGate:动作白名单 + 物理动作关键字拦截 + 只读模拟约束。"""

from __future__ import annotations

import logging

from maple_agent.executor.models import ExecutionTask, SafetyResult
from maple_agent.logging_setup import TraceContext

logger = logging.getLogger("maple_agent.executor")

_PHYSICAL_KEYWORDS = (
    "click",
    "mouse",
    "key",
    "input",
    "send",
    "execute",
)

_DEFAULT_ALLOWED_ACTIONS = frozenset(
    {
        "ANALYZE",
        "MOVE_HINT",
        "TALK",
        "COLLECT",
        "DEFEAT",
        "DELIVER",
        "COMPLETE",
        "OBSERVE",
        "WAIT",
        "PAUSE",
        "QUERY_KNOWLEDGE",
    }
)


class SafetyGate:
    """检查任务是否允许执行;默认只读模拟模式。"""

    def __init__(self, allowed_actions: set[str] | None = None) -> None:
        self.allowed_actions = frozenset(allowed_actions or _DEFAULT_ALLOWED_ACTIONS)
        self.mode = "mock_only"

    def check(
        self,
        task: ExecutionTask,
        *,
        trace_id: str | None = None,
    ) -> SafetyResult:
        with TraceContext(trace_id=trace_id):
            text = f"{task.action} {task.target}".lower()
            for keyword in _PHYSICAL_KEYWORDS:
                if keyword in text:
                    return SafetyResult(
                        allowed=False,
                        reason=f"物理动作关键字: {keyword}",
                        mode=self.mode,
                    )
            if task.action.upper() not in self.allowed_actions:
                return SafetyResult(
                    allowed=False,
                    reason=f"动作不允许: {task.action}",
                    mode=self.mode,
                )
            logger.info("safety gate: allowed action=%s", task.action)
            return SafetyResult(allowed=True, mode=self.mode)
