"""Window Binding Foundation(Phase 3-A):只读识别/绑定/坐标体系。"""

from maple_agent.window.binding import BoundWindow, WindowBindingService
from maple_agent.window.coordinate import CoordinateTransformer
from maple_agent.window.detector import MockWindowDetector, WindowsWindowDetector
from maple_agent.window.discovery import (
    WindowCandidate,
    WindowDiscoveryResult,
    WindowsWindowDiscovery,
    discover_window,
)
from maple_agent.window.models import (
    WindowBindingStatus,
    WindowInfo,
    WindowRect,
)
from maple_agent.window.profile import GameWindowProfile, default_game_window_profile

__all__ = [
    "BoundWindow",
    "CoordinateTransformer",
    "GameWindowProfile",
    "MockWindowDetector",
    "WindowBindingService",
    "WindowBindingStatus",
    "WindowCandidate",
    "WindowDiscoveryResult",
    "WindowInfo",
    "WindowRect",
    "WindowsWindowDiscovery",
    "WindowsWindowDetector",
    "default_game_window_profile",
    "discover_window",
]
