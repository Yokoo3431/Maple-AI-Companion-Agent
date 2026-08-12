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
        self.last_window_info: dict = {}
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
            handle = self._find_window()
            if not handle:
                return {}
            self._collect_window_info(handle)
            left, top, right, bottom = self._win32.GetClientRect(handle)
            # GetClientRect 返回客户区相对坐标(左上通常 0,0);
            # ImageGrab bbox 需要屏幕坐标,因此用 ClientToScreen 修正。
            screen_x, screen_y = self._win32.ClientToScreen(handle, (0, 0))
            self.last_window_info["client_rect"] = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
            self.last_window_info["screen_rect"] = {
                "left": screen_x + left,
                "top": screen_y + top,
                "width": right - left,
                "height": bottom - top,
            }
            self._finalize_window_info()
            return {
                "left": screen_x + left,
                "top": screen_y + top,
                "width": right - left,
                "height": bottom - top,
            }
        except Exception:
            return {}

    def _find_window(self) -> int:
        """按标题查找窗口;未找到时返回 0。"""
        try:
            return int(self._win32.FindWindow(None, self.window_title) or 0)
        except Exception:
            return 0

    def _collect_window_info(self, handle: int) -> None:
        """收集窗口元数据(只读,不控制窗口)。"""
        info: dict = {
            "hwnd": handle,
            "requested_title": self.window_title,
            "window_title": "",
            "class_name": "",
            "pid": None,
            "process_name": "",
            "window_rect": {},
            "client_rect": {},
            "screen_rect": {},
            "resolution": "",
            "dpi_scale": 1.0,
            "window_mode": "",
            "visible": False,
            "minimized": False,
            "foreground": False,
        }
        try:
            info["window_title"] = self._win32.GetWindowText(handle)
            info["class_name"] = self._win32.GetClassName(handle)
            info["visible"] = bool(self._win32.IsWindowVisible(handle))
            info["minimized"] = bool(self._win32.IsIconic(handle))
            try:
                info["foreground"] = (
                    self._win32.GetForegroundWindow() == handle
                )
            except Exception:
                pass
            left, top, right, bottom = self._win32.GetWindowRect(handle)
            info["window_rect"] = {
                "left": left,
                "top": top,
                "width": right - left,
                "height": bottom - top,
            }
        except Exception:
            pass
        try:
            import win32process  # type: ignore[import-not-found]

            _, pid = win32process.GetWindowThreadProcessId(handle)
            info["pid"] = pid
            try:
                import win32api  # type: ignore[import-not-found]

                process = win32api.OpenProcess(0x1000, False, pid)
                info["process_name"] = win32process.GetModuleFileNameEx(
                    process, 0
                )
            except Exception:
                pass
        except Exception:
            pass
        self.last_window_info = info

    def _finalize_window_info(self) -> None:
        """在 client/screen rect 填充后派生 resolution 与 window_mode。"""
        info = self.last_window_info
        client_rect = info.get("client_rect") or {}
        screen_rect = info.get("screen_rect") or {}
        width = client_rect.get("width") or screen_rect.get("width") or 0
        height = client_rect.get("height") or screen_rect.get("height") or 0
        if width and height:
            info["resolution"] = f"{width}x{height}"
        window_rect = info.get("window_rect") or {}
        if window_rect:
            info["window_mode"] = (
                "fullscreen-windowed"
                if (
                    window_rect.get("left", 0) == 0
                    and window_rect.get("top", 0) == 0
                    and window_rect.get("width", 0) >= 2560
                )
                else "windowed"
            )
        try:
            import ctypes

            hwnd = info.get("hwnd")
            dpi = ctypes.windll.user32.GetDpiForWindow(hwnd) if hwnd else 0
            if dpi:
                info["dpi_scale"] = round(dpi / 96.0, 3)
        except Exception:
            pass

    def discover_window(self) -> dict:
        """返回窗口发现结果(找不到窗口时返回空元数据 + binding 状态)。"""
        if self._win32 is None:
            return {"binding": "NOT_FOUND", "reason": "win32 unavailable"}
        handle = self._find_window()
        if not handle:
            self.last_window_info = {}
            return {
                "binding": "NOT_FOUND",
                "requested_title": self.window_title,
                "reason": "window not found",
            }
        self._collect_window_info(handle)
        self._resolve_rect()
        self._finalize_window_info()
        return {"binding": "BOUND", **self.last_window_info}

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
        if self.method in ("auto", "win32") and self._win32 is not None:
            reference, status = self._printwindow(rect)
            if status is CaptureStatus.OK:
                self.capture_method = "printwindow"
                return reference, status
            self.fallback_reason = (
                "printwindow unavailable/black frame; imagegrab fallback"
            )
        if self.method in ("auto", "imagegrab", "win32"):
            reference, status = self._imagegrab(rect)
            if status is CaptureStatus.OK:
                self.capture_method = "imagegrab"
            return reference, status
        self.fallback_reason = f"method not supported: {self.method}"
        return "unavailable://method-not-supported", CaptureStatus.UNAVAILABLE

    def _printwindow(self, rect: dict) -> tuple[str, CaptureStatus]:
        """PrintWindow 只读尝试(GPU 合成内容可能返回黑帧,失败安全回退)。"""
        try:
            import ctypes

            import win32gui  # type: ignore[import-not-found]
            import win32ui  # type: ignore[import-not-found]

            hwnd = self.last_window_info.get("hwnd")
            if not hwnd:
                return "unavailable://printwindow-no-hwnd", CaptureStatus.UNAVAILABLE
            if self.last_window_info.get("minimized"):
                return (
                    "unavailable://printwindow-minimized",
                    CaptureStatus.UNAVAILABLE,
                )
            left, top, right, bottom = win32gui.GetWindowRect(hwnd)
            width = right - left
            height = bottom - top
            if width <= 0 or height <= 0:
                return (
                    "unavailable://printwindow-empty-rect",
                    CaptureStatus.UNAVAILABLE,
                )
            hdc = win32gui.GetWindowDC(hwnd)
            mfc_dc = win32ui.CreateDCFromHandle(hdc)
            save_dc = mfc_dc.CreateCompatibleDC()
            bitmap = win32ui.CreateBitmap()
            bitmap.CreateCompatibleBitmap(mfc_dc, width, height)
            save_dc.SelectObject(bitmap)
            result = 0
            try:
                result = ctypes.windll.user32.PrintWindow(
                    hwnd,
                    save_dc.GetSafeHdc(),
                    1,
                )
                bmpinfo = bitmap.GetInfo()
                bmpstr = bitmap.GetBitmapBits(True)
            finally:
                win32gui.DeleteObject(bitmap.GetHandle())
                save_dc.DeleteDC()
                mfc_dc.DeleteDC()
                win32gui.ReleaseDC(hwnd, hdc)
            if not result:
                return (
                    "unavailable://printwindow-failed",
                    CaptureStatus.UNAVAILABLE,
                )
            from PIL import Image, ImageStat

            image = Image.frombuffer(
                "RGB",
                (bmpinfo["bmWidth"], bmpinfo["bmHeight"]),
                bmpstr,
                "raw",
                "BGRX",
                0,
                1,
            )
            stats = ImageStat.Stat(image.convert("L"))
            if stats.mean[0] < 5.0 or stats.stddev[0] < 6.0:
                return (
                    "unavailable://printwindow-black",
                    CaptureStatus.UNAVAILABLE,
                )
            reference = f"capture://printwindow/{self.last_window_info.get('hwnd')}"
            if self.save_dir:
                from pathlib import Path

                directory = Path(self.save_dir)
                directory.mkdir(parents=True, exist_ok=True)
                path = directory / f"{new_id()}.png"
                image.save(path)
                reference = str(path)
            return reference, CaptureStatus.OK
        except Exception as exc:
            self.fallback_reason = f"printwindow failed: {exc}"
            return (
                "unavailable://printwindow-error",
                CaptureStatus.UNAVAILABLE,
            )

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
