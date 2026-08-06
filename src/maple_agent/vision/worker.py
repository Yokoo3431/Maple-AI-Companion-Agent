"""Vision Worker:内部采集循环与状态机(STOPPED / IDLE / CAPTURING / ERROR)。"""

from __future__ import annotations

import asyncio
import logging
from enum import StrEnum

from maple_agent.events import Event, EventBus, EventType
from maple_agent.logging_setup import TraceContext
from maple_agent.vision.capture import CaptureProvider
from maple_agent.vision.models import ScreenFrame, VisionState

logger = logging.getLogger("maple_agent.vision.worker")


class VisionWorkerState(StrEnum):
    """Vision Worker 内部采集状态。"""

    STOPPED = "STOPPED"
    IDLE = "IDLE"
    CAPTURING = "CAPTURING"
    ERROR = "ERROR"


class VisionWorkerError(RuntimeError):
    """Worker 生命周期误用。"""


class VisionWorker:
    """Vision 采样 Worker。

    Runtime 负责总体生命周期;本 Worker 只负责内部采集状态。
    Phase 1.1 仅感知:截图 → ScreenFrame → EventBus,无 OCR / 输入 / 控制。
    """

    def __init__(
        self,
        capture: CaptureProvider,
        bus: EventBus,
        *,
        interval: float = 0.5,
        retry_delay: float = 1.0,
    ) -> None:
        self.capture = capture
        self.bus = bus
        self.interval = interval
        self.retry_delay = retry_delay
        self._state = VisionWorkerState.STOPPED
        self._task: asyncio.Task[None] | None = None
        self.latest_frame: ScreenFrame | None = None
        self.capture_count = 0

    @property
    def state(self) -> VisionWorkerState:
        return self._state

    @property
    def fps(self) -> float:
        return 1.0 / self.interval if self.interval > 0 else 0.0

    def start(self) -> None:
        """STOPPED -> IDLE,启动采样循环(须在事件循环内调用)。"""
        if self._state is not VisionWorkerState.STOPPED:
            raise VisionWorkerError(f"worker 状态 {self._state.value},不能 start")
        self._state = VisionWorkerState.IDLE
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        """任意状态 -> STOPPED。"""
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        self._state = VisionWorkerState.STOPPED

    async def tick(self) -> ScreenFrame | None:
        """执行一次采集循环(单帧;测试与手动触发用)。"""
        if self._state is VisionWorkerState.STOPPED:
            return None
        self._state = VisionWorkerState.CAPTURING
        with TraceContext.new() as trace:
            try:
                frame = self.capture.capture_frame(trace_id=trace.trace_id)
            except Exception:
                self._state = VisionWorkerState.ERROR
                logger.error("vision tick failed")
                raise
            self.latest_frame = frame
            self.capture_count += 1
            state = VisionState(
                frame_id=frame.frame_id,
                trace_id=frame.trace_id,
                summary=f"frame captured {frame.width}x{frame.height}",
            )
            self.bus.publish(
                Event.create(
                    EventType.SCREEN_UPDATED,
                    source="vision.worker",
                    payload=state,
                    trace_id=frame.trace_id,
                )
            )
        self._state = VisionWorkerState.IDLE
        return frame

    async def _loop(self) -> None:
        try:
            while True:
                await asyncio.sleep(self.interval)
                try:
                    await self.tick()
                except asyncio.CancelledError:
                    raise
                except Exception:
                    # tick 已置 ERROR;等待后自动恢复 IDLE
                    await asyncio.sleep(self.retry_delay)
                    if self._state is VisionWorkerState.ERROR:
                        self._state = VisionWorkerState.IDLE
        except asyncio.CancelledError:
            pass
        finally:
            self._state = VisionWorkerState.STOPPED
