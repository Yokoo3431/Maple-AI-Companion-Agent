"""WorldKnowledgeImporter:JSON/YAML/dict -> MapGraph(数据驱动,可版本管理)。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import (
    MapConnectionReference,
    MapConnectionType,
    MapNodeReference,
)
from maple_agent.world_knowledge.relation import MapRelationBuilder


class WorldKnowledgeImporter:
    """导入外部结构化地图数据(不绑定单一来源)。"""

    @staticmethod
    def import_data(
        data: dict | str,
        *,
        source: str = "external",
    ) -> MapGraph:
        payload = WorldKnowledgeImporter._parse(data)
        graph = MapGraph()
        for index, item in enumerate(payload.get("maps", [])):
            name = str(item.get("name", ""))
            if not name:
                continue
            map_id = str(
                item.get(
                    "map_id",
                    f"map_{index:09d}",
                )
            )
            graph.add_node(
                MapNodeReference(
                    map_id=map_id,
                    map_name=name,
                    aliases=[
                        str(alias)
                        for alias in item.get("aliases", [])
                    ],
                    region=str(item.get("region", "")),
                    map_type=str(item.get("type", "")),
                    description=str(item.get("description", "")),
                    npc_references=[
                        str(npc)
                        for npc in item.get("npcs", [])
                    ],
                    monster_references=[
                        str(monster)
                        for monster in item.get("monsters", [])
                    ],
                    quest_references=[
                        str(quest)
                        for quest in item.get("quests", [])
                    ],
                    portal_references=[
                        str(portal)
                        for portal in item.get("portals", [])
                    ],
                    confidence=float(
                        item.get("confidence", 0.9)
                    ),
                )
            )
        for connection in MapRelationBuilder.build(
            payload.get("connections", [])
        ):
            if (
                graph.find_map(connection.source_map) is not None
                and graph.find_map(connection.target_map) is not None
            ):
                graph.add_connection(connection)
        return graph

    @staticmethod
    def import_file(path: str | Path) -> MapGraph:
        content = Path(path).read_text(encoding="utf-8")
        suffix = Path(path).suffix.lower()
        if suffix in (".yaml", ".yml"):
            payload = yaml.safe_load(content)
        else:
            payload = json.loads(content)
        return WorldKnowledgeImporter.import_data(
            payload,
            source=str(path),
        )

    @staticmethod
    def import_from_dataset(
        dataset: KnowledgeDataset,
    ) -> tuple[MapGraph, list[str]]:
        """World-specific Adapter:复用 Generic Import Pipeline 产物构建 MapGraph。

        不重复 JSON/YAML 解析与校验;未知关系类型跳过并返回 warnings,不静默 PORTAL。
        """
        graph = MapGraph()
        by_id: dict[str, str] = {}
        for map_node in dataset.maps:
            map_id = str(map_node.map_id)
            by_id[map_id] = map_node.name
            graph.add_node(
                MapNodeReference(
                    map_id=map_id,
                    map_name=map_node.name,
                    aliases=list(map_node.aliases),
                    region=getattr(map_node, "region", ""),
                    map_type="",
                    description="",
                    confidence=0.9,
                )
            )
        warnings: list[str] = []
        for relation in dataset.relations:
            if relation.source != "map" or relation.target != "map":
                continue
            source_name = by_id.get(str(relation.source_id))
            target_name = by_id.get(str(relation.target_id))
            if not source_name or not target_name:
                warnings.append(
                    f"dangling map relation: "
                    f"{relation.source_id}->{relation.target_id}"
                )
                continue
            try:
                connection_type = MapConnectionType(
                    relation.relation_type.value
                )
            except ValueError:
                warnings.append(
                    f"unknown relation type skipped: "
                    f"{relation.relation_type.value}"
                )
                continue
            graph.add_connection(
                MapConnectionReference(
                    source_map=source_name,
                    target_map=target_name,
                    connection_type=connection_type,
                    confidence=getattr(relation, "confidence", 0.9),
                )
            )
        return graph, warnings

    @staticmethod
    def _parse(data: dict | str) -> dict[str, Any]:
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            loaded = yaml.safe_load(data)
            return loaded if isinstance(loaded, dict) else {}
