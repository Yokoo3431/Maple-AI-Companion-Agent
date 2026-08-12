"""SpatialWorldBuilder:世界知识/游戏状态 -> SpatialWorldReference(只读)。"""

from __future__ import annotations

from maple_agent.game_state.models import GameStateReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.spatial_world.location import LocationResolver
from maple_agent.spatial_world.models import SpatialWorldReference
from maple_agent.spatial_world.portal import PortalRegistry
from maple_agent.spatial_world.spatial_map import SpatialMapStore
from maple_agent.world_knowledge.models import WorldKnowledgeReference


class SpatialWorldBuilder:
    """汇总当前地图的空间参考。"""

    def __init__(
        self,
        store: SpatialMapStore,
        *,
        portal_registry: PortalRegistry | None = None,
        location_resolver: LocationResolver | None = None,
    ) -> None:
        self.store = store
        self.registry = portal_registry or PortalRegistry()
        self.location_resolver = (
            location_resolver
            or LocationResolver(store, self.registry)
        )
        self.last_reference: SpatialWorldReference | None = None

    def resolve(
        self,
        *,
        world_knowledge_reference: WorldKnowledgeReference | None = None,
        game_state_reference: GameStateReference | None = None,
        maple_knowledge_reference: MapleKnowledgeReference | None = None,
    ) -> SpatialWorldReference:
        current_map = ""
        if (
            world_knowledge_reference is not None
            and world_knowledge_reference.current_map
        ):
            current_map = world_knowledge_reference.current_map
        elif (
            game_state_reference is not None
            and game_state_reference.current_map is not None
        ):
            current_map = game_state_reference.current_map.map_name
        spatial_map = self.store.find_map(current_map) if current_map else None
        portals = self.store.find_portals(current_map) if current_map else []
        self.registry.register_many(portals)
        npc_positions = (
            self.store.find_npc_locations(current_map)
            if current_map
            else []
        )
        quest_zones = (
            self.store.find_quest_zones(current_map)
            if current_map
            else []
        )
        nearby_points: list[dict] = []
        for portal in portals:
            nearby_points.append(
                {
                    "kind": "portal",
                    "name": portal.portal_id,
                    "target": portal.target_map,
                    **portal.position_reference,
                }
            )
        for npc in npc_positions:
            nearby_points.append({"kind": "npc", **dict(npc)})
        for zone in quest_zones:
            nearby_points.append({"kind": "quest_zone", **dict(zone)})
        confidence = (
            spatial_map.confidence
            if spatial_map is not None
            else (
                world_knowledge_reference.confidence
                if world_knowledge_reference is not None
                else 0.0
            )
        )
        reasoning = [
            f"当前地图: {current_map or '未知'}",
            f"传送门: {len(portals)}",
            f"NPC 位置: {len(npc_positions)}",
            f"任务区域: {len(quest_zones)}",
        ]
        reference = SpatialWorldReference(
            current_map=current_map,
            nearby_points=nearby_points,
            portals=portals,
            npc_positions=npc_positions,
            quest_targets=quest_zones,
            spatial_confidence=round(min(1.0, max(0.0, confidence)), 4),
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference
