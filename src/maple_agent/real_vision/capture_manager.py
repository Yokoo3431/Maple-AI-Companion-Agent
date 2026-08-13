"""CaptureManager:WGC 优先 + 条件感知 failover(Phase 13-I.2)。

规则:
- Windows 且 WGC available -> 首选 WGC;
- WGC failure + FOREGROUND/BACKGROUND_VISIBLE -> ImageGrab fallback;
- WGC failure + BACKGROUND_OCCLUDED -> 不静默 fallback(ImageGrab 可能捕获遮挡内容);
- MINIMIZED -> NOT_SUPPORTED,不尝试;
- WGC unavailable -> ImageGrab(标记可能 occluded,不宣称 WGC 成功)。
"""

from __future__ import annotations

from maple_agent.hybrid_vision.models import CaptureCondition
from maple_agent.real_vision.capture import WindowsScreenshotProvider
from maple_agent.real_vision.wgc import WindowsGraphicsCaptureProvider
from maple_agent.vision_runtime.models import VisionFrame


class CaptureManager:
    """按条件选择捕获 provider,并诚实报告来源与原因。"""

    def __init__(
        self,
        *,
        window_title: str = "MapleStory",
        save_dir: str | None = None,
    ) -> None:
        self.wgc = WindowsGraphicsCaptureProvider(
            window_title=window_title,
            save_dir=save_dir,
        )
        self.imagegrab = WindowsScreenshotProvider(
            window_title=window_title,
            save_dir=save_dir,
        )
        self.preferred = "wgc" if self.wgc.available else "imagegrab"
        self.last_provider = ""
        self.last_reason = ""

    def capture(
        self,
        *,
        condition: str | None = None,
        trace_id: str = "",
    ) -> tuple[VisionFrame, str, str]:
        """返回 (frame, provider, reason)。失败帧 confidence=0,不伪造成功。"""
        if condition == CaptureCondition.MINIMIZED.value:
            self.last_provider = "none"
            self.last_reason = "minimized-not-supported"
            return (
                self._unavailable("unavailable://minimized-not-supported"),
                "none",
                self.last_reason,
            )
        if self.wgc.available:
            frame = self.wgc.capture(trace_id=trace_id)
            if frame.confidence > 0:
                self.last_provider = "wgc"
                self.last_reason = "wgc-ok"
                return frame, "wgc", self.last_reason
            if condition == CaptureCondition.BACKGROUND_OCCLUDED.value:
                # 遮挡场景 WGC 失败:不得用 ImageGrab 假装成功
                self.last_provider = "wgc"
                self.last_reason = "occluded-wgc-failed-no-fallback"
                return frame, "wgc", self.last_reason
            if condition == CaptureCondition.BACKGROUND_VISIBLE.value:
                self.last_provider = "imagegrab"
                self.last_reason = "wgc-failed-imagegrab-fallback"
                fallback = self.imagegrab.capture(trace_id=trace_id)
                return fallback, "imagegrab", self.last_reason
            # FOREGROUND / 未指定
            self.last_provider = "imagegrab"
            self.last_reason = "wgc-failed-imagegrab-fallback"
            fallback = self.imagegrab.capture(trace_id=trace_id)
            return fallback, "imagegrab", self.last_reason
        self.last_provider = "imagegrab"
        frame = self.imagegrab.capture(trace_id=trace_id)
        if condition == CaptureCondition.BACKGROUND_OCCLUDED.value:
            self.last_reason = "wgc-unavailable-imagegrab-may-be-occluded"
        else:
            self.last_reason = "wgc-unavailable-imagegrab"
        return frame, "imagegrab", self.last_reason

    @staticmethod
    def _unavailable(reference: str) -> VisionFrame:
        from datetime import UTC, datetime

        from maple_agent.logging_setup import new_id
        from maple_agent.vision_runtime.models import VisionSource

        return VisionFrame(
            frame_id=new_id(),
            timestamp=datetime.now(UTC),
            source=VisionSource.WINDOW_CAPTURE_REFERENCE,
            image_reference=reference,
            confidence=0.0,
        )
