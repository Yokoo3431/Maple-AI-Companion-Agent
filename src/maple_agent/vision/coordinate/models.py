"""Vision 坐标对齐模型(Phase 3-B)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class CoordinateSpace(StrEnum):
    """坐标系。"""

    SCREEN_SPACE = "SCREEN_SPACE"
    CLIENT_SPACE = "CLIENT_SPACE"
    CLIENT_LOGICAL_SPACE = "CLIENT_LOGICAL_SPACE"


class VisionFrameCoordinate(BaseModel):
    """帧坐标对齐参数。"""

    frame_width: int = Field(gt=0)
    frame_height: int = Field(gt=0)
    source_space: CoordinateSpace = CoordinateSpace.CLIENT_SPACE
    target_space: CoordinateSpace = CoordinateSpace.CLIENT_LOGICAL_SPACE
    dpi_scale: float = Field(default=1.0, gt=0)
    offset_x: float = 0.0
    offset_y: float = 0.0
    trace_id: str = ""
