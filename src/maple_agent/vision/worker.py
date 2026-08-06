"""Vision Worker:内部采集循环与状态机(STOPPED / IDLE / CAPTURING / ERROR)。"""

from __future__ import annotations

import asyncio
import json
import logging
from enum import StrEnum
from typing import TYPE_CHECKING

from PIL import Image

from maple_agent.events import Event, EventBus, EventType
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.ocr import OCRProvider, OCRRequest, OCRResult
from maple_agent.vision.capture import CaptureProvider
from maple_agent.vision.models import (
    Observation,
    ObservationRef,
    ScreenFrame,
    VisionState,
)

if TYPE_CHECKING:
    from maple_agent.fusion import FusionService
    from maple_agent.fusion.models import WorldState

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
        ocr: OCRProvider | None = None,
        fusion: FusionService | None = None,
    ) -> None:
        self.capture = capture
        self.bus = bus
        self.ocr = ocr
        self.fusion = fusion
        self.interval = interval
        self.retry_delay = retry_delay
        self._state = VisionWorkerState.STOPPED
        self._task: asyncio.Task[None] | None = None
        self.latest_frame: ScreenFrame | None = None
        self.latest_ocr: list[OCRResult] = []
        self.latest_vision: VisionState | None = None
        self.latest_world: WorldState | None = None
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
                frame, image = self.capture.capture_with_image(trace_id=trace.trace_id)
            except Exception:
                self._state = VisionWorkerState.ERROR
                logger.error("vision tick failed")
                raise
            self.latest_frame = frame
            self.capture_count += 1
            observations: list[Observation] = []
            ocr_results: list[OCRResult] = []
            world: WorldState | None = None
            if self.ocr is not None:
                ocr_path = self._ensure_ocr_image(image, frame)
                result = self.ocr.recognize(
                    OCRRequest(image_path=ocr_path),
                    trace_id=frame.trace_id,
                )
                ocr_results = [result]
                self.latest_ocr = ocr_results
                observations = [
                    Observation(
                        element="ocr_text",
                        type="text",
                        raw_value=result.text,
                        normalized_value=result.text,
                        confidence=result.confidence,
                        source=result.source,
                    )
                ]
            if self.fusion is not None and observations:
                world = self.fusion.fuse(observations, trace_id=frame.trace_id)
                self.latest_world = world
            state = VisionState(
                frame_id=frame.frame_id,
                trace_id=frame.trace_id,
                map_name=world.current_map.name if world and world.current_map else None,
                map_id=world.current_map.map_id if world and world.current_map else None,
                region=world.current_map.region if world and world.current_map else "",
                map_confidence=world.confidence if world else None,
                summary="OCR " + (" | ".join(r.text for r in ocr_results))
                if ocr_results
                else f"frame captured {frame.width}x{frame.height}",
                observation_refs=[
                    ObservationRef(
                        element=item.element,
                        normalized_value=item.normalized_value,
                        confidence=item.confidence,
                    )
                    for item in observations
                ],
            )
            self.latest_vision = state
            self._write_replay(frame, observations, state, world)
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

    def _ensure_ocr_image(self, image: Image.Image, frame: ScreenFrame) -> str:
        if frame.image_path:
            return frame.image_path
        directory = self.capture.sessions_dir / frame.trace_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "ocr_input.png"
        image.convert("RGB").save(path, "PNG")
        return str(path)

    def _write_replay(
        self,
        frame: ScreenFrame,
        observations: list[Observation],
        state: VisionState,
        world: WorldState | None,
    ) -> None:
        directory = self.capture.sessions_dir / frame.trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "frame": frame.model_dump(mode="json"),
            "observations": [item.model_dump(mode="json") for item in observations],
            "vision_state": state.model_dump(mode="json"),
            "world_state": world.model_dump(mode="json") if world is not None else None,
        }
        (directory / "vision.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

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
