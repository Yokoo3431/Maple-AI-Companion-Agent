"""OCR Provider 契约与 Mock(Phase 0 不执行真实 OCR)。"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from maple_agent.events import EventBus, EventType
from maple_agent.providers.base import BaseProvider, ProviderError


class OCRRequest(BaseModel):
    """OCR 请求(Phase 0 仅契约,不读取图片)。"""

    image_path: str = ""


class OCRResult(BaseModel):
    """OCR 识别结果。"""

    text: str
    confidence: float
    engine: str
    trace_id: str = ""


@runtime_checkable
class OCRProviderProtocol(Protocol):
    """OCR Provider 调用契约。"""

    def recognize(
        self, request: OCRRequest, *, trace_id: str | None = None
    ) -> OCRResult: ...


class OCRProvider(BaseProvider):
    """OCR Provider 抽象(未来可接 Tesseract / Windows OCR / PaddleOCR)。"""

    def __init__(self, *, bus: EventBus | None = None) -> None:
        super().__init__(
            name="ocr",
            logger_name="maple_agent.vision.ocr",
            bus=bus,
        )

    def recognize(
        self, request: OCRRequest, *, trace_id: str | None = None
    ) -> OCRResult:
        return self._run_call(
            trace_id,
            success_event=EventType.SCREEN_UPDATED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._recognize(request, tid),
        )

    @abstractmethod
    def _recognize(self, request: OCRRequest, tid: str) -> OCRResult: ...


class MockOCRProvider(OCRProvider):
    """Mock 实现:固定文本与置信度;可配置失败。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        text: str = "射手村",
        confidence: float = 0.95,
        raise_on_call: bool = False,
    ) -> None:
        super().__init__(bus=bus)
        self._text = text
        self._confidence = confidence
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def _recognize(self, request: OCRRequest, tid: str) -> OCRResult:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock ocr failure")
        return OCRResult(
            text=self._text,
            confidence=self._confidence,
            engine="mock",
            trace_id=tid,
        )
