"""Knowledge Import 单测:导入 / 重复检测 / 归一化 / 非法关系 / Replay / 空源降级。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge.importer import (
    DatasetValidator,
    ImportSource,
    build_dataset,
    normalize_relation,
    run_import,
)
from maple_agent.knowledge_graph.models import MapNode, NPCNode, Relation, RelationType
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app

DEMO_SOURCE = {
    "maps": [
        {"map_id": 1, "name": "射手村", "aliases": ["Henesys"]},
        {"map_id": 2, "name": "魔法密林", "aliases": ["Ellinia"]},
    ],
    "npcs": [
        {"npc_id": 101, "name": "赫丽娜", "aliases": ["弓箭手教官"], "map_id": 1},
    ],
    "monsters": [
        {"monster_id": 100, "name": "绿水灵", "map_id": 1, "level": 4},
    ],
    "items": [
        {"item_id": 1, "name": "树液"},
    ],
    "relations": [
        {
            "source": "map",
            "source_id": 1,
            "target": "npc",
            "target_id": 101,
            "relation_type": "CONTAINS",
        },
        {
            "source": "map",
            "source_id": 1,
            "target": "monster",
            "target_id": 100,
            "relation_type": "SPAWNS",
        },
    ],
}


def test_valid_import_builds_dataset():
    dataset, result = build_dataset(DEMO_SOURCE, source="demo", version="v1")
    assert result.imported_maps == 2
    assert result.imported_npcs == 1
    assert result.imported_monsters == 1
    assert result.imported_items == 1
    assert result.imported_relations == 2
    assert result.warnings == []
    assert len(dataset.maps) == 2
    assert len(dataset.relations) == 2


def test_duplicate_id_skipped_with_warning():
    source = {
        "maps": [
            {"map_id": 1, "name": "射手村"},
            {"map_id": 1, "name": "射手村(重复)"},
        ]
    }
    dataset, result = build_dataset(source)
    assert result.imported_maps == 1
    assert any("重复 map id: 1" in warning for warning in result.warnings)
    assert len(dataset.maps) == 1


def test_builder_name_conflict_warning():
    source = {
        "maps": [
            {"map_id": 1, "name": "射手村"},
            {"map_id": 2, "name": "射手村"},
        ]
    }
    _, result = build_dataset(source)
    assert result.imported_maps == 1
    assert any("命名冲突" in warning for warning in result.warnings)


def test_normalization():
    source = {
        "maps": [
            {
                "map_id": 1,
                "name": "  射手村!!! ",
                "aliases": [" Henesys ", "Henesys", ""],
            }
        ],
        "npcs": [
            {
                "npc_id": 1,
                "name": " 赫丽娜 ",
                "aliases": ["弓箭手教官", "弓箭手教官"],
            }
        ],
    }
    dataset, _ = build_dataset(source)
    assert dataset.maps[0].name == "射手村"
    assert dataset.maps[0].aliases == ["Henesys"]
    assert dataset.npcs[0].name == "赫丽娜"
    assert dataset.npcs[0].aliases == ["弓箭手教官"]


def test_normalize_relation_variants():
    assert normalize_relation("located-at") == "LOCATED_AT"
    assert normalize_relation(" contains ") == "CONTAINS"
    assert normalize_relation("teleport") is None
    assert normalize_relation("") is None


def test_invalid_relation_skipped_with_warning():
    source = {
        **DEMO_SOURCE,
        "relations": [
            {
                "source": "map",
                "source_id": 1,
                "target": "npc",
                "target_id": 101,
                "relation_type": "TELEPORT",
            },
            {
                "source": "map",
                "source_id": 1,
                "target": "npc",
                "target_id": 999,
                "relation_type": "CONTAINS",
            },
        ],
    }
    dataset, result = build_dataset(source)
    assert result.imported_relations == 0
    assert any("非法关系类型" in warning for warning in result.warnings)
    assert any("关系引用缺失" in warning for warning in result.warnings)
    assert len(dataset.relations) == 0


def test_empty_source_fallback():
    dataset, result = build_dataset({})
    assert dataset.maps == []
    assert dataset.npcs == []
    assert dataset.monsters == []
    assert dataset.items == []
    assert result.imported_maps == 0
    assert result.warnings == []
    validation = DatasetValidator().validate(dataset)
    assert validation.valid is True
    assert validation.errors == []


def test_validator_detects_name_conflict_and_missing_ref():
    dataset = KnowledgeDataset(
        maps=[
            MapNode(map_id=1, name="射手村"),
            MapNode(map_id=2, name="射手村"),
        ],
        npcs=[NPCNode(npc_id=101, name="赫丽娜")],
        relations=[
            Relation(
                source="map",
                source_id=1,
                target="npc",
                target_id=999,
                relation_type=RelationType.CONTAINS,
            )
        ],
    )
    validation = DatasetValidator().validate(dataset)
    assert validation.valid is False
    assert any("命名冲突" in warning for warning in validation.warnings)
    assert any("关系引用缺失" in error for error in validation.errors)


def test_replay_generation(tmp_path):
    bundle = run_import(
        DEMO_SOURCE,
        source=ImportSource(source_id="demo", version="v1.0"),
        sessions_dir=tmp_path,
    )
    replay = json.loads((tmp_path / "knowledge_import.json").read_text(encoding="utf-8"))
    assert replay["source"] == "demo"
    assert replay["version"] == "v1.0"
    assert replay["imported_count"]["maps"] == 2
    assert replay["imported_count"]["relations"] == 2
    assert replay["warnings"] == []
    assert replay["validation_result"]["valid"] is True
    assert bundle.validation.valid is True
    assert bundle.result.source == "demo"


def test_webui_import_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    knowledge_import = {
        "source": "demo",
        "version": "v1.0",
        "maps": 2,
        "npcs": 1,
        "monsters": 1,
        "items": 1,
        "warnings": [],
        "valid": True,
    }
    app = create_app(runtime=runtime, bus=bus, knowledge_import=knowledge_import)
    with TestClient(app) as client:
        resp = client.get("/api/knowledge/import")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["source"] == "demo"
    assert data["maps"] == 2
    assert data["warnings"] == []


def test_webui_import_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/knowledge/import")
    assert resp.json()["enabled"] is False
