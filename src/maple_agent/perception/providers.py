"""VisionProvider 抽象 + Mock 实现(无真实截图依赖)。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from maple_agent.logging_setup import new_id
from maple_agent.perception.models import (
    ObservationSource,
    PerceivedEntity,
    VisualObservation,
)


@runtime_checkable
class VisionProvider(Protocol):
    """视觉提供者契约(未来可接入真实截图)。"""

    def capture(self, *, trace_id: str = "") -> VisualObservation: ...

    def analyze(
        self,
        observation: VisualObservation,
    ) -> list[PerceivedEntity]: ...


class MockVisionProvider:
    """Mock 实现:固定生成截图观察。"""

    def __init__(
        self,
        *,
        location: str = "",
        visible_entities: list[str] | None = None,
        ui_state: str = "",
        confidence: float = 0.9,
    ) -> None:
        self.location = location
        self.visible_entities = visible_entities or []
        self.ui_state = ui_state
        self.confidence = confidence
        self.call_count = 0

    def capture(self, *, trace_id: str = "") -> VisualObservation:
        self.call_count += 1
        detected = list(self.visible_entities)
        if self.location:
            detected.append(self.location)
        return VisualObservation(
            observation_id=new_id(),
            source=ObservationSource.MOCK_SCREENSHOT,
            timestamp=datetime.now(UTC),
            image_reference="mock://screenshot",
            resolution={"width": 800, "height": 600},
            confidence=self.confidence,
            detected_elements=detected,
            context={
                "location": self.location,
                "ui_state": self.ui_state,
            },
        )

    def analyze(
        self,
        observation: VisualObservation,
    ) -> list[PerceivedEntity]:
        # 完整分析由 ObservationAnalyzer 提供;此处返回空占位
        return []
