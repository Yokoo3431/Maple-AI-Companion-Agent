"""RealOCRProvider:真实 OCR backend 适配(可配置,失败安全降级)。"""

from __future__ import annotations

from maple_agent.vision_runtime.models import OcrResult, VisionFrame


class TesseractOCRAdapter:
    """Tesseract backend(需 pytesseract + tesseract 二进制)。"""

    def __init__(self, lang: str = "chi_sim") -> None:
        self.lang = lang
        self.available = False
        self._pytesseract = None
        try:
            import pytesseract  # type: ignore[import-not-found]

            self._pytesseract = pytesseract
            self.available = True
        except ImportError:
            self.available = False

    def recognize(self, frame: VisionFrame) -> OcrResult:
        if not self.available:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="tesseract-unavailable",
            )
        return OcrResult(
            text="",
            lines=[],
            confidence=0.0,
            source="tesseract-bridge-not-implemented",
        )


class WindowsOCRAdapter:
    """Windows OCR backend(需 WinRT 运行时)。"""

    def __init__(self, language: str = "zh-Hans-CN") -> None:
        self.language = language
        self.available = False
        try:
            import winrt  # type: ignore[import-not-found]

            self._winrt = winrt
            self.available = True
        except ImportError:
            self.available = False

    def recognize(self, frame: VisionFrame) -> OcrResult:
        if not self.available:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="windows-ocr-unavailable",
            )
        return OcrResult(
            text="",
            lines=[],
            confidence=0.0,
            source="windows-ocr-bridge-not-implemented",
        )


class RealOCRProvider:
    """可配置 OCR Provider,auto 优先 Windows OCR -> Tesseract。"""

    def __init__(self, backend: str = "auto") -> None:
        self.backend_name = "none"
        self._backend = None
        if backend in ("auto", "windows"):
            candidate = WindowsOCRAdapter()
            if candidate.available:
                self._backend = candidate
                self.backend_name = "windows"
        if self._backend is None and backend in ("auto", "tesseract"):
            candidate = TesseractOCRAdapter()
            if candidate.available:
                self._backend = candidate
                self.backend_name = "tesseract"
        self.available = self._backend is not None
        self.call_count = 0

    def recognize(self, frame: VisionFrame) -> OcrResult:
        self.call_count += 1
        if not self.available or self._backend is None:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="ocr-unavailable",
            )
        return self._backend.recognize(frame)
