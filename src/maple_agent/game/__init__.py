"""游戏客户端相关(Phase 0 仅只读窗口检测接口)。"""

from maple_agent.game.window import (
    GameWindowDetector,
    MockGameWindowDetector,
    WindowInfo,
    WindowRect,
)

__all__ = ["GameWindowDetector", "MockGameWindowDetector", "WindowInfo", "WindowRect"]
