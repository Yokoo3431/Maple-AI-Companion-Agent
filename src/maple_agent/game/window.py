"""只读 Game Window Detector 接口(Phase 0:接口 + Mock,不接真实 win32)。"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class WindowRect:
    """窗口矩形(窗口坐标,逻辑单位)。"""

    left: int
    top: int
    width: int
    height: int


@dataclass(frozen=True)
class WindowInfo:
    """窗口信息(handle 仅用于标识,禁止任何写入 / 注入 / Hook)。"""

    handle: int
    title: str
    process_name: str
    rect: WindowRect


class GameWindowDetector(ABC):
    """只读窗口检测抽象。

    允许:窗口存在检测、窗口标题、进程名、窗口 Rect。
    禁止:内存读取、注入、Hook、句柄写入、窗口内容操作。
    """

    @abstractmethod
    def find_window(self) -> WindowInfo | None:
        """返回目标窗口信息;未找到返回 None。"""

    def exists(self) -> bool:
        """目标窗口是否存在。"""
        return self.find_window() is not None


class MockGameWindowDetector(GameWindowDetector):
    """Mock 实现:返回预设窗口信息(Phase 0 测试用)。"""

    def __init__(self, window: WindowInfo | None = None) -> None:
        self._window = window

    def find_window(self) -> WindowInfo | None:
        return self._window
