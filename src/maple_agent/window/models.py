"""Window 领域模型(Phase 3-A,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class WindowRect(BaseModel):
    """窗口矩形。"""

    left: int
    top: int
    width: int
    height: int


class WindowInfo(BaseModel):
    """窗口信息(只读,禁止内存读取/注入/Hook)。"""

    title: str
    process_name: str
    hwnd: int
    screen_rect: WindowRect
    client_rect: WindowRect
    dpi_scale: float = Field(default=1.0, gt=0)
    trace_id: str = ""


class WindowBindingStatus(StrEnum):
    """窗口绑定状态。"""

    UNBOUND = "UNBOUND"
    BOUND = "BOUND"
    LOST = "LOST"
