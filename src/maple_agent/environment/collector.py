"""EnvironmentCollector:Observation + Knowledge -> EnvironmentState(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.context.models import KnowledgeState
from maple_agent.environment.models import EnvironmentState
from maple_agent.logging_setup import new_id
from maple_agent.observation.models import ObservationState
from maple_agent.providers.knowledge import KnowledgeProvider


class EnvironmentCollector:
    """把观察与知识组装为结构化环境状态。"""

    _RESOURCE_KEYWORDS = ("树液", "木柴", "矿石", "药水")

    def __init__(
        self,
        *,
        knowledge: KnowledgeProvider | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.last_state: EnvironmentState | None = None

    def collect(
        self,
        *,
        observation_state: ObservationState,
        knowledge_state: KnowledgeState | None = None,
        trace_id: str = "",
    ) -> EnvironmentState:
        location = observation_state.map_name
        entities = list(observation_state.visible_entities)
        resources = self._resources(observation_state)
        conditions = self._conditions(observation_state)
        world_context = self._world_context(
            location,
            entities,
            conditions,
        )
        state = EnvironmentState(
            environment_id=new_id(),
            timestamp=datetime.now(UTC),
            location=location,
            visible_entities=entities,
            resources=resources,
            conditions=conditions,
            world_context=world_context,
            confidence=observation_state.confidence,
        )
        self.last_state = state
        return state

    def _resources(self, observation_state: ObservationState) -> list[str]:
        text = " ".join(observation_state.observations)
        resources: list[str] = []
        if self.knowledge is not None:
            try:
                data = getattr(self.knowledge, "data", None)
                items = getattr(data, "items", None)
                if items:
                    for item in items:
                        if item.name and item.name in text:
                            resources.append(item.name)
            except Exception:
                pass
        for keyword in self._RESOURCE_KEYWORDS:
            if keyword in text and keyword not in resources:
                resources.append(keyword)
        return resources

    @staticmethod
    def _conditions(observation_state: ObservationState) -> dict:
        return {
            "observed_count": len(observation_state.observations),
            "entity_count": len(observation_state.visible_entities),
            "confidence": observation_state.confidence,
        }

    @staticmethod
    def _world_context(
        location: str,
        entities: list[str],
        conditions: dict,
    ) -> str:
        location_text = location or "未知区域"
        entity_text = "、".join(entities) if entities else "无可见实体"
        return (
            f"当前位于 {location_text},可见实体: {entity_text},"
            f"观察 {conditions.get('observed_count', 0)} 条"
        )
