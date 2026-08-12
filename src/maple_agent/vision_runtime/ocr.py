"""OCRProvider 抽象 + Mock 实现(预留 Windows OCR / Tesseract / PaddleOCR)。"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from maple_agent.vision_runtime.models import OcrResult, VisionFrame


@runtime_checkable
class OCRProvider(Protocol):
    """OCR 提供者契约。"""

    def recognize(self, frame: VisionFrame) -> OcrResult: ...


class MockOCRProvider:
    """Mock 实现:直接返回配置文本。"""

    def __init__(
        self,
        *,
        text: str = "",
        confidence: float = 0.9,
        source: str = "mock",
    ) -> None:
        self.text = text
        self.confidence = confidence
        self.source = source
        self.call_count = 0

    def recognize(self, frame: VisionFrame) -> OcrResult:
        self.call_count += 1
        lines = [line.strip() for line in self.text.splitlines() if line.strip()]
        return OcrResult(
            text=self.text,
            lines=lines,
            confidence=self.confidence,
            source=self.source,
        )


# 预留适配器契约(本阶段不实现真实引擎):
# - WindowsOCRAdapter: 基于 Windows.Media.Ocr(需 WinRT 运行时)
# - TesseractOCRAdapter: 基于 pytesseract + tesseract 二进制
# - PaddleOCRAdapter: 基于 paddleocr 引擎
# 未来实现时必须保持 OCRProvider 协议,只替换 Mock。
