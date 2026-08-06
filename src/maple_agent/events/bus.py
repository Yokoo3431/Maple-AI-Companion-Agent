"""进程内异步事件总线:优先级队列 + 订阅分发 + 日志 trace 集成。"""

from __future__ import annotations

import asyncio
import itertools
import logging
from collections import defaultdict
from collections.abc import Callable
from typing import Any, Protocol

from maple_agent.events.types import Event, EventType, priority_order

logger = logging.getLogger("maple_agent.events")

Subscriber = Callable[[Event], Any]


class Publisher(Protocol):
    """事件发布者抽象。"""

    def publish(self, event: Event) -> None: ...


class EventBus:
    """异步事件总线。

    Phase 0 范围:强类型 Event、发布/订阅、优先级队列、Mock 测试;
    不连接真实 Vision / Input / 游戏。

    用法:
        bus = EventBus()
        bus.subscribe(handler, event_type=EventType.HP_LOW)
        await bus.start()
        bus.publish(event)          # 同事件循环线程内调用
        await bus.wait_idle()
        await bus.stop()
    """

    def __init__(self, maxsize: int = 1000) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, int, Event]] = asyncio.PriorityQueue(
            maxsize
        )
        self._subscribers: dict[EventType, list[Subscriber]] = defaultdict(list)
        self._all_subscribers: list[Subscriber] = []
        self._seq = itertools.count()
        self._task: asyncio.Task[None] | None = None

    def subscribe(self, subscriber: Subscriber, event_type: EventType | None = None) -> None:
        """订阅指定类型事件;event_type 为 None 时订阅全部事件。"""
        if event_type is None:
            self._all_subscribers.append(subscriber)
        else:
            self._subscribers[event_type].append(subscriber)

    def publish(self, event: Event) -> None:
        """发布事件(同事件循环线程内调用)。"""
        from maple_agent.logging_setup import TraceContext  # 延迟导入,避免循环依赖

        # 队列按元组升序弹出,取负值让 CRITICAL 最先出队
        item = (-priority_order(event.priority), next(self._seq), event)
        self._queue.put_nowait(item)
        with TraceContext(trace_id=event.trace_id or None):
            logger.info(
                "event published: type=%s priority=%s trace=%s source=%s",
                event.event_type.value,
                event.priority.value,
                event.trace_id,
                event.source,
            )

    async def start(self) -> None:
        """启动后台分发任务。"""
        if self._task is None:
            self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        """停止后台分发任务。"""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def wait_idle(self) -> None:
        """等待队列清空且全部事件分发完成。"""
        await self._queue.join()

    async def _run(self) -> None:
        while True:
            _, _, event = await self._queue.get()
            try:
                await self._dispatch(event)
            finally:
                self._queue.task_done()

    async def _dispatch(self, event: Event) -> None:
        from maple_agent.logging_setup import TraceContext  # 延迟导入,避免循环依赖

        callbacks = list(self._subscribers.get(event.event_type, [])) + list(
            self._all_subscribers
        )
        with TraceContext(trace_id=event.trace_id or None):
            logger.debug(
                "event dispatch: type=%s subscribers=%d",
                event.event_type.value,
                len(callbacks),
            )
            for callback in callbacks:
                try:
                    result = callback(event)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception:
                    logger.exception(
                        "event subscriber failed: type=%s", event.event_type.value
                    )
