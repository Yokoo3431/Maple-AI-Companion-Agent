"""Vision 坐标对齐(Phase 3-B):帧像素/OCR bbox → 客户区逻辑坐标。"""

from maple_agent.vision.coordinate.alignment import VisionAlignmentService
from maple_agent.vision.coordinate.mapper import (
    VisionCoordinateError,
    VisionCoordinateMapper,
)
from maple_agent.vision.coordinate.models import (
    CoordinateSpace,
    VisionFrameCoordinate,
)

__all__ = [
    "CoordinateSpace",
    "VisionAlignmentService",
    "VisionCoordinateError",
    "VisionCoordinateMapper",
    "VisionFrameCoordinate",
]
