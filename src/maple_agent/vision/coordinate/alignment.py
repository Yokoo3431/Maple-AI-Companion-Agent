"""VisionAlignmentService:窗口绑定 + 帧尺寸 → VisionFrameCoordinate。"""

from __future__ import annotations

from maple_agent.vision.coordinate.models import (
    CoordinateSpace,
    VisionFrameCoordinate,
)
from maple_agent.window.binding import BoundWindow


class VisionAlignmentService:
    def align(
        self,
        *,
        frame_width: int,
        frame_height: int,
        bound: BoundWindow,
        source_space: CoordinateSpace = CoordinateSpace.CLIENT_SPACE,
        target_space: CoordinateSpace = CoordinateSpace.CLIENT_LOGICAL_SPACE,
        trace_id: str = "",
    ) -> VisionFrameCoordinate:
        offset_x, offset_y = 0.0, 0.0
        if source_space is CoordinateSpace.SCREEN_SPACE:
            offset_x, offset_y = (
                float(bound.client_offset[0]),
                float(bound.client_offset[1]),
            )
        return VisionFrameCoordinate(
            frame_width=frame_width,
            frame_height=frame_height,
            source_space=source_space,
            target_space=target_space,
            dpi_scale=bound.dpi_scale,
            offset_x=offset_x,
            offset_y=offset_y,
            trace_id=trace_id,
        )
