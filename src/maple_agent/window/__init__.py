"""Window Binding Foundation(Phase 3-A):只读识别/绑定/坐标体系。"""

from maple_agent.window.binding import BoundWindow, WindowBindingService
from maple_agent.window.coordinate import CoordinateTransformer
from maple_agent.window.detector import MockWindowDetector, WindowsWindowDetector
from maple_agent.window.models import (
    WindowBindingStatus,
    WindowInfo,
    WindowRect,
)

__all__ = [
    "BoundWindow",
    "CoordinateTransformer",
    "MockWindowDetector",
    "WindowBindingService",
    "WindowBindingStatus",
    "WindowInfo",
    "WindowRect",
    "WindowsWindowDetector",
]
