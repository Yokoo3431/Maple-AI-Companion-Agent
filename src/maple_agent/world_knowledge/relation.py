"""MapRelationBuilder:原始连接数据 -> MapConnectionReference(确定性)。"""

from __future__ import annotations

from maple_agent.world_knowledge.models import (
    MapConnectionReference,
    MapConnectionType,
)


class MapRelationBuilder:
    """把数据驱动的连接条目转为强类型连接参考。"""

    @staticmethod
    def build(
        connections: list[dict],
    ) -> list[MapConnectionReference]:
        built: list[MapConnectionReference] = []
        for item in connections or []:
            source = str(item.get("from", item.get("source", "")))
            target = str(item.get("to", item.get("target", "")))
            if not source or not target:
                continue
            try:
                connection_type = MapConnectionType(
                    item.get("type", "PORTAL")
                )
            except ValueError:
                connection_type = MapConnectionType.PORTAL
            built.append(
                MapConnectionReference(
                    source_map=source,
                    target_map=target,
                    connection_type=connection_type,
                    direction_reference=item.get(
                        "direction_reference",
                        {},
                    ),
                    confidence=float(
                        item.get("confidence", 0.9)
                    ),
                )
            )
        return built
