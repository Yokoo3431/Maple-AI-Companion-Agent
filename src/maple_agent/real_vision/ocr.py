"""RealOCRProvider:真实 OCR backend 适配(可配置,失败安全降级)。"""

from __future__ import annotations

import os
import shutil
import statistics
from pathlib import Path

from maple_agent.vision_runtime.models import OcrResult, VisionFrame


def _default_tesseract_cmd() -> str:
    """定位 tesseract 二进制:环境变量 > PATH > 常见安装路径。"""
    configured = os.environ.get("TESSERACT_CMD", "").strip()
    if configured and Path(configured).is_file():
        return configured
    discovered = shutil.which("tesseract")
    if discovered:
        return discovered
    common = Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe")
    if common.is_file():
        return str(common)
    return ""


def _default_tessdata_dir() -> str:
    """定位 tessdata 目录:环境变量 > 常见安装路径。"""
    configured = os.environ.get("TESSDATA_PREFIX", "").strip()
    if configured and Path(configured).is_dir():
        configured_path = Path(configured)
        if (configured_path / "eng.traineddata").is_file():
            return str(configured_path)
        nested = configured_path / "tessdata"
        if (nested / "eng.traineddata").is_file():
            return str(nested)
    user_local = Path.home() / "AppData/Local/Tesseract-OCR/tessdata"
    if user_local.is_dir():
        return str(user_local)
    common = Path(r"C:\Program Files\Tesseract-OCR\tessdata")
    if common.is_dir():
        return str(common)
    return ""


class TesseractOCRAdapter:
    """Tesseract backend(需 pytesseract + tesseract 二进制,真实可运行)。"""

    def __init__(self, lang: str = "chi_sim+eng") -> None:
        self.lang = lang
        self.available = False
        self.version = ""
        self.languages: list[str] = []
        self._tesseract_cmd = ""
        self._tessdata_dir = ""
        self._pytesseract = None
        try:
            import pytesseract  # type: ignore[import-not-found]

            self._pytesseract = pytesseract
            command = _default_tesseract_cmd()
            if not command:
                self.available = False
                return
            self._tesseract_cmd = command
            pytesseract.pytesseract.tesseract_cmd = command
            self._tessdata_dir = _default_tessdata_dir()
            if self._tessdata_dir:
                os.environ["TESSDATA_PREFIX"] = self._tessdata_dir
            self.version = str(pytesseract.get_tesseract_version())
            self.languages = pytesseract.get_languages(config="")
            self.available = True
        except Exception:
            self.available = False

    def _config(self) -> str:
        if self._tessdata_dir:
            return f"--tessdata-dir {self._tessdata_dir}"
        return ""

    def capability(self) -> dict:
        """backend 能力探测:版本 / 语言包 / 中英文支持。"""
        languages = list(self.languages)
        return {
            "backend": "tesseract",
            "available": self.available,
            "version": self.version,
            "languages": languages,
            "chinese_support": "chi_sim" in languages,
            "english_support": "eng" in languages,
            "tesseract_cmd": self._tesseract_cmd,
            "tessdata_dir": self._tessdata_dir,
        }

    def recognize(self, frame: VisionFrame) -> OcrResult:
        if not self.available:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="tesseract-unavailable",
            )
        image = self._load_image(frame)
        if image is None:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="tesseract-no-image",
            )
        try:
            data = self._pytesseract.image_to_data(
                image,
                lang=self.lang,
                config=self._config(),
                output_type=self._pytesseract.Output.DICT,
            )
            lines = self._group_lines(data)
            text = "\n".join(lines)
            confidences = [
                int(value) / 100.0
                for value, word in zip(data["conf"], data["text"])
                if word.strip() and int(value) >= 0
            ]
            confidence = (
                round(statistics.mean(confidences), 4)
                if confidences
                else 0.0
            )
            return OcrResult(
                text=text,
                lines=lines,
                confidence=min(1.0, max(0.0, confidence)),
                source="tesseract",
            )
        except Exception:
            return OcrResult(
                text="",
                lines=[],
                confidence=0.0,
                source="tesseract-error",
            )

    def _load_image(self, frame: VisionFrame):
        reference = frame.image_reference or ""
        if not reference or reference.startswith(("capture://", "unavailable://")):
            return None
        try:
            from PIL import Image

            path = Path(reference)
            if not path.is_file():
                return None
            return Image.open(path)
        except Exception:
            return None

    @staticmethod
    def _group_lines(data: dict) -> list[str]:
        """按 block/par/line 聚合词级 OCR 输出为行文本。"""
        groups: dict[tuple[int, int, int], list[tuple[int, str]]] = {}
        for index, word in enumerate(data["text"]):
            if not word.strip():
                continue
            key = (
                data["block_num"][index],
                data["par_num"][index],
                data["line_num"][index],
            )
            groups.setdefault(key, []).append(
                (data["left"][index], word)
            )
        lines: list[str] = []
        for key in sorted(groups):
            words = [word for _, word in sorted(groups[key])]
            lines.append(" ".join(words))
        return lines


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

    def capability(self) -> dict:
        """当前 backend 能力探测结果。"""
        if self._backend is not None and hasattr(self._backend, "capability"):
            return self._backend.capability()
        return {
            "backend": self.backend_name,
            "available": False,
            "reason": "no OCR backend available",
        }

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
