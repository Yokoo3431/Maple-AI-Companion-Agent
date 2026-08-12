"""MapStateParser:ScreenObservation + Knowledge -> MapStateReference(确定性)。"""

from __future__ import annotations

from maple_agent.game_state.models import MapStateReference
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.vision_runtime.models import ScreenObservation


class MapStateParser:
    """识别当前地图并判断是否为已知地图。"""

    def __init__(self, graph: MapleKnowledgeGraph | None = None) -> None:
        self.graph = graph

    def parse(
        self,
        observation: ScreenObservation,
    ) -> MapStateReference:
        map_name = observation.visible_map
        known = (
            self.graph is not None
            and bool(map_name)
            and self.graph.find_by_name(map_name) is not None
        )
        return MapStateReference(
            map_name=map_name,
            known_map=known,
            exits_reference=[],
        )
