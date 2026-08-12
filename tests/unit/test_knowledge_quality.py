"""Knowledge Quality 单测:provenance/映射/合并/拓扑/benchmark/readiness/CLI/WebUI(仅 fixtures)。"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import yaml
from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.knowledge_quality import (
    CanonicalEntityReference,
    CanonicalMapper,
    KnowledgeCoverageDenominator,
    KnowledgeImportOrchestrator,
    KnowledgeReadinessPolicy,
    KnowledgeSourceReference,
    KnowledgeSourceType,
    LocalStaticKnowledgeAdapter,
    ManualCuratedAdapter,
    MergeOutcome,
    WorldTopologyValidator,
    save_knowledge_acquisition_trace,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_vnext.models import ReadinessStatus
from maple_agent.webui.app import create_app
from maple_agent.world_knowledge.importer import WorldKnowledgeImporter
from maple_agent.world_knowledge.map_graph import MapGraph
from maple_agent.world_knowledge.models import (
    MapConnectionReference,
    MapConnectionType,
    MapNodeReference,
)
from maple_agent.world_knowledge.relation import MapRelationBuilder

REPO_ROOT = Path(__file__).resolve().parents[2]


def _graph() -> MapleKnowledgeGraph:
    graph = MapleKnowledgeGraph()
    entities, relations = load_demo_knowledge()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph


def _source(
    *,
    profile: str = "maple-v113",
    server: str = "nostalgic",
    version: str = "v1.0",
) -> KnowledgeSourceReference:
    return KnowledgeSourceReference(
        source_id="src-1",
        source_type=KnowledgeSourceType.MANUAL_CURATED,
        source_name="fixture source",
        game_profile=profile,
        server_profile=server,
        data_version=version,
        extracted_at=datetime(2026, 1, 1, tzinfo=UTC),
        imported_at=datetime(2026, 1, 1, tzinfo=UTC),
        content_hash="fixture",
        trust_level=0.5,
        confidence=0.5,
        adapter_name="ManualCuratedAdapter",
        adapter_version="1.0",
    )


def _demo_denominators() -> list[KnowledgeCoverageDenominator]:
    return [
        KnowledgeCoverageDenominator(
            source_name="fixture",
            expected_counts={
                "map": 3,
                "portal": 2,
                "npc": 1,
                "monster": 1,
                "quest": 1,
                "item": 2,
            },
        )
    ]


def _acquire_demo():
    mapper = CanonicalMapper.from_maple_graph(
        _graph(),
        game_profile="maple-v113",
        server_profile="nostalgic",
        data_version="v1.0",
    )
    orchestrator = KnowledgeImportOrchestrator(
        canonical_mapper=mapper,
        policy=KnowledgeReadinessPolicy(minimum_total_entities=5),
    )
    return orchestrator.acquire(
        _source(),
        ManualCuratedAdapter(),
        denominators=_demo_denominators(),
    )


def test_provenance_model():
    source = _source()
    assert source.source_type is KnowledgeSourceType.MANUAL_CURATED
    assert source.game_profile == "maple-v113"
    assert source.server_profile == "nostalgic"
    assert source.data_version == "v1.0"
    assert source.content_hash == "fixture"


def test_deterministic_timestamp():
    fixed = datetime(2026, 1, 1, tzinfo=UTC)
    first = _source().model_copy(
        update={"extracted_at": fixed, "imported_at": fixed}
    )
    second = _source().model_copy(
        update={"extracted_at": fixed, "imported_at": fixed}
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")


def test_local_json_adapter(tmp_path):
    payload = {
        "maps": [
            {"map_id": "m1", "name": "射手村", "aliases": ["Henesys"]}
        ]
    }
    path = tmp_path / "source.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    adapter = LocalStaticKnowledgeAdapter()
    packet = adapter.load(
        _source().model_copy(
            update={
                "source_type": KnowledgeSourceType.LOCAL_STATIC_FILE,
                "source_reference": str(path),
            }
        )
    )
    assert packet["maps"][0]["name"] == "射手村"


def test_local_yaml_adapter(tmp_path):
    path = tmp_path / "source.yaml"
    path.write_text("maps:\n  - map_id: m1\n    name: 射手村\n", encoding="utf-8")
    adapter = LocalStaticKnowledgeAdapter()
    packet = adapter.load(
        _source().model_copy(
            update={
                "source_type": KnowledgeSourceType.LOCAL_STATIC_FILE,
                "source_reference": str(path),
            }
        )
    )
    assert packet["maps"][0]["name"] == "射手村"
    assert yaml.safe_load("a: 1")["a"] == 1


def test_profile_binding():
    result = _acquire_demo()
    assert result.readiness.game_profile == "maple-v113"
    assert result.readiness.server_version == "nostalgic"
    assert result.manifest.game_profile == "maple-v113"


def test_version_binding():
    result = _acquire_demo()
    assert result.manifest.data_version == "v1.0"
    assert result.readiness.dataset_version == "v1.0"


def test_canonical_exact_mapping():
    mapper = CanonicalMapper.from_maple_graph(_graph())
    canonical_id, outcome, _ = mapper.resolve(canonical_id="map-100000000")
    assert outcome is MergeOutcome.MERGED
    assert canonical_id == "map-100000000"


def test_canonical_alias_mapping():
    mapper = CanonicalMapper.from_maple_graph(_graph())
    canonical_id, outcome, _ = mapper.resolve(name="Henesys")
    assert outcome is MergeOutcome.MERGED
    assert canonical_id == "map-100000000"


def test_canonical_unresolved():
    mapper = CanonicalMapper.from_maple_graph(_graph())
    canonical_id, outcome, _ = mapper.resolve(name="未知实体")
    assert outcome is MergeOutcome.UNRESOLVED
    assert canonical_id == ""


def test_duplicate_handling():
    packet = {
        "maps": [
            {"map_id": "m1", "name": "地图1"},
            {"map_id": "m1", "name": "地图1"},
        ]
    }
    adapter = type(
        "FakeAdapter",
        (),
        {"load": lambda self, source: packet},
    )()
    manual_dup = KnowledgeImportOrchestrator().acquire(
        _source(),
        adapter,
    )
    assert manual_dup.manifest.duplicate_count == 1


def test_conflict_handling():
    packet = {
        "maps": [
            {"map_id": "m1", "name": "地图1"},
            {"map_id": "m2", "name": "地图1"},
        ]
    }
    adapter = type(
        "FakeAdapter",
        (),
        {"load": lambda self, source: packet},
    )()
    result = KnowledgeImportOrchestrator().acquire(_source(), adapter)
    assert result.manifest.conflict_count >= 1


def test_cross_profile_no_silent_overwrite():
    packet = {
        "maps": [{"map_id": "m1", "name": "射手村"}],
        "connections": [{"from": "射手村", "to": "魔法密林"}],
    }
    adapter = type(
        "FakeAdapter",
        (),
        {"load": lambda self, source: packet},
    )()
    result_a = KnowledgeImportOrchestrator().acquire(
        _source(server="server-a"),
        adapter,
    )
    result_b = KnowledgeImportOrchestrator().acquire(
        _source(server="server-b"),
        adapter,
    )
    assert result_a.manifest.server_profile == "server-a"
    assert result_b.manifest.server_profile == "server-b"
    # 两个 profile 各自独立结果,不互相覆盖
    assert result_a.graph["maps"] == result_b.graph["maps"]


def test_generic_pipeline_reused():
    result = _acquire_demo()
    assert result.dataset is not None
    assert len(result.dataset.maps) == 3
    assert result.manifest.entity_counts["npc"] == 1


def test_world_importer_compatibility():
    dataset = _acquire_demo().dataset
    graph, warnings = WorldKnowledgeImporter.import_from_dataset(dataset)
    assert isinstance(graph, MapGraph)
    assert graph.node_count() == 3
    # 原 API 仍工作
    legacy = WorldKnowledgeImporter.import_data(
        {"maps": [{"name": "X"}], "connections": []}
    )
    assert legacy.node_count() == 1


def test_unknown_relation_not_silently_portal():
    connections = [{"from": "A", "to": "B", "type": "MYSTERY_TYPE"}]
    built, warnings = MapRelationBuilder.build_strict(connections)
    assert built == []
    assert any("unknown relation type" in warning for warning in warnings)


def test_dangling_source():
    graph = MapGraph()
    graph.add_node(MapNodeReference(map_id="m1", map_name="A"))
    graph.add_connection(
        MapConnectionReference(
            source_map="A",
            target_map="不存在",
            connection_type=MapConnectionType.PORTAL,
        )
    )
    result = WorldTopologyValidator().validate(graph)
    assert result.dangling_target == 1
    assert result.valid is False


def test_dangling_target():
    graph = MapGraph()
    graph.add_node(MapNodeReference(map_id="m1", map_name="A"))
    graph.add_connection(
        MapConnectionReference(
            source_map="B",
            target_map="A",
            connection_type=MapConnectionType.PORTAL,
        )
    )
    result = WorldTopologyValidator().validate(graph)
    assert result.dangling_source == 1


def test_duplicate_edge():
    graph = MapGraph()
    graph.add_node(MapNodeReference(map_id="m1", map_name="A"))
    graph.add_node(MapNodeReference(map_id="m2", map_name="B"))
    for _ in range(2):
        graph.add_connection(
            MapConnectionReference(
                source_map="A",
                target_map="B",
                connection_type=MapConnectionType.PORTAL,
            )
        )
    result = WorldTopologyValidator().validate(graph)
    assert result.duplicate_edges == 1


def test_one_way_relation_preserved():
    graph = MapGraph()
    graph.add_node(MapNodeReference(map_id="m1", map_name="A"))
    graph.add_node(MapNodeReference(map_id="m2", map_name="B"))
    graph.add_connection(
        MapConnectionReference(
            source_map="A",
            target_map="B",
            connection_type=MapConnectionType.PORTAL,
        )
    )
    result = WorldTopologyValidator().validate(graph)
    assert result.one_way_edges == 1
    assert result.bidirectional_edges == 0


def test_topology_validation():
    result = _acquire_demo()
    assert result.topology is not None
    assert result.topology.valid is True
    assert result.topology.edge_count == 2


def test_provenance_coverage():
    result = _acquire_demo()
    assert result.benchmark.provenance_coverage is not None
    assert 0 < result.benchmark.provenance_coverage <= 1


def test_canonical_coverage():
    result = _acquire_demo()
    assert result.benchmark.canonical_id_coverage is not None
    assert result.benchmark.canonical_id_coverage < 1.0


def test_denominator_missing_coverage_na():
    result = KnowledgeImportOrchestrator(
        policy=KnowledgeReadinessPolicy(minimum_total_entities=1)
    ).acquire(_source(), ManualCuratedAdapter(), denominators=None)
    assert result.readiness.status is ReadinessStatus.FOUNDATION_ONLY
    assert result.readiness.map_coverage == 0.0
    assert any(
        "denominator" in reason
        for reason in result.benchmark.reasons
    )


def test_benchmark_metrics():
    result = _acquire_demo()
    assert result.benchmark.total_entities >= 7
    assert result.benchmark.map_count == 3
    assert result.benchmark.validation_score is not None


def test_readiness_foundation_only():
    result = _acquire_demo()
    assert result.readiness.status is ReadinessStatus.FOUNDATION_ONLY


def test_readiness_ready_only_at_thresholds():
    maps = [
        {"map_id": f"m{i}", "name": f"地图{i}"} for i in range(10)
    ]
    npcs = [
        {"npc_id": f"n{i}", "name": f"NPC{i}"} for i in range(5)
    ]
    items = [
        {"item_id": f"it{i}", "name": f"道具{i}"} for i in range(5)
    ]
    packet = {
        "maps": maps,
        "npcs": npcs,
        "items": items,
        "connections": [
            {"from": "地图0", "to": "地图1", "type": "PORTAL"},
            {"from": "地图1", "to": "地图2", "type": "PORTAL"},
        ],
    }
    mapper = CanonicalMapper(
        [
            CanonicalEntityReference(
                canonical_id=item["map_id"],
                entity_type="MAP",
                display_name=item["name"],
            )
            for item in maps
        ]
        + [
            CanonicalEntityReference(
                canonical_id=item["npc_id"],
                entity_type="NPC",
                display_name=item["name"],
            )
            for item in npcs
        ]
        + [
            CanonicalEntityReference(
                canonical_id=item["item_id"],
                entity_type="ITEM",
                display_name=item["name"],
            )
            for item in items
        ]
    )
    orchestrator = KnowledgeImportOrchestrator(
        canonical_mapper=mapper,
        policy=KnowledgeReadinessPolicy(minimum_total_entities=20),
    )
    adapter = type(
        "FakeAdapter",
        (),
        {"load": lambda self, source: packet},
    )()
    result = orchestrator.acquire(
        _source(),
        adapter,
        denominators=[
            KnowledgeCoverageDenominator(
                source_name="fixture",
                expected_counts={
                    "map": 10,
                    "portal": 2,
                    "npc": 5,
                    "monster": 0,
                    "quest": 0,
                    "item": 5,
                },
            )
        ],
    )
    assert result.readiness.status is ReadinessStatus.READY
    assert result.benchmark.validation_score >= 0.9


def test_static_vs_dynamic_boundary():
    # 13-G 不创建第二套动态模型:world_model 仍是唯一动态层
    from maple_agent import world_model

    assert hasattr(world_model, "EnvironmentHistoryManager")
    result = _acquire_demo()
    assert result.dataset is not None
    assert not hasattr(result, "dynamic_history")


def test_spatial_canonical_reference():
    from maple_agent.spatial_world import load_demo_spatial_map

    spatial = load_demo_spatial_map()
    map_ids = {item["map_id"] for item in spatial["maps"]}
    assert "map_100000000" in map_ids
    mapper = CanonicalMapper.from_maple_graph(_graph())
    # spatial 用下划线 display id;Phase 9-D canonical 用连字符 id。
    # 名称只用于解析,canonical ID 才是身份(需经 mapping 对齐,不静默合并)。
    assert mapper.get("map_100000000") is None
    assert mapper.lookup("射手村") == "map-100000000"


def test_replay(tmp_path):
    result = _acquire_demo()
    save_knowledge_acquisition_trace(
        tmp_path,
        "trace-replay",
        manifest=result.manifest.model_dump(mode="json"),
        sources=result.source.model_dump(mode="json"),
        import_summary={"entity_counts": result.manifest.entity_counts},
        mapping_summary={"mapped": result.manifest.canonical_mapped_count},
        conflicts=[],
        benchmark=result.benchmark,
        readiness=result.readiness.model_dump(mode="json"),
        validation=result.readiness.status.value,
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "knowledge_acquisition_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["manifest"]["entity_counts"]["map"] == 3
    assert replay["readiness"]["status"] == "FOUNDATION_ONLY"


def test_webui_knowledge_quality_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    result = _acquire_demo()
    payload = {
        "dataset_version": result.readiness.dataset_version,
        "game_profile": result.readiness.game_profile,
        "server_profile": result.readiness.server_version,
        "sources": result.manifest.canonical_mapped_count,
        "total_relations": result.manifest.relation_counts.get("total", 0),
        "map_count": result.manifest.entity_counts.get("map", 0),
        "npc_count": result.manifest.entity_counts.get("npc", 0),
        "monster_count": result.manifest.entity_counts.get("monster", 0),
        "quest_count": result.manifest.entity_counts.get("quest", 0),
        "item_count": result.manifest.entity_counts.get("item", 0),
        "canonical_id_coverage": result.benchmark.canonical_id_coverage,
        "provenance_coverage": result.benchmark.provenance_coverage,
        "map_coverage": result.readiness.map_coverage,
        "portal_coverage": result.readiness.portal_coverage,
        "npc_coverage": result.readiness.npc_coverage,
        "monster_coverage": result.readiness.monster_coverage,
        "quest_coverage": result.readiness.quest_coverage,
        "item_coverage": result.readiness.item_coverage,
        "unresolved_reference_rate": (
            result.benchmark.unresolved_reference_rate
        ),
        "dangling_reference_rate": (
            result.benchmark.dangling_reference_rate
        ),
        "duplicate_rate": result.benchmark.duplicate_rate,
        "conflict_rate": result.benchmark.conflict_rate,
        "validation_score": result.benchmark.validation_score,
        "status": result.readiness.status.value,
        "reasons": result.benchmark.reasons,
    }
    app = create_app(runtime=runtime, bus=bus, knowledge_quality=payload)
    with TestClient(app) as client:
        resp = client.get("/api/knowledge-quality/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["map_count"] == 3
    assert data["status"] == "FOUNDATION_ONLY"


def test_webui_knowledge_quality_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/knowledge-quality/state")
    assert resp.json()["enabled"] is False


def test_cli(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_knowledge_quality.py",
            "--output",
            str(tmp_path / "sessions"),
            "--knowledge-root",
            str(tmp_path / "knowledge_versions"),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=90,
    )
    assert "KnowledgeReadiness = FOUNDATION_ONLY" in result.stdout
    assert result.returncode == 0
    version_dir = tmp_path / "knowledge_versions" / "demo-v1"
    assert (version_dir / "manifest.json").exists()
    assert (version_dir / "sources.json").exists()
    assert (version_dir / "canonical_map.json").exists()
    assert (version_dir / "validation_report.json").exists()
