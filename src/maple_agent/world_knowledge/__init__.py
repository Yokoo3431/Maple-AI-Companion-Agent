"""Maple World Knowledge 层(Phase 11-C,世界知识图谱,只读,无导航执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.world_knowledge.importer import WorldKnowledgeImporter
from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import (
    MapConnectionReference,
    MapConnectionType,
    MapNodeReference,
    WorldKnowledgeReference,
)
from maple_agent.world_knowledge.relation import MapRelationBuilder
from maple_agent.world_knowledge.resolver import WorldKnowledgeResolver
from maple_agent.world_knowledge.validator import (
    WorldKnowledgeValidationResult,
    WorldKnowledgeValidator,
    WorldKnowledgeVerdict,
)


def load_demo_world_map() -> dict:
    """读取内置演示世界地图数据集。"""
    path = Path(__file__).parent / "data" / "demo_world_map.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_world_knowledge_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    current_map: str,
    known_maps: list[str],
    connections: list[MapConnectionReference],
    validation: str,
) -> None:
    """写入 world_knowledge_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "current_map": current_map,
        "known_maps": known_maps,
        "connections": [
            {
                "from": connection.source_map,
                "to": connection.target_map,
            }
            for connection in connections
        ],
        "validation": validation,
    }
    (directory / "world_knowledge_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "MapConnectionReference",
    "MapConnectionType",
    "MapGraph",
    "MapNodeReference",
    "MapRelationBuilder",
    "WorldKnowledgeImporter",
    "WorldKnowledgeReference",
    "WorldKnowledgeResolver",
    "WorldKnowledgeValidationResult",
    "WorldKnowledgeValidator",
    "WorldKnowledgeVerdict",
    "load_demo_world_map",
    "save_world_knowledge_trace",
]
