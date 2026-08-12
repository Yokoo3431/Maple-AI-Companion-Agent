"""Spatial World Model 层(Phase 11-D,空间认知,只读,不执行导航)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.spatial_world.location import LocationResolver
from maple_agent.spatial_world.models import (
    PortalReference,
    SpatialMapReference,
    SpatialWorldReference,
)
from maple_agent.spatial_world.portal import PortalRegistry
from maple_agent.spatial_world.resolver import SpatialWorldBuilder
from maple_agent.spatial_world.spatial_map import SpatialMapStore
from maple_agent.spatial_world.validator import (
    SpatialWorldValidationResult,
    SpatialWorldValidator,
    SpatialWorldVerdict,
)


def load_demo_spatial_map() -> dict:
    """读取内置演示空间地图数据集。"""
    path = Path(__file__).parent / "data" / "demo_spatial_map.json"
    return json.loads(path.read_text(encoding="utf-8"))


def save_spatial_world_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    current_map: str,
    portals: list[PortalReference],
    locations: list[dict],
    validation: str,
) -> None:
    """写入 spatial_world_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "map": current_map,
        "portals": [
            {
                "portal_id": portal.portal_id,
                "from": portal.source_map,
                "to": portal.target_map,
                **portal.position_reference,
            }
            for portal in portals
        ],
        "locations": locations,
        "validation": validation,
    }
    (directory / "spatial_world_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "LocationResolver",
    "PortalReference",
    "PortalRegistry",
    "SpatialMapReference",
    "SpatialMapStore",
    "SpatialWorldBuilder",
    "SpatialWorldReference",
    "SpatialWorldValidationResult",
    "SpatialWorldValidator",
    "SpatialWorldVerdict",
    "load_demo_spatial_map",
    "save_spatial_world_trace",
]
