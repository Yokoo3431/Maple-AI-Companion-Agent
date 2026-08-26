"""WindowsGraphicsCaptureProvider:WGC 只读窗口捕获(Phase 13-I.1)。

复用 ScreenshotProvider 契约(WindowsScreenshotProvider 同级实现,非第二套架构)。
依赖 `windows-capture` 包 + pywin32;未安装/窗口不可用/最小化时诚实失败。
不激活窗口、不控制窗口、无 Hook/注入。
"""

from __future__ import annotations

import importlib.util
import time
from datetime import UTC, datetime

from maple_agent.logging_setup import new_id
from maple_agent.real_vision.models import CaptureStatus
from maple_agent.vision_runtime.models import (
    CaptureReference,
    VisionFrame,
    VisionSource,
)
from maple_agent.window import (
    GameWindowProfile,
    WindowDiscoveryResult,
    WindowsWindowDiscovery,
    default_game_window_profile,
)


class WindowsGraphicsCaptureProvider:
    """Windows.Graphics.Capture 只读 Provider(后台/遮挡可用,最小化不可用)。"""

    def __init__(
        self,
        *,
        window_title: str | None = None,
        save_dir: str | None = None,
        frame_timeout_s: float = 5.0,
        window_profile: GameWindowProfile | None = None,
    ) -> None:
        profile = window_profile or default_game_window_profile()
        if window_title:
            profile = profile.with_title_candidates((window_title,))
        self.window_profile = profile
        self.window_title = window_title or profile.primary_title
        self.save_dir = save_dir
        self.frame_timeout_s = max(0.5, frame_timeout_s)
        self.capture_method = "wgc"
        self.last_capture: CaptureReference | None = None
        self.last_status: CaptureStatus = CaptureStatus.UNAVAILABLE
        self.last_window_info: dict = {}
        self.last_discovery: WindowDiscoveryResult | None = None
        self.available = (
            importlib.util.find_spec("win32gui") is not None
            and importlib.util.find_spec("windows_capture") is not None
        )

    def binding_status(self) -> str:
        if not self.available:
            return "NOT_FOUND"
        return "DISCOVERABLE"

    def _find_window(self) -> int:
        try:
            import win32gui  # type: ignore[import-not-found]

            result = WindowsWindowDiscovery(win32gui=win32gui).discover(
                self.window_profile
            )
            self.last_discovery = result
            handle = int(result.hwnd or 0)
            if handle:
                self.last_window_info = {
                    "hwnd": handle,
                    "window_title": result.window_title,
                    "pid": result.pid,
                    "process_name": result.process_name,
                    "match_method": result.match_method,
                    "match_confidence": result.confidence,
                    "match_reason": result.reason,
                    "minimized": bool(win32gui.IsIconic(handle)),
                    "visible": bool(win32gui.IsWindowVisible(handle)),
                }
            return handle
        except Exception:
            self.last_discovery = None
            return 0

    def capture(self, *, trace_id: str = "") -> VisionFrame:
        """单帧 WGC 捕获;看门狗超时 / 最小化 -> 诚实失败。"""
        self.last_capture = None
        if not self.available:
            self.last_status = CaptureStatus.UNAVAILABLE
            return self._frame(
                "unavailable://wgc-package-missing", 0.0
            )
        hwnd = self._find_window()
        if not hwnd:
            self.last_status = CaptureStatus.WINDOW_NOT_FOUND
            return self._frame(
                "unavailable://wgc-window-not-found", 0.0
            )
        if self.last_window_info.get("minimized"):
            self.last_status = CaptureStatus.WINDOW_INVALID
            return self._frame(
                "unavailable://wgc-minimized", 0.0
            )
        result: list[str] = []
        start = time.perf_counter()

        def on_frame(frame, control) -> None:
            if self.save_dir:
                from pathlib import Path

                directory = Path(self.save_dir)
                directory.mkdir(parents=True, exist_ok=True)
                target = str(directory / f"{new_id()}.png")
                frame.save_as_image(target)
                result.append(target)
            control.stop()

        try:
            from windows_capture import WindowsCapture  # type: ignore

            capture = WindowsCapture(
                window_hwnd=hwnd,
                cursor_capture=False,
                draw_border=False,
            )

            @capture.event
            def on_frame_arrived(frame, control) -> None:
                on_frame(frame, control)

            @capture.event
            def on_closed() -> None:
                pass

            control = capture.start_free_threaded()
            deadline = time.time() + self.frame_timeout_s
            while (
                time.time() < deadline
                and not result
                and not control.is_finished()
            ):
                time.sleep(0.05)
            control.stop()
            control.wait()
        except Exception:
            self.last_status = CaptureStatus.CAPTURE_FAILED
            return self._frame(
                "unavailable://wgc-capture-failed", 0.0
            )
        if not result:
            self.last_status = CaptureStatus.WINDOW_INVALID
            return self._frame("unavailable://wgc-no-frame", 0.0)
        latency = round((time.perf_counter() - start) * 1000, 2)
        self.last_status = CaptureStatus.OK
        self._record_capture_reference(
            reference=result[0],
            timestamp=datetime.now(UTC),
            confidence=1.0,
            latency_ms=latency,
        )
        return self._frame(result[0], 1.0)

    def _frame(self, reference: str, confidence: float) -> VisionFrame:
        return VisionFrame(
            frame_id=new_id(),
            timestamp=datetime.now(UTC),
            source=VisionSource.WINDOW_CAPTURE_REFERENCE,
            image_reference=reference,
            confidence=confidence,
        )

    def _record_capture_reference(
        self,
        *,
        reference: str,
        timestamp,
        confidence: float,
        latency_ms: float,
    ) -> None:
        self.last_capture = CaptureReference(
            capture_id=new_id(),
            source="windows/wgc",
            window_title=self.window_title,
            window_rect=self.last_window_info,
            timestamp=timestamp,
            confidence=confidence,
        )

    def capture_reference(self) -> CaptureReference | None:
        return self.last_capture
