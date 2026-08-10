"""ExecutionStep 状态机(Phase 5-C):严格转换限制,禁止非法跳转。"""

from __future__ import annotations

from enum import StrEnum


class ExecutionStepStatus(StrEnum):
    """执行步骤生命周期状态。"""

    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    RUNNING = "RUNNING"
    WAITING_OBSERVATION = "WAITING_OBSERVATION"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class IllegalTransitionError(RuntimeError):
    """非法状态转换。"""


# target -> 允许的来源状态集合
_TRANSITION_TABLE: dict[ExecutionStepStatus, frozenset[ExecutionStepStatus]] = {
    ExecutionStepStatus.VALIDATING: frozenset(
        {ExecutionStepStatus.CREATED}
    ),
    ExecutionStepStatus.READY: frozenset(
        {ExecutionStepStatus.VALIDATING, ExecutionStepStatus.FAILED}
    ),
    ExecutionStepStatus.RUNNING: frozenset(
        {
            ExecutionStepStatus.READY,
            ExecutionStepStatus.WAITING_OBSERVATION,
        }
    ),
    ExecutionStepStatus.WAITING_OBSERVATION: frozenset(
        {ExecutionStepStatus.RUNNING}
    ),
    ExecutionStepStatus.COMPLETED: frozenset(
        {ExecutionStepStatus.WAITING_OBSERVATION}
    ),
    # FAILED 仅允许回到 READY(retry),禁止直接 FAILED -> RUNNING
    ExecutionStepStatus.FAILED: frozenset(
        {
            ExecutionStepStatus.RUNNING,
            ExecutionStepStatus.WAITING_OBSERVATION,
        }
    ),
    ExecutionStepStatus.BLOCKED: frozenset(
        {
            ExecutionStepStatus.CREATED,
            ExecutionStepStatus.VALIDATING,
            ExecutionStepStatus.READY,
            ExecutionStepStatus.RUNNING,
        }
    ),
}


def validate_transition(
    current: ExecutionStepStatus,
    target: ExecutionStepStatus,
) -> None:
    """校验状态转换;非法抛出 IllegalTransitionError。"""
    allowed = _TRANSITION_TABLE.get(target, frozenset())
    if current not in allowed:
        raise IllegalTransitionError(
            f"非法状态转换: {current.value} -> {target.value}"
        )


class ExecutionStepStateMachine:
    """执行步骤状态机(纯校验,无副作用)。"""

    def transition(
        self,
        current: ExecutionStepStatus,
        target: ExecutionStepStatus,
    ) -> ExecutionStepStatus:
        validate_transition(current, target)
        return target
