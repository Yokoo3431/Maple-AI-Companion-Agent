"""MapleWorldContextBuilder:世界上下文聚合(只读)。"""

from __future__ import annotations

from maple_agent.environment.models import EnvironmentState
from maple_agent.maple_context.models import MapleWorldContext
from maple_agent.world_model.models import (
    EnvironmentEvent,
    PredictedEnvironmentState,
)


class MapleWorldContextBuilder:
    """聚合环境状态 / 世界预测 / 事件 / 风险。"""

    def build(
        self,
        *,
        environment_state: EnvironmentState | None = None,
        world_prediction: PredictedEnvironmentState | None = None,
        world_events: list[EnvironmentEvent] | None = None,
        environment_risk: str = "",
    ) -> MapleWorldContext:
        location = (
            environment_state.location
            if environment_state is not None
            else ""
        )
        entities = (
            list(environment_state.visible_entities)
            if environment_state is not None
            else []
        )
        events = [
            f"{event.event_type.value}: {event.detail}"
            for event in (world_events or [])
        ]
        confidence = self._confidence(
            environment_state,
            world_prediction,
        )
        return MapleWorldContext(
            location=location,
            environment_state=environment_state,
            world_prediction=world_prediction,
            visible_entities=entities,
            world_events=events,
            environment_risk=environment_risk,
            confidence=confidence,
        )

    @staticmethod
    def _confidence(
        environment_state: EnvironmentState | None,
        world_prediction: PredictedEnvironmentState | None,
    ) -> float:
        values: list[float] = []
        if environment_state is not None:
            values.append(environment_state.confidence)
        if world_prediction is not None:
            values.append(world_prediction.confidence)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
