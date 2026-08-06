"""Runtime Manager:生命周期状态机 + Event Bus 消费者(Phase 0 仅生命周期)。"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from maple_agent.events import Event, EventBus, EventType
from maple_agent.events.types import Priority
from maple_agent.game.window import GameWindowDetector
from maple_agent.logging_setup import TraceContext
from maple_agent.runtime.states import RuntimeState, validate_transition

logger = logging.getLogger("maple_agent.runtime.manager")

_STATE_EVENTS: dict[RuntimeState, EventType] = {
    RuntimeState.STARTING: EventType.STARTING,
    RuntimeState.READY: EventType.READY,
    RuntimeState.RUNNING: EventType.RUNNING,
    RuntimeState.PAUSED: EventType.PAUSE,
    RuntimeState.STOPPING: EventType.STOPPING,
    RuntimeState.OFFLINE: EventType.STOPPED,
    RuntimeState.ERROR: EventType.ERROR_OCCURRED,
}


class RuntimeGateError(RuntimeError):
    """运行门控未通过(用户确认 / 窗口检测)。"""


@dataclass
class RuntimeManager:
    """Runtime 生命周期管理器。

    Phase 0 范围:仅生命周期管理;禁止游戏控制、输入执行、OCR、任务逻辑。
    """

    bus: EventBus
    source: str = "runtime.manager"
    _state: RuntimeState = field(default=RuntimeState.OFFLINE, init=False)
    _user_confirmed: bool = field(default=False, init=False)

    @property
    def state(self) -> RuntimeState:
        return self._state

    def attach(self) -> None:
        """作为 Event Bus 消费者订阅命令与异常事件。"""
        for event_type in (
            EventType.START,
            EventType.PAUSE,
            EventType.STOP,
            EventType.GAME_WINDOW_LOST,
        ):
            self.bus.subscribe(self._on_event, event_type=event_type)

    def confirm(self) -> None:
        """用户确认(进入 RUNNING 的门控之一)。"""
        self._user_confirmed = True
        logger.info("user confirmation accepted")

    def start(self, *, trace_id: str | None = None) -> None:
        """OFFLINE -> STARTING -> READY(Phase 0 同步完成启动装配)。"""
        self._transition(RuntimeState.STARTING, trace_id=trace_id)
        self._transition(RuntimeState.READY, trace_id=trace_id)

    def start_agent(
        self,
        *,
        trace_id: str | None = None,
        detector: GameWindowDetector | None = None,
    ) -> None:
        """READY -> RUNNING;需用户确认 + 目标窗口存在。"""
        self._require_running_gate(detector)
        self._transition(RuntimeState.RUNNING, trace_id=trace_id)

    def pause(self, *, trace_id: str | None = None, reason: str = "user") -> None:
        """RUNNING -> PAUSED。"""
        self._transition(RuntimeState.PAUSED, trace_id=trace_id, reason=reason)

    def resume(
        self,
        *,
        trace_id: str | None = None,
        detector: GameWindowDetector | None = None,
    ) -> None:
        """PAUSED -> RUNNING;重新校验门控。"""
        self._require_running_gate(detector)
        self._transition(RuntimeState.RUNNING, trace_id=trace_id)

    def stop(self, *, trace_id: str | None = None, reason: str = "user") -> None:
        """READY / RUNNING / PAUSED / STARTING -> STOPPING -> OFFLINE。"""
        self._transition(RuntimeState.STOPPING, trace_id=trace_id, reason=reason)
        self._transition(RuntimeState.OFFLINE, trace_id=trace_id)

    def fail(self, *, trace_id: str | None = None, reason: str = "unknown") -> None:
        """进入 ERROR(允许从多数运行状态)。"""
        self._transition(RuntimeState.ERROR, trace_id=trace_id, reason=reason)

    def reset(self, *, trace_id: str | None = None) -> None:
        """ERROR -> OFFLINE。"""
        self._transition(RuntimeState.OFFLINE, trace_id=trace_id, reason="recover")

    def _require_running_gate(self, detector: GameWindowDetector | None) -> None:
        if not self._user_confirmed:
            raise RuntimeGateError("用户未确认,禁止进入 RUNNING")
        if detector is not None and detector.find_window() is None:
            logger.warning("running gate failed: 目标游戏窗口不存在")
            raise RuntimeGateError("目标游戏窗口不存在")

    def _on_event(self, event: Event) -> None:
        if event.source == self.source:
            return  # 忽略自身发布的事件,防止自循环
        if event.event_type is EventType.START:
            self.start(trace_id=event.trace_id)
        elif event.event_type is EventType.PAUSE:
            self.pause(trace_id=event.trace_id, reason="command")
        elif event.event_type is EventType.STOP:
            self.stop(trace_id=event.trace_id, reason="command")
        elif event.event_type is EventType.GAME_WINDOW_LOST:
            if self._state is RuntimeState.RUNNING:
                self.pause(trace_id=event.trace_id, reason="window_lost")

    def _transition(
        self,
        target: RuntimeState,
        *,
        trace_id: str | None = None,
        reason: str = "",
    ) -> None:
        validate_transition(self._state, target)
        current = self._state
        self._state = target
        event = Event.create(
            _STATE_EVENTS[target],
            source=self.source,
            priority=Priority.CRITICAL if target is RuntimeState.ERROR else Priority.NORMAL,
            trace_id=trace_id,
        )
        with TraceContext(trace_id=event.trace_id):
            logger.info(
                "runtime state: %s -> %s reason=%s event=%s",
                current.value,
                target.value,
                reason,
                event.event_type.value,
            )
        self.bus.publish(event)
