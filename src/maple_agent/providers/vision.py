"""Vision Provider 契约与 Mock(Phase 0 不做截图分析)。"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from maple_agent.events import EventBus, EventType
from maple_agent.providers.base import BaseProvider, ProviderError


class VisionResult(BaseModel):
    """画面状态识别结果(Phase 0 由 Mock 提供)。"""

    hp: int
    mp: int
    map_name: str
    frame_id: str
    trace_id: str = ""


@runtime_checkable
class VisionProviderProtocol(Protocol):
    """Vision Provider 调用契约。"""

    def capture_state(self, *, trace_id: str | None = None) -> VisionResult: ...


class VisionProvider(BaseProvider):
    """Vision Provider 抽象(未来接截图 / OpenCV / OCR 组合)。"""

    def __init__(self, *, bus: EventBus | None = None) -> None:
        super().__init__(
            name="vision",
            logger_name="maple_agent.vision.capture",
            bus=bus,
        )

    def capture_state(self, *, trace_id: str | None = None) -> VisionResult:
        return self._run_call(
            trace_id,
            success_event=EventType.SCREEN_UPDATED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._capture_state(tid),
        )

    @abstractmethod
    def _capture_state(self, tid: str) -> VisionResult: ...


class MockVisionProvider(VisionProvider):
    """Mock 实现:固定画面状态;可配置失败。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        result: VisionResult | None = None,
        raise_on_call: bool = False,
    ) -> None:
        super().__init__(bus=bus)
        self._result = result
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def _capture_state(self, tid: str) -> VisionResult:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock vision failure")
        base = self._result or VisionResult(
            hp=1000,
            mp=500,
            map_name="射手村",
            frame_id="mock-frame",
        )
        return base.model_copy(update={"trace_id": tid})
