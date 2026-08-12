"""ObservationBuilder:视觉观察构建辅助(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.logging_setup import new_id
from maple_agent.perception.models import (
    ObservationSource,
    VisualObservation,
)


class ObservationBuilder:
    """构造 VisualObservation。"""

    @staticmethod
    def build(
        *,
        source: ObservationSource = ObservationSource.MOCK_SCREENSHOT,
        location: str = "",
        visible_entities: list[str] | None = None,
        ui_state: str = "",
        confidence: float = 0.9,
    ) -> VisualObservation:
        detected = list(visible_entities or [])
        if location:
            detected.append(location)
        return VisualObservation(
            observation_id=new_id(),
            source=source,
            timestamp=datetime.now(UTC),
            image_reference="mock://screenshot",
            resolution={"width": 800, "height": 600},
            confidence=confidence,
            detected_elements=detected,
            context={
                "location": location,
                "ui_state": ui_state,
            },
        )
