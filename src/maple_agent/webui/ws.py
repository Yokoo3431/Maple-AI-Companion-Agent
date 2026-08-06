"""WebSocket 管理器:向浏览器推送 runtime 事件 / error 事件 / 日志。"""

from __future__ import annotations

import asyncio
import logging
from collections import deque
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

from maple_agent.events import Event, EventBus
from maple_agent.logging_setup import TraceFormatter


class LogStreamHandler(logging.Handler):
    """把日志记录转发给 WebSocketManager。"""

    def __init__(self, manager: WebSocketManager) -> None:
        super().__init__()
        self.manager = manager

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.manager.push_log(self.format(record))
        except Exception:
            pass


class WebSocketManager:
    """广播 Event / 日志到所有连接的浏览器。"""

    def __init__(
        self,
        bus: EventBus,
        max_recent_events: int = 100,
        max_recent_logs: int = 200,
    ) -> None:
        self.bus = bus
        self._connections: dict[WebSocket, asyncio.Queue[dict[str, Any]]] = {}
        self._tasks: set[asyncio.Task[None]] = set()
        self._log_handler: LogStreamHandler | None = None
        self._attached = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self.recent_events: deque[Event] = deque(maxlen=max_recent_events)
        self.recent_logs: deque[str] = deque(maxlen=max_recent_logs)

    def attach(self) -> None:
        """订阅 Event Bus 并挂接日志转发(须在事件循环内调用)。"""
        if self._attached:
            return
        self._loop = asyncio.get_running_loop()
        self.bus.subscribe(self._on_event)
        self._log_handler = LogStreamHandler(self)
        self._log_handler.setFormatter(TraceFormatter())
        logging.getLogger().addHandler(self._log_handler)
        self._attached = True

    def detach(self) -> None:
        """移除日志转发并清空订阅。"""
        if not self._attached:
            return
        if self._log_handler is not None:
            logging.getLogger().removeHandler(self._log_handler)
            self._log_handler = None
        self._attached = False
        self._loop = None

    def _on_event(self, event: Event) -> None:
        self.recent_events.append(event)
        self._broadcast({"type": "event", "event": event.model_dump(mode="json")})

    def push_log(self, line: str) -> None:
        self.recent_logs.append(line)
        if (
            self._loop is not None
            and self._loop.is_running()
            and asyncio.get_running_loop() is not self._loop
        ):
            self._loop.call_soon_threadsafe(
                self._broadcast, {"type": "log", "line": line}
            )
        else:
            self._broadcast({"type": "log", "line": line})

    def _broadcast(self, message: dict[str, Any]) -> None:
        for queue in list(self._connections.values()):
            queue.put_nowait(message)

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._connections[websocket] = queue
        sender = asyncio.create_task(self._sender(websocket, queue))
        self._tasks.add(sender)
        try:
            while True:
                await websocket.receive_text()  # 仅用于感知连接存活
        except WebSocketDisconnect:
            pass
        finally:
            self._connections.pop(websocket, None)
            sender.cancel()
            self._tasks.discard(sender)

    async def _sender(self, websocket: WebSocket, queue: asyncio.Queue) -> None:
        while True:
            message = await queue.get()
            await websocket.send_json(message)
