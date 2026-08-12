"""WorldTopologyValidator:地图拓扑校验(确定性,不自动双向化)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.knowledge_quality.canonical import CanonicalMapper
from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import MapConnectionType


class TopologyValidationResult(BaseModel):
    """拓扑校验结果。"""

    valid: bool = False
    edge_count: int = 0
    dangling_source: int = 0
    dangling_target: int = 0
    duplicate_edges: int = 0
    self_loops: int = 0
    invalid_relation_types: int = 0
    invalid_confidence: int = 0
    unresolved_canonical: int = 0
    one_way_edges: int = 0
    bidirectional_edges: int = 0
    issues: list[str] = Field(default_factory=list)


class WorldTopologyValidator:
    """检查 dangling / 重复 / 自环 / 非法类型 / canonical 未解析。"""

    def validate(
        self,
        graph: MapGraph,
        *,
        canonical_mapper: CanonicalMapper | None = None,
    ) -> TopologyValidationResult:
        known = set(graph.known_map_names())
        connections = graph.all_connections()
        seen: set[tuple[str, str, str]] = set()
        directed: set[tuple[str, str]] = set()
        result = TopologyValidationResult(edge_count=len(connections))
        for connection in connections:
            source = connection.source_map
            target = connection.target_map
            if source not in known:
                result.dangling_source += 1
                result.issues.append(f"dangling source: {source}")
            if target not in known:
                result.dangling_target += 1
                result.issues.append(f"dangling target: {target}")
            key = (source, target, connection.connection_type.value)
            if key in seen:
                result.duplicate_edges += 1
                result.issues.append(f"duplicate edge: {key}")
            seen.add(key)
            if source == target:
                result.self_loops += 1
                result.issues.append(f"self-loop: {source}")
            try:
                connection_type = MapConnectionType(
                    connection.connection_type.value
                )
            except ValueError:
                connection_type = None
            if connection_type is None:
                result.invalid_relation_types += 1
                result.issues.append(
                    f"invalid relation type: {connection.connection_type}"
                )
            if not (0 <= connection.confidence <= 1):
                result.invalid_confidence += 1
                result.issues.append(
                    f"invalid confidence: {connection.confidence}"
                )
            if canonical_mapper is not None:
                if canonical_mapper.lookup(source) is None:
                    result.unresolved_canonical += 1
                if canonical_mapper.lookup(target) is None:
                    result.unresolved_canonical += 1
            directed.add((source, target))
        for source, target in directed:
            if (target, source) in directed:
                result.bidirectional_edges += 1
            else:
                result.one_way_edges += 1
        result.valid = not (
            result.dangling_source
            or result.dangling_target
            or result.duplicate_edges
            or result.self_loops
            or result.invalid_relation_types
            or result.invalid_confidence
        )
        return result
