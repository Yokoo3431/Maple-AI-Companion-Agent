"""Provider 抽象基类:统一生命周期、trace、日志、Event Bus 集成。"""

from __future__ import annotations

import logging
from abc import ABC
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import BaseModel

from maple_agent.events import Event, EventBus, EventType
from maple_agent.logging_setup import TraceContext, new_id


class ProviderStatus(StrEnum):
    """Provider 生命周期状态。"""

    CREATED = "CREATED"
    INITIALIZED = "INITIALIZED"
    SHUTDOWN = "SHUTDOWN"


class ProviderError(RuntimeError):
    """Provider 调用 / 生命周期异常。"""


class ErrorPayload(BaseModel):
    """失败事件负载。"""

    provider: str
    message: str


@runtime_checkable
class ProviderProtocol(Protocol):
    """Provider 生命周期契约(结构化类型检查)。"""

    @property
    def status(self) -> ProviderStatus: ...

    def initialize(self, *, trace_id: str | None = None) -> None: ...

    def shutdown(self, *, trace_id: str | None = None) -> None: ...


class BaseProvider(ABC):
    """Provider 抽象基类:生命周期门控 + trace + 日志 + Event Bus 事件。"""

    def __init__(
        self,
        *,
        name: str,
        logger_name: str,
        bus: EventBus | None = None,
    ) -> None:
        self.name = name
        self.bus = bus
        self._status = ProviderStatus.CREATED
        self._logger = logging.getLogger(logger_name)

    @property
    def status(self) -> ProviderStatus:
        return self._status

    def initialize(self, *, trace_id: str | None = None) -> None:
        """CREATED -> INITIALIZED。"""
        if self._status is not ProviderStatus.CREATED:
            raise ProviderError(
                f"{self.name}: 当前状态 {self._status.value},不能重复 initialize"
            )
        self._status = ProviderStatus.INITIALIZED
        with self._trace(trace_id):
            self._logger.info("provider initialized: %s", self.name)

    def shutdown(self, *, trace_id: str | None = None) -> None:
        """INITIALIZED -> SHUTDOWN。"""
        if self._status is not ProviderStatus.INITIALIZED:
            raise ProviderError(
                f"{self.name}: 当前状态 {self._status.value},不能 shutdown"
            )
        self._status = ProviderStatus.SHUTDOWN
        with self._trace(trace_id):
            self._logger.info("provider shutdown: %s", self.name)

    def _require_initialized(self) -> None:
        if self._status is not ProviderStatus.INITIALIZED:
            raise ProviderError(f"{self.name}: provider 未初始化")

    @contextmanager
    def _trace(self, trace_id: str | None) -> Iterator[str]:
        """解析/生成 trace_id 并恢复日志追踪上下文。"""
        resolved = trace_id or TraceContext.current()[0] or new_id()
        with TraceContext(trace_id=resolved):
            yield resolved

    def _run_call(
        self,
        trace_id: str | None,
        *,
        success_event: EventType,
        failure_event: EventType,
        fn: Callable[[str], Any],
    ) -> Any:
        """统一调用包装:门控 -> trace -> 日志 -> 成功/失败事件。"""
        self._require_initialized()
        with self._trace(trace_id) as tid:
            self._logger.info("provider call start: %s", self.name)
            try:
                result = fn(tid)
                self._logger.info("provider call ok: %s", self.name)
                self._emit(
                    success_event,
                    payload=result if isinstance(result, BaseModel) else None,
                    trace_id=tid,
                )
                return result
            except Exception as exc:
                self._logger.error("provider call failed: %s: %s", self.name, exc)
                self._emit(
                    failure_event,
                    payload=ErrorPayload(provider=self.name, message=str(exc)),
                    trace_id=tid,
                )
                raise

    def _emit(
        self,
        event_type: EventType,
        payload: BaseModel | None,
        trace_id: str,
    ) -> None:
        """发布事件(未绑定 Bus 时跳过)。"""
        if self.bus is None:
            return
        event = Event.create(
            event_type,
            source=f"provider.{self.name}",
            payload=payload,
            trace_id=trace_id,
        )
        self.bus.publish(event)
