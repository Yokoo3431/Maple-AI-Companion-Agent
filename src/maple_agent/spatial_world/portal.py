"""PortalRegistry:传送门跨地图索引与位置查询(确定性)。"""

from __future__ import annotations

from maple_agent.spatial_world.models import PortalReference


class PortalRegistry:
    """聚合全部传送门并提供查询。"""

    def __init__(self) -> None:
        self._portals: dict[str, PortalReference] = {}

    def register(self, portal: PortalReference) -> None:
        self._portals[portal.portal_id] = portal

    def register_many(
        self,
        portals: list[PortalReference],
    ) -> None:
        for portal in portals:
            self.register(portal)

    def find_by_map(self, map_name: str) -> list[PortalReference]:
        return [
            portal
            for portal in self._portals.values()
            if portal.source_map == map_name
        ]

    def find_by_id(self, portal_id: str) -> PortalReference | None:
        return self._portals.get(portal_id)

    def resolve_position(
        self,
        portal_id: str,
    ) -> dict:
        portal = self._portals.get(portal_id)
        return (
            dict(portal.position_reference)
            if portal is not None
            else {}
        )

    def count(self) -> int:
        return len(self._portals)
