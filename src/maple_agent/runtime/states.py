"""Runtime 状态机:状态枚举 + 严格迁移表。"""

from __future__ import annotations

from enum import StrEnum


class RuntimeState(StrEnum):
    """Runtime 完整生命周期状态。"""

    OFFLINE = "OFFLINE"
    STARTING = "STARTING"
    READY = "READY"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    ERROR = "ERROR"


class IllegalTransitionError(RuntimeError):
    """非法状态跳转。"""


# 目标状态 -> 允许的源状态集合(严格迁移表,禁止非法跳转)
_TRANSITION_TABLE: dict[RuntimeState, frozenset[RuntimeState]] = {
    RuntimeState.STARTING: frozenset({RuntimeState.OFFLINE}),
    RuntimeState.READY: frozenset({RuntimeState.STARTING}),
    RuntimeState.RUNNING: frozenset({RuntimeState.READY, RuntimeState.PAUSED}),
    RuntimeState.PAUSED: frozenset({RuntimeState.RUNNING}),
    RuntimeState.STOPPING: frozenset(
        {
            RuntimeState.STARTING,
            RuntimeState.READY,
            RuntimeState.RUNNING,
            RuntimeState.PAUSED,
        }
    ),
    RuntimeState.OFFLINE: frozenset({RuntimeState.STOPPING, RuntimeState.ERROR}),
    RuntimeState.ERROR: frozenset(
        {
            RuntimeState.STARTING,
            RuntimeState.READY,
            RuntimeState.RUNNING,
            RuntimeState.PAUSED,
            RuntimeState.STOPPING,
        }
    ),
}


def validate_transition(current: RuntimeState, target: RuntimeState) -> None:
    """校验迁移;非法时抛 IllegalTransitionError,状态保持不变。"""
    allowed = _TRANSITION_TABLE.get(target, frozenset())
    if current not in allowed:
        raise IllegalTransitionError(f"非法状态跳转: {current.value} -> {target.value}")


def allowed_transitions() -> list[tuple[RuntimeState, RuntimeState]]:
    """返回全部合法迁移(供测试与文档使用)。"""
    return [
        (source, target)
        for target, sources in _TRANSITION_TABLE.items()
        for source in sorted(sources, key=lambda s: s.value)
    ]
