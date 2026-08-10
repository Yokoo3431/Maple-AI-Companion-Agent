"""ReflectionMemory:反思状态记忆(供 AgentContext 挂载)。"""

from __future__ import annotations

from maple_agent.reflection.models import ReflectionResult, ReflectionState


class ReflectionMemory:
    """记录反思结果,维护 failure_history / retry_count / confidence。"""

    def __init__(self) -> None:
        self._state = ReflectionState()

    @property
    def state(self) -> ReflectionState:
        return self._state

    def record(self, result: ReflectionResult) -> None:
        if not result.success:
            self._state.failure_history.append(result)
            self._state.retry_count += 1
        self._state.last_reflection = result
        self._state.confidence = result.confidence

    def reset(self) -> None:
        self._state = ReflectionState()
