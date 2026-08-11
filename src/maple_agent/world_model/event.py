"""EnvironmentEventDetector:环境变化事件识别(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.world_model.models import (
    EnvironmentEvent,
    EnvironmentTransition,
    WorldEventType,
)


class EnvironmentEventDetector:
    """从状态转换识别事件:出现/消失/位置/资源/条件变化。"""

    def detect(
        self,
        *,
        transition: EnvironmentTransition,
    ) -> list[EnvironmentEvent]:
        events: list[EnvironmentEvent] = []
        before = transition.from_state
        after = transition.to_state
        if before is None or after is None:
            return events
        timestamp = datetime.now(UTC)
        before_entities = set(before.visible_entities)
        after_entities = set(after.visible_entities)
        for entity in sorted(after_entities - before_entities):
            events.append(
                EnvironmentEvent(
                    event_type=WorldEventType.ENTITY_APPEARED,
                    detail=f"{entity} 出现",
                    timestamp=timestamp,
                )
            )
        for entity in sorted(before_entities - after_entities):
            events.append(
                EnvironmentEvent(
                    event_type=WorldEventType.ENTITY_DISAPPEARED,
                    detail=f"{entity} 消失",
                    timestamp=timestamp,
                )
            )
        if before.location != after.location:
            events.append(
                EnvironmentEvent(
                    event_type=WorldEventType.LOCATION_CHANGED,
                    detail=(
                        f"{before.location or '-'} -> "
                        f"{after.location or '-'}"
                    ),
                    timestamp=timestamp,
                )
            )
        if set(before.resources) != set(after.resources):
            events.append(
                EnvironmentEvent(
                    event_type=WorldEventType.RESOURCE_CHANGED,
                    detail=(
                        f"{before.resources} -> {after.resources}"
                    ),
                    timestamp=timestamp,
                )
            )
        if before.conditions != after.conditions:
            events.append(
                EnvironmentEvent(
                    event_type=WorldEventType.CONDITION_CHANGED,
                    detail="conditions 变化",
                    timestamp=timestamp,
                )
            )
        return events
