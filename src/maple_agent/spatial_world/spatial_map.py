"""SpatialMapStore:地图空间数据存储与查询(确定性)。"""

from __future__ import annotations

from maple_agent.spatial_world.models import (
    PortalReference,
    SpatialMapReference,
)


class SpatialMapStore:
    """按地图 id/名称索引空间数据。"""

    def __init__(self) -> None:
        self._maps: dict[str, SpatialMapReference] = {}

    @classmethod
    def from_data(cls, data: dict) -> SpatialMapStore:
        store = cls()
        for index, item in enumerate(data.get("maps", [])):
            name = str(item.get("name", ""))
            if not name:
                continue
            map_id = str(
                item.get("map_id", f"spatial_map_{index:09d}")
            )
            portals = [
                PortalReference(
                    portal_id=str(portal.get("portal_id", f"portal_{i}")),
                    source_map=name,
                    target_map=str(portal.get("target", "")),
                    position_reference={
                        "x": int(portal.get("x", 0)),
                        "y": int(portal.get("y", 0)),
                    },
                    direction_reference=portal.get(
                        "direction_reference",
                        {},
                    ),
                    confidence=float(portal.get("confidence", 0.9)),
                )
                for i, portal in enumerate(item.get("portals", []))
            ]
            store.add_map(
                SpatialMapReference(
                    map_id=map_id,
                    map_name=name,
                    width_reference=int(item.get("width", 0)),
                    height_reference=int(item.get("height", 0)),
                    platforms=list(item.get("platforms", [])),
                    portals=portals,
                    npc_locations=list(item.get("npcs", [])),
                    monster_zones=list(item.get("monster_zones", [])),
                    quest_zones=list(item.get("quest_zones", [])),
                    confidence=float(item.get("confidence", 0.9)),
                )
            )
        return store

    def add_map(self, spatial_map: SpatialMapReference) -> None:
        self._maps[spatial_map.map_id] = spatial_map

    def find_map(self, name: str) -> SpatialMapReference | None:
        normalized = name.strip().lower()
        for spatial_map in self._maps.values():
            if spatial_map.map_name.strip().lower() == normalized:
                return spatial_map
        return None

    def find_portals(self, map_name: str) -> list[PortalReference]:
        spatial_map = self.find_map(map_name)
        return list(spatial_map.portals) if spatial_map is not None else []

    def find_npc_locations(self, map_name: str) -> list[dict]:
        spatial_map = self.find_map(map_name)
        return (
            list(spatial_map.npc_locations)
            if spatial_map is not None
            else []
        )

    def find_monster_zones(self, map_name: str) -> list[dict]:
        spatial_map = self.find_map(map_name)
        return (
            list(spatial_map.monster_zones)
            if spatial_map is not None
            else []
        )

    def find_quest_zones(self, map_name: str) -> list[dict]:
        spatial_map = self.find_map(map_name)
        return (
            list(spatial_map.quest_zones)
            if spatial_map is not None
            else []
        )

    def map_count(self) -> int:
        return len(self._maps)
