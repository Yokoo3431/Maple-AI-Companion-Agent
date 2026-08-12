"""WindowsScreenshotProvider:真实只读窗口截图(无输入,失败安全)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.logging_setup import new_id
from maple_agent.real_vision.models import CaptureStatus
from maple_agent.vision_runtime.models import (
    CaptureReference,
    VisionFrame,
    VisionSource,
)


class WindowsScreenshotProvider:
    """绑定指定游戏窗口的只读截图 Provider(复用 ScreenshotProvider 契约)。"""

    def __init__(
        self,
        *,
        window_title: str = "MapleStory",
        method: str = "auto",
        window_rect: dict | None = None,
        dpi_scale: float = 1.0,
        save_dir: str | None = None,
    ) -> None:
        self.window_title = window_title
        self.method = method
        self.window_rect = dict(window_rect or {})
        self.dpi_scale = dpi_scale
        self.save_dir = save_dir
        self.capture_method = ""
        self.fallback_reason = ""
        self.last_capture: CaptureReference | None = None
        self.last_status: CaptureStatus = CaptureStatus.UNAVAILABLE
        self._win32 = self._probe_win32()
        self.call_count = 0

    @staticmethod
    def _probe_win32():
        try:
            import win32gui  # type: ignore[import-not-found]

            return win32gui
        except ImportError:
            return None

    def _resolve_rect(self) -> dict:
        if self.window_rect:
            return self.window_rect
        if self._win32 is None:
            return {}
        try:
            handle = self._win32.FindWindow(None, self.window_title)
            if not handle:
                return {}
            left, top, right, bottom = self._win32.GetClientRect(handle)
            # GetClientRect 返回客户区相对坐标(左上通常 0,0);
            # ImageGrab bbox 需要屏幕坐标,因此用 ClientToScreen 修正。
            screen_x, screen_y = self._win32.ClientToScreen(handle, (0, 0))
            return {
                "left": screen_x + left,
                "top": screen_y + top,
                "width": right - left,
                "height": bottom - top,
            }
        except Exception:
            return {}

    def binding_status(self) -> str:
        if self.window_rect:
            return "BOUND"
        if self._win32 is not None:
            return "DISCOVERABLE"
        return "NOT_FOUND"

    def capture(self, *, trace_id: str = "") -> VisionFrame:
        self.call_count += 1
        rect = self._resolve_rect()
        width = int(rect.get("width", 0))
        height = int(rect.get("height", 0))
        if not rect or width <= 0 or height <= 0:
            self.last_status = CaptureStatus.WINDOW_NOT_FOUND
            self._record_capture_reference(
                rect=rect,
                timestamp=datetime.now(UTC),
                source="windows/unavailable",
                confidence=0.0,
            )
            return VisionFrame(
                frame_id=new_id(),
                timestamp=datetime.now(UTC),
                source=VisionSource.WINDOW_CAPTURE_REFERENCE,
                image_reference="unavailable://window-not-found",
                confidence=0.0,
            )
        image_reference, status = self._capture_region(rect)
        self.last_status = status
        if status is not CaptureStatus.OK:
            self._record_capture_reference(
                rect=rect,
                timestamp=datetime.now(UTC),
                source=(
                    f"windows/{self.capture_method or 'capture-failed'}"
                ),
                confidence=0.0,
            )
            return VisionFrame(
                frame_id=new_id(),
                timestamp=datetime.now(UTC),
                source=VisionSource.WINDOW_CAPTURE_REFERENCE,
                image_reference=image_reference,
                confidence=0.0,
            )
        frame = VisionFrame(
            frame_id=new_id(),
            timestamp=datetime.now(UTC),
            source=VisionSource.WINDOW_CAPTURE_REFERENCE,
            image_reference=image_reference,
            confidence=1.0,
        )
        self._record_capture_reference(
            rect=rect,
            timestamp=frame.timestamp,
            source=f"windows/{self.capture_method}",
            confidence=1.0,
        )
        return frame

    def _capture_region(self, rect: dict) -> tuple[str, CaptureStatus]:
        if (
            self.method in ("auto", "win32")
            and self._win32 is not None
        ):
            # PrintWindow capability probe(未实现):明确记录后回退 ImageGrab,
            # 不在成功 metadata 中误报 printwindow。
            self.fallback_reason = (
                "printwindow capability probe: not implemented; "
                "imagegrab fallback"
            )
        if self.method in ("auto", "imagegrab", "win32"):
            return self._imagegrab(rect)
        self.fallback_reason = f"method not supported: {self.method}"
        return "unavailable://method-not-supported", CaptureStatus.UNAVAILABLE

    def _imagegrab(self, rect: dict) -> tuple[str, CaptureStatus]:
        try:
            import PIL.ImageGrab

            self.capture_method = "imagegrab"
            box = (
                rect.get("left", 0),
                rect.get("top", 0),
                rect.get("left", 0) + rect.get("width", 0),
                rect.get("top", 0) + rect.get("height", 0),
            )
            image = PIL.ImageGrab.grab(bbox=box)
            reference = f"capture://frame/{new_id()}"
            if self.save_dir:
                from pathlib import Path

                directory = Path(self.save_dir)
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"{new_id()}.png"
                image.save(path)
                reference = str(path)
            return reference, CaptureStatus.OK
        except Exception as exc:
            self.fallback_reason = f"imagegrab failed: {exc}"
            return "unavailable://capture-failed", CaptureStatus.CAPTURE_FAILED

    def capture_reference(self) -> CaptureReference | None:
        return self.last_capture

    def _record_capture_reference(
        self,
        *,
        rect: dict,
        timestamp,
        source: str,
        confidence: float,
    ) -> None:
        """每次 capture() 调用都是一次 Capture Attempt,无论成败均生成审计参考。"""
        self.last_capture = CaptureReference(
            capture_id=new_id(),
            source=source,
            window_title=self.window_title,
            window_rect=dict(rect),
            timestamp=timestamp,
            confidence=confidence,
        )
