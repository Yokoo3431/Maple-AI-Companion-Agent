"""WindowDetector:只读获取窗口标题/进程/hwnd/rect。"""

from __future__ import annotations

import sys
from typing import Protocol, runtime_checkable

from maple_agent.window.models import WindowInfo, WindowRect


@runtime_checkable
class WindowDetector(Protocol):
    """窗口检测契约(只读)。"""

    def find_window(self, *, trace_id: str | None = None) -> WindowInfo | None: ...


def _process_name(pid: int) -> str:
    """通过 OpenProcess + QueryFullProcessImageNameW 获取进程名(只读)。"""
    import ctypes
    from ctypes import wintypes

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    kernel32 = ctypes.windll.kernel32
    handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ""
    try:
        buffer = ctypes.create_unicode_buffer(1024)
        size = wintypes.DWORD(1024)
        if kernel32.QueryFullProcessImageNameW(handle, 0, buffer, ctypes.byref(size)):
            return buffer.value.split("\\")[-1]
        return ""
    finally:
        kernel32.CloseHandle(handle)


class WindowsWindowDetector:
    """win32 实现:仅读取标题/进程名/hwnd/rect/DPI(禁止内存读取/注入/Hook)。"""

    @staticmethod
    def is_supported() -> bool:
        return sys.platform == "win32"

    def find_window(
        self,
        *,
        title: str | None = None,
        trace_id: str | None = None,
    ) -> WindowInfo | None:
        if not self.is_supported():
            return None
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            hwnd = (
                user32.FindWindowW(None, title)
                if title
                else user32.GetForegroundWindow()
            )
            if not hwnd:
                return None
            rect = wintypes.RECT()
            user32.GetWindowRect(hwnd, ctypes.byref(rect))
            client = wintypes.RECT()
            user32.GetClientRect(hwnd, ctypes.byref(client))
            point = wintypes.POINT(0, 0)
            user32.ClientToScreen(hwnd, ctypes.byref(point))
            dpi_scale = 1.0
            try:
                dpi_scale = user32.GetDpiForWindow(hwnd) / 96.0
            except Exception:
                pass
            title_buffer = ctypes.create_unicode_buffer(512)
            user32.GetWindowTextW(hwnd, title_buffer, 512)
            pid = wintypes.DWORD()
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
            info = WindowInfo(
                title=title_buffer.value or (title or ""),
                process_name=_process_name(pid.value),
                hwnd=int(hwnd),
                screen_rect=WindowRect(
                    left=rect.left,
                    top=rect.top,
                    width=rect.right - rect.left,
                    height=rect.bottom - rect.top,
                ),
                client_rect=WindowRect(
                    left=point.x,
                    top=point.y,
                    width=client.right - client.left,
                    height=client.bottom - client.top,
                ),
                dpi_scale=round(dpi_scale, 4),
                trace_id=trace_id or "",
            )
            return info
        except Exception:
            return None


class MockWindowDetector:
    """Mock 实现:返回固定窗口信息(离线测试)。"""

    def __init__(self, window: WindowInfo | None = None) -> None:
        self._window = window

    def find_window(self, *, trace_id: str | None = None) -> WindowInfo | None:
        if self._window is None:
            return None
        if trace_id and not self._window.trace_id:
            return self._window.model_copy(update={"trace_id": trace_id})
        return self._window
