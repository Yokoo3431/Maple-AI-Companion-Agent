"""FusionService:Observation → KnowledgeProvider → WorldState。"""

from __future__ import annotations

import logging

from maple_agent.fusion.models import WorldState
from maple_agent.knowledge.models import MapInfo
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.vision.models import Observation

logger = logging.getLogger("maple_agent.fusion")


class FusionService:
    """把 Vision 的 Observation 与知识库关联,生成 WorldState。"""

    def __init__(self, knowledge: KnowledgeProvider) -> None:
        self.knowledge = knowledge

    def fuse(
        self,
        observations: list[Observation],
        *,
        trace_id: str | None = None,
    ) -> WorldState:
        with TraceContext(trace_id=trace_id) as trace:
            map_name, map_confidence = self._resolve_map(observations, trace.trace_id)
            current_map = (
                self.knowledge.get_map(map_name, trace_id=trace.trace_id)
                if map_name
                else None
            )
            npcs: list = []
            monsters: list = []
            if current_map is not None:
                npcs = self.knowledge.get_npcs_by_map(
                    current_map.map_id, trace_id=trace.trace_id
                )
                monsters = self.knowledge.get_monsters_by_map(
                    current_map.map_id, trace_id=trace.trace_id
                )
            world = WorldState(
                current_map=current_map,
                known_npcs=npcs,
                known_monsters=monsters,
                confidence=round(map_confidence, 4),
                trace_id=trace.trace_id,
            )
            logger.info(
                "fusion complete: map=%s confidence=%s npcs=%d monsters=%d",
                current_map.name if current_map else None,
                world.confidence,
                len(npcs),
                len(monsters),
            )
            return world

    def _resolve_map(
        self,
        observations: list[Observation],
        trace_id: str,
    ) -> tuple[str | None, float]:
        """优先取 map_name 元素;否则用文本 Observation 经知识库别名解析。"""
        for obs in observations:
            if obs.element == "map_name" and isinstance(obs.normalized_value, str):
                return obs.normalized_value, obs.confidence
        for obs in observations:
            if obs.type == "text" and obs.normalized_value:
                resolved = self.knowledge.resolve_alias(
                    str(obs.normalized_value),
                    trace_id=trace_id,
                )
                if resolved:
                    return resolved, obs.confidence
        return None, 0.0

    def map_for(
        self,
        map_name: str,
        *,
        trace_id: str | None = None,
    ) -> MapInfo | None:
        """按名称(含别名)直接查地图。"""
        return self.knowledge.get_map(map_name, trace_id=trace_id)
