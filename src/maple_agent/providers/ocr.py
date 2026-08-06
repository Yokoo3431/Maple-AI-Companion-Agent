"""OCR Provider 契约与实现:Mock / Windows OCR(baseline)/ Tesseract(fallback)(Phase 1.2)。"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from abc import abstractmethod
from pathlib import Path
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, Field

from maple_agent.events import EventBus, EventType
from maple_agent.providers.base import BaseProvider, ProviderError


class OCRRequest(BaseModel):
    """OCR 请求。"""

    image_path: str = ""
    language: str = "zh-Hans-CN"


class OCRBBox(BaseModel):
    """识别文本的边界框。"""

    left: int
    top: int
    width: int
    height: int


class OCRResult(BaseModel):
    """OCR 识别结果。"""

    text: str
    bbox: OCRBBox
    confidence: float = Field(ge=0, le=1)
    source: str = "unknown"
    schema_version: str = "1.0"
    trace_id: str = ""


@runtime_checkable
class OCRProviderProtocol(Protocol):
    """OCR Provider 调用契约。"""

    def recognize(
        self, request: OCRRequest, *, trace_id: str | None = None
    ) -> OCRResult: ...


class OCRProvider(BaseProvider):
    """OCR Provider 抽象(复用 BaseProvider 生命周期)。"""

    def __init__(self, *, bus: EventBus | None = None, source: str = "ocr") -> None:
        super().__init__(
            name=source,
            logger_name="maple_agent.vision.ocr",
            bus=bus,
        )

    def recognize(
        self, request: OCRRequest, *, trace_id: str | None = None
    ) -> OCRResult:
        return self._run_call(
            trace_id,
            success_event=EventType.OCR_COMPLETED,
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
        bbox: OCRBBox | None = None,
        raise_on_call: bool = False,
        source: str = "ocr",
    ) -> None:
        super().__init__(bus=bus, source=source)
        self._text = text
        self._confidence = confidence
        self._bbox = bbox or OCRBBox(left=0, top=0, width=200, height=40)
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def _recognize(self, request: OCRRequest, tid: str) -> OCRResult:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock ocr failure")
        return OCRResult(
            text=self._text,
            bbox=self._bbox,
            confidence=self._confidence,
            source="mock",
            schema_version="1.0",
            trace_id=tid,
        )


class WindowsOCRProvider(OCRProvider):
    """Windows 内置 OCR(WinRT,zh-Hans),Phase 1.2 baseline。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        language: str = "zh-Hans-CN",
        helper: str | Path | None = None,
    ) -> None:
        super().__init__(bus=bus, source="windows.ocr")
        self.language = language
        self.helper = (
            Path(helper)
            if helper
            else Path(__file__).resolve().parent / "windows_ocr_helper.ps1"
        )

    @staticmethod
    def is_supported() -> bool:
        return sys.platform == "win32"

    def _powershell(self) -> str:
        windir = os.environ.get("WINDIR", r"C:\Windows")
        return str(Path(windir) / "System32" / "WindowsPowerShell" / "v1.0" / "powershell.exe")

    def _recognize(self, request: OCRRequest, tid: str) -> OCRResult:
        if not self.is_supported():
            raise ProviderError("Windows OCR 仅支持 Windows")
        if not request.image_path:
            raise ProviderError("OCR 需要 image_path")
        image_path = Path(request.image_path)
        if not image_path.exists():
            raise ProviderError(f"图片不存在: {image_path}")
        proc = subprocess.run(
            [
                self._powershell(),
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(self.helper),
                "-ImagePath",
                str(image_path),
                "-Language",
                self.language,
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=90,
        )
        if proc.returncode != 0:
            detail = (proc.stderr or proc.stdout or "").strip()
            raise ProviderError(f"Windows OCR 失败: {detail[:400]}")
        try:
            data = json.loads(proc.stdout.strip())
        except json.JSONDecodeError as exc:
            raise ProviderError(f"Windows OCR 输出解析失败: {exc}") from exc
        bbox = data.get("bbox") or {"left": 0, "top": 0, "width": 0, "height": 0}
        return OCRResult(
            text=data.get("text", ""),
            bbox=OCRBBox(**bbox),
            confidence=float(data.get("confidence", 0.0)),
            source="windows.ocr",
            schema_version="1.0",
            trace_id=tid,
        )


class TesseractOCRProvider(OCRProvider):
    """Tesseract fallback(需系统安装 tesseract 与 pytesseract)。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        lang: str = "chi_sim+eng",
        tesseract_cmd: str | None = None,
    ) -> None:
        super().__init__(bus=bus, source="tesseract")
        self.lang = lang
        self._tesseract_cmd = tesseract_cmd or shutil.which("tesseract")

    def is_available(self) -> bool:
        return self._tesseract_cmd is not None and Path(self._tesseract_cmd).exists()

    def _recognize(self, request: OCRRequest, tid: str) -> OCRResult:
        if self._tesseract_cmd is None:
            raise ProviderError("未检测到 Tesseract;请安装或改用 Windows OCR")
        if not request.image_path or not Path(request.image_path).exists():
            raise ProviderError("OCR 需要存在的 image_path")
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise ProviderError("缺少 pytesseract 依赖") from exc
        pytesseract.pytesseract.tesseract_cmd = self._tesseract_cmd
        data = pytesseract.image_to_data(
            Image.open(request.image_path),
            lang=self.lang,
            output_type=pytesseract.Output.DICT,
        )
        words: list[str] = []
        confs: list[float] = []
        xs: list[int] = []
        ys: list[int] = []
        xe: list[int] = []
        ye: list[int] = []
        for index, word in enumerate(data.get("text", [])):
            conf = data.get("conf", [0])[index]
            if not word or not word.strip() or conf == -1:
                continue
            words.append(word.strip())
            confs.append(max(0.0, float(conf) / 100.0))
            xs.append(data["left"][index])
            ys.append(data["top"][index])
            xe.append(data["left"][index] + data["width"][index])
            ye.append(data["top"][index] + data["height"][index])
        left = min(xs) if xs else 0
        top = min(ys) if ys else 0
        right = max(xe) if xe else 0
        bottom = max(ye) if ye else 0
        confidence = sum(confs) / len(confs) if confs else 0.0
        return OCRResult(
            text=" ".join(words),
            bbox=OCRBBox(
                left=left,
                top=top,
                width=max(0, right - left),
                height=max(0, bottom - top),
            ),
            confidence=round(confidence, 4),
            source="tesseract",
            schema_version="1.0",
            trace_id=tid,
        )
