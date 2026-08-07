"""CaptureProvider:截图源抽象 + Mock + Windows 实现(Phase 1.1 仅感知)。"""

from __future__ import annotations

import sys
from abc import abstractmethod
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from maple_agent.events import EventBus, EventType
from maple_agent.game.window import GameWindowDetector, WindowInfo
from maple_agent.logging_setup import new_id
from maple_agent.providers.base import BaseProvider, ProviderError
from maple_agent.vision.models import ScreenFrame
from maple_agent.vision.policy import ScreenshotPolicy, enforce_capacity


class CaptureProvider(BaseProvider):
    """截图 Provider 抽象(复用 BaseProvider 生命周期)。"""

    def __init__(
        self,
        *,
        name: str = "capture",
        bus: EventBus | None = None,
        policy: ScreenshotPolicy | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        super().__init__(name=name, logger_name="maple_agent.vision.capture", bus=bus)
        self.policy = policy or ScreenshotPolicy()
        self.sessions_dir = Path(sessions_dir)

    def capture_frame(self, *, trace_id: str | None = None) -> ScreenFrame:
        """捕获一帧并返回 ScreenFrame(成功发布 SCREEN_CAPTURED)。"""
        return self._run_call(
            trace_id,
            success_event=EventType.SCREEN_CAPTURED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._do_capture(tid)[0],
        )

    def capture_with_image(
        self, *, trace_id: str | None = None
    ) -> tuple[ScreenFrame, Image.Image]:
        """捕获一帧并返回 (ScreenFrame, 图像)(OCR 等下游使用)。"""
        return self._run_call(
            trace_id,
            success_event=EventType.SCREEN_CAPTURED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._do_capture(tid),
        )

    @abstractmethod
    def _capture_image(self, tid: str) -> tuple[Image.Image, dict[str, Any]]:
        """返回 (图像, 元信息)。"""

    def _do_capture(self, tid: str) -> tuple[ScreenFrame, Image.Image]:
        image, meta = self._capture_image(tid)
        width, height = image.size
        frame = ScreenFrame(
            frame_id=new_id(),
            trace_id=tid,
            captured_at=datetime.now(UTC),
            window=meta.get("window"),
            width=width,
            height=height,
            dpi_scale=float(meta.get("dpi_scale", 1.0)),
            source_provider=self.name,
            window_hwnd=meta.get("window_hwnd"),
            capture_space=str(meta.get("capture_space", "")),
            capture_width=width,
            capture_height=height,
        )
        if self.policy.save_enabled:
            frame.image_path = self._save_image(image, tid)
        return frame, image

    def _save_image(self, image: Image.Image, trace_id: str) -> str:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        if self.policy.compression == "jpeg":
            path = directory / "frame.jpg"
            image.convert("RGB").save(path, "JPEG", quality=85)
        else:
            path = directory / "frame.png"
            image.save(path, "PNG")
        enforce_capacity(self.sessions_dir, self.policy.max_images, self.policy.ttl_seconds)
        return str(path)


class MockCaptureProvider(CaptureProvider):
    """Mock 实现:生成固定尺寸的合成帧,离线测试用。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        policy: ScreenshotPolicy | None = None,
        sessions_dir: str | Path = "sessions",
        width: int = 1280,
        height: int = 720,
        window: WindowInfo | None = None,
        dpi_scale: float = 1.0,
        raise_on_capture: bool = False,
    ) -> None:
        super().__init__(
            name="mock_capture",
            bus=bus,
            policy=policy,
            sessions_dir=sessions_dir,
        )
        self._width = width
        self._height = height
        self._window = window
        self._dpi_scale = dpi_scale
        self._raise_on_capture = raise_on_capture
        self.call_count = 0

    def _capture_image(self, tid: str) -> tuple[Image.Image, dict[str, Any]]:
        self.call_count += 1
        if self._raise_on_capture:
            raise ProviderError("mock capture failure")
        image = Image.new("RGB", (self._width, self._height), color=(28, 52, 84))
        draw = ImageDraw.Draw(image)
        draw.rectangle((20, 20, 260, 60), fill=(230, 200, 120))
        draw.text((30, 28), f"MAPLE MOCK FRAME {tid[:8]}", fill=(20, 20, 20))
        return image, {
            "window": self._window,
            "width": self._width,
            "height": self._height,
            "dpi_scale": self._dpi_scale,
        }


class WindowsCaptureProvider(CaptureProvider):
    """真实 win32 截图(DPI-Aware),仅 Windows;未找到有效窗口时抛 ProviderError。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        policy: ScreenshotPolicy | None = None,
        sessions_dir: str | Path = "sessions",
        detector: GameWindowDetector | None = None,
    ) -> None:
        super().__init__(
            name="win32_capture",
            bus=bus,
            policy=policy,
            sessions_dir=sessions_dir,
        )
        self.detector = detector

    @staticmethod
    def is_supported() -> bool:
        return sys.platform == "win32"

    def _capture_image(self, tid: str) -> tuple[Image.Image, dict[str, Any]]:
        if not self.is_supported():
            raise ProviderError("WindowsCaptureProvider 仅支持 Windows")
        if self.detector is None:
            raise ProviderError("未配置窗口检测器")
        window = self.detector.find_window()
        if window is None or window.handle <= 0:
            raise ProviderError("目标窗口不存在,无法截图")
        image, dpi_scale = self._capture_window(window.handle, window.rect.width)
        return image, {
            "window": window,
            "width": image.size[0],
            "height": image.size[1],
            "dpi_scale": dpi_scale,
        }

    def _capture_window(self, hwnd: int, logical_width: int) -> tuple[Image.Image, float]:
        import ctypes
        from ctypes import wintypes

        from PIL import ImageGrab

        user32 = ctypes.windll.user32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass
        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise ProviderError("GetWindowRect 失败")
        left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        if right <= left or bottom <= top:
            raise ProviderError("窗口尺寸无效")
        image = ImageGrab.grab(bbox=(left, top, right, bottom), all_screens=True)
        dpi_scale = 1.0
        if logical_width > 0:
            dpi_scale = round((right - left) / logical_width, 4)
        return image, dpi_scale
