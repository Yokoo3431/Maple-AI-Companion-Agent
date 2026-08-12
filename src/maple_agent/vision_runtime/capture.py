"""ScreenshotProvider 抽象 + Mock 实现(无真实截图依赖)。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from maple_agent.logging_setup import new_id
from maple_agent.vision_runtime.models import (
    CaptureReference,
    VisionFrame,
    VisionSource,
)


@runtime_checkable
class ScreenshotProvider(Protocol):
    """窗口截图提供者契约(未来可接入真实窗口截图)。"""

    def capture(self, *, trace_id: str = "") -> VisionFrame: ...

    def capture_reference(self) -> CaptureReference | None: ...


class MockScreenshotProvider:
    """Mock 实现:按场景配置生成一帧视觉快照。"""

    def __init__(
        self,
        *,
        map_name: str = "",
        npcs: list[str] | None = None,
        monsters: list[str] | None = None,
        items: list[str] | None = None,
        ui_elements: list[str] | None = None,
        hp_ratio: float | None = None,
        mp_ratio: float | None = None,
        quests: list[str] | None = None,
        confidence: float = 0.9,
        window_title: str = "MapleStory",
        width: int = 800,
        height: int = 600,
    ) -> None:
        self.map_name = map_name
        self.npcs = list(npcs or [])
        self.monsters = list(monsters or [])
        self.items = list(items or [])
        self.ui_elements = list(ui_elements or [])
        self.hp_ratio = hp_ratio
        self.mp_ratio = mp_ratio
        self.quests = list(quests or [])
        self.confidence = confidence
        self.window_title = window_title
        self.window_rect = {"left": 0, "top": 0, "width": width, "height": height}
        self.call_count = 0
        self.last_capture: CaptureReference | None = None

    def capture(self, *, trace_id: str = "") -> VisionFrame:
        self.call_count += 1
        frame = VisionFrame(
            frame_id=new_id(),
            timestamp=datetime.now(UTC),
            source=VisionSource.MOCK_SCREENSHOT,
            image_reference=f"mock://frame/{new_id()}",
            confidence=self.confidence,
        )
        self.last_capture = CaptureReference(
            capture_id=new_id(),
            source="mock",
            window_title=self.window_title,
            window_rect=dict(self.window_rect),
            timestamp=frame.timestamp,
            confidence=self.confidence,
        )
        return frame

    def capture_reference(self) -> CaptureReference | None:
        return self.last_capture

    def mock_ocr_text(self) -> str:
        """生成与场景配置一致的 Mock OCR 文本(确定性)。"""
        lines: list[str] = []
        if self.map_name:
            lines.append(f"地图:{self.map_name}")
        for name in self.npcs:
            lines.append(f"NPC:{name}")
        for name in self.monsters:
            lines.append(f"MONSTER:{name}")
        for name in self.items:
            lines.append(f"ITEM:{name}")
        for name in self.ui_elements:
            lines.append(f"UI:{name}")
        if self.hp_ratio is not None:
            lines.append(f"HP:{int(round(self.hp_ratio * 100))}%")
        if self.mp_ratio is not None:
            lines.append(f"MP:{int(round(self.mp_ratio * 100))}%")
        for name in self.quests:
            lines.append(f"任务:{name}")
        return "\n".join(lines)
