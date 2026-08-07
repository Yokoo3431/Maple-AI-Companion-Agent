"""VisionCoordinateMapper:帧像素 / OCR bbox → 客户区逻辑坐标。"""

from __future__ import annotations

from maple_agent.providers.ocr import OCRBBox
from maple_agent.vision.coordinate.models import (
    CoordinateSpace,
    VisionFrameCoordinate,
)
from maple_agent.vision.models import MappedBBox
from maple_agent.window.binding import BoundWindow
from maple_agent.window.coordinate import CoordinateTransformer


class VisionCoordinateError(RuntimeError):
    """坐标变换非法。"""


class VisionCoordinateMapper:
    def __init__(
        self,
        coordinate: VisionFrameCoordinate,
        bound: BoundWindow,
    ) -> None:
        self.coordinate = coordinate
        self.bound = bound
        self._transformer = CoordinateTransformer(bound)

    def frame_to_client_logical(self, x: float, y: float) -> tuple[float, float]:
        """帧像素坐标 → 客户区逻辑坐标。"""
        if self.coordinate.target_space is not CoordinateSpace.CLIENT_LOGICAL_SPACE:
            raise VisionCoordinateError(
                f"目标坐标系不支持: {self.coordinate.target_space.value}"
            )
        if self.coordinate.source_space is CoordinateSpace.SCREEN_SPACE:
            return self._transformer.screen_to_client(
                x + self.coordinate.offset_x,
                y + self.coordinate.offset_y,
            )
        if self.coordinate.source_space is CoordinateSpace.CLIENT_SPACE:
            return (
                x / self.coordinate.dpi_scale,
                y / self.coordinate.dpi_scale,
            )
        raise VisionCoordinateError(
            f"源坐标系不支持: {self.coordinate.source_space.value}"
        )

    def frame_to_screen(self, x: float, y: float) -> tuple[float, float]:
        """帧像素坐标 → 屏幕物理坐标。"""
        if self.coordinate.source_space is CoordinateSpace.SCREEN_SPACE:
            return (
                x + self.coordinate.offset_x,
                y + self.coordinate.offset_y,
            )
        return self._transformer.client_to_screen(
            x / self.coordinate.dpi_scale,
            y / self.coordinate.dpi_scale,
        )

    def map_bbox(self, bbox: OCRBBox) -> MappedBBox:
        """OCR bbox(帧像素)→ 客户区逻辑 bbox。"""
        left, top = self.frame_to_client_logical(bbox.left, bbox.top)
        right, bottom = self.frame_to_client_logical(
            bbox.left + bbox.width,
            bbox.top + bbox.height,
        )
        return MappedBBox(
            left=left,
            top=top,
            width=right - left,
            height=bottom - top,
        )
