"""LocationResolver:NPC/Portal/Quest 区域位置查询(确定性,无 LLM)。"""

from __future__ import annotations

from maple_agent.spatial_world.portal import PortalRegistry
from maple_agent.spatial_world.spatial_map import SpatialMapStore


class LocationResolver:
    """提供空间位置参考查询。"""

    def __init__(
        self,
        store: SpatialMapStore,
        registry: PortalRegistry | None = None,
    ) -> None:
        self.store = store
        self.registry = registry or PortalRegistry()

    def find_npc_location(
        self,
        map_name: str,
        npc_name: str,
    ) -> dict | None:
        for location in self.store.find_npc_locations(map_name):
            if location.get("name") == npc_name:
                return dict(location)
        return None

    def find_portal_location(
        self,
        map_name: str,
        portal_id: str,
    ) -> dict | None:
        for portal in self.store.find_portals(map_name):
            if portal.portal_id == portal_id:
                return {
                    "portal_id": portal.portal_id,
                    "target": portal.target_map,
                    **portal.position_reference,
                }
        return None

    def find_quest_area(
        self,
        map_name: str,
        quest_name: str,
    ) -> dict | None:
        for zone in self.store.find_quest_zones(map_name):
            if zone.get("quest") == quest_name:
                return dict(zone)
        return None
