"""WorldKnowledgeImporter:JSON/YAML/dict -> MapGraph(数据驱动,可版本管理)。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import MapNodeReference
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
    def _parse(data: dict | str) -> dict[str, Any]:
        if isinstance(data, dict):
            return data
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            loaded = yaml.safe_load(data)
            return loaded if isinstance(loaded, dict) else {}
