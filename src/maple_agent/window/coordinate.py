"""CoordinateTransformer:Screen ↔ Client 坐标换算(支持 100%/125%/150%/200% DPI)。"""

from __future__ import annotations

from maple_agent.window.binding import BoundWindow


class CoordinateTransformer:
    """基于 BoundWindow 的屏幕/客户区坐标转换(逻辑坐标系)。"""

    def __init__(self, bound: BoundWindow) -> None:
        self.bound = bound

    @property
    def dpi_scale(self) -> float:
        return self.bound.dpi_scale

    def screen_to_client(self, x: float, y: float) -> tuple[float, float]:
        """屏幕物理坐标 → 客户区逻辑坐标。"""
        origin_x, origin_y = self.bound.client_offset
        return (
            (x - origin_x) / self.dpi_scale,
            (y - origin_y) / self.dpi_scale,
        )

    def client_to_screen(self, cx: float, cy: float) -> tuple[float, float]:
        """客户区逻辑坐标 → 屏幕物理坐标。"""
        origin_x, origin_y = self.bound.client_offset
        return (
            cx * self.dpi_scale + origin_x,
            cy * self.dpi_scale + origin_y,
        )
