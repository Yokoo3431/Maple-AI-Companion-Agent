"""WindowsCaptureProvider:真实窗口截图(Phase 3-C,只读,无输入)。"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from PIL import Image

from maple_agent.events import EventBus
from maple_agent.vision.capture import CaptureProvider
from maple_agent.vision.policy import ScreenshotPolicy
from maple_agent.window.binding import BoundWindow


class CaptureError(RuntimeError):
    """窗口截图失败。"""


class WindowsCaptureProvider(CaptureProvider):
    """真实 win32 截图:优先 BitBlt,失败 PrintWindow;仅读取,无任何输入操作。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        policy: ScreenshotPolicy | None = None,
        sessions_dir: str | Path = "sessions",
        bound: BoundWindow | None = None,
        capture_space: str = "CLIENT_SPACE",
    ) -> None:
        super().__init__(
            name="win32_capture",
            bus=bus,
            policy=policy,
            sessions_dir=sessions_dir,
        )
        self.bound = bound
        self.capture_space = capture_space
        self.last_capture_method: str | None = None

    @staticmethod
    def is_supported() -> bool:
        return sys.platform == "win32"

    def _capture_image(self, tid: str) -> tuple[Image.Image, dict[str, Any]]:
        if not self.is_supported():
            raise CaptureError("WindowsCaptureProvider 仅支持 Windows")
        if self.bound is None:
            raise CaptureError("未绑定窗口(需要 BoundWindow)")
        hwnd = self.bound.window.hwnd
        if hwnd <= 0:
            raise CaptureError(f"窗口句柄无效: {hwnd}")
        image, method = self._capture_window(hwnd, self.capture_space)
        self.last_capture_method = method
        return image, {
            "width": image.size[0],
            "height": image.size[1],
            "dpi_scale": self.bound.dpi_scale,
            "window_hwnd": hwnd,
            "capture_space": self.capture_space,
        }

    def _capture_window(
        self,
        hwnd: int,
        capture_space: str,
    ) -> tuple[Image.Image, str]:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            pass

        rect = wintypes.RECT()
        if capture_space == "CLIENT_SPACE":
            user32.GetClientRect(hwnd, ctypes.byref(rect))
            left, top = 0, 0
            right, bottom = rect.right, rect.bottom
        else:
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            left, top, right, bottom = rect.left, rect.top, rect.right, rect.bottom
        width = right - left
        height = bottom - top
        if width <= 0 or height <= 0:
            raise CaptureError(f"捕获区域无效: {width}x{height}")

        try:
            image = self._bitblt(hwnd, left, top, width, height)
            return image, "BITBLT"
        except Exception:
            pass
        try:
            image = self._print_window(hwnd, width, height)
            return image, "PRINTWINDOW"
        except Exception as exc:
            raise CaptureError(f"窗口截图失败: {exc}") from exc

    def _bitblt(
        self,
        hwnd: int,
        left: int,
        top: int,
        width: int,
        height: int,
    ) -> Image.Image:
        """BitBlt 方案:对可见窗口截取客户区/屏幕区域。"""
        import ctypes
        from ctypes import wintypes

        from PIL import ImageGrab

        user32 = ctypes.windll.user32
        if left == 0 and top == 0:
            point = wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(point))
            left, top = point.x, point.y
        return ImageGrab.grab(
            bbox=(left, top, left + width, top + height),
            all_screens=True,
        )

    def _print_window(
        self,
        hwnd: int,
        width: int,
        height: int,
    ) -> Image.Image:
        """PrintWindow 方案:可捕获隐藏/遮挡窗口。"""
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        class BITMAPINFOHEADER(ctypes.Structure):
            _fields_ = [
                ("biSize", wintypes.DWORD),
                ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long),
                ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD),
                ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD),
                ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long),
                ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD),
            ]

        hwnd_dc = user32.GetWindowDC(hwnd)
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        old = gdi32.SelectObject(mem_dc, bitmap)
        try:
            if not user32.PrintWindow(hwnd, mem_dc, 2):
                raise CaptureError("PrintWindow 失败")
            bmi = BITMAPINFOHEADER()
            bmi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmi.biWidth = width
            bmi.biHeight = -height
            bmi.biPlanes = 1
            bmi.biBitCount = 32
            bmi.biCompression = 0
            buffer = ctypes.create_string_buffer(width * height * 4)
            if gdi32.GetDIBits(mem_dc, bitmap, 0, height, buffer, ctypes.byref(bmi), 0) == 0:
                raise CaptureError("GetDIBits 失败")
            return Image.frombuffer(
                "RGBA",
                (width, height),
                buffer.raw,
                "raw",
                "BGRA",
                0,
                1,
            ).convert("RGB")
        finally:
            gdi32.SelectObject(mem_dc, old)
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)
