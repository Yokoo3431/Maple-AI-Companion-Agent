"""Spatial World 单测:空间地图/传送门/位置解析/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.spatial_world import (
    LocationResolver,
    PortalReference,
    SpatialMapReference,
    SpatialMapStore,
    SpatialWorldBuilder,
    SpatialWorldReference,
    SpatialWorldValidator,
    SpatialWorldVerdict,
    load_demo_spatial_map,
    save_spatial_world_trace,
)
from maple_agent.webui.app import create_app
from maple_agent.world_knowledge.models import WorldKnowledgeReference


def _store() -> SpatialMapStore:
    return SpatialMapStore.from_data(load_demo_spatial_map())


def _resolve(store: SpatialMapStore, current_map: str = "射手村"):
    reference = SpatialWorldBuilder(store).resolve(
        world_knowledge_reference=WorldKnowledgeReference(
            current_map=current_map,
            known_maps=["射手村", "东部森林", "魔法密林"],
            reachable_maps=["东部森林"],
            confidence=0.95,
        )
    )
    validation = SpatialWorldValidator().validate(reference)
    return reference, validation


def test_spatial_map_creation():
    spatial_map = SpatialMapReference(
        map_id="map_100000000",
        map_name="射手村",
        width_reference=1024,
        height_reference=720,
        npc_locations=[{"name": "赫丽娜", "x": 120, "y": 80}],
        confidence=0.95,
    )
    assert spatial_map.map_name == "射手村"
    assert spatial_map.width_reference == 1024
    assert spatial_map.npc_locations[0]["name"] == "赫丽娜"


def test_portal_creation():
    portal = PortalReference(
        portal_id="east_forest",
        source_map="射手村",
        target_map="东部森林",
        position_reference={"x": 800, "y": 200},
        confidence=0.95,
    )
    assert portal.source_map == "射手村"
    assert portal.position_reference["x"] == 800
    assert portal.confidence == 0.95


def test_demo_data_import():
    store = _store()
    assert store.map_count() == 3
    spatial_map = store.find_map("射手村")
    assert spatial_map is not None
    assert len(spatial_map.portals) == 1
    assert len(spatial_map.npc_locations) == 1
    assert len(spatial_map.quest_zones) == 1


def test_find_npc_location():
    resolver = LocationResolver(_store())
    location = resolver.find_npc_location("射手村", "赫丽娜")
    assert location is not None
    assert location["x"] == 120
    assert location["y"] == 80
    assert resolver.find_npc_location("射手村", "不存在") is None


def test_find_portal_location():
    resolver = LocationResolver(_store())
    location = resolver.find_portal_location("射手村", "east_forest")
    assert location is not None
    assert location["target"] == "东部森林"
    assert location["x"] == 800
    assert resolver.find_portal_location("射手村", "missing") is None


def test_find_quest_area():
    resolver = LocationResolver(_store())
    area = resolver.find_quest_area("射手村", "新手任务")
    assert area is not None
    assert area["x"] == 120
    assert area["radius"] == 30


def test_resolver_full():
    store = _store()
    reference, validation = _resolve(store)
    assert reference.current_map == "射手村"
    assert len(reference.portals) == 1
    assert reference.portals[0].target_map == "东部森林"
    assert reference.npc_positions[0]["name"] == "赫丽娜"
    assert reference.quest_targets[0]["quest"] == "新手任务"
    assert len(reference.nearby_points) == 3
    assert reference.spatial_confidence == 0.95
    assert validation.verdict is SpatialWorldVerdict.VALID


def test_validator_warning_no_spatial_data():
    store = _store()
    _, validation = _resolve(store, current_map="魔法密林")
    assert validation.verdict is SpatialWorldVerdict.WARNING
    assert any("no portals" in issue for issue in validation.issues)
    assert any("no npc locations" in issue for issue in validation.issues)


def test_validator_blocked():
    reference = SpatialWorldReference.model_construct(
        current_map="射手村",
        spatial_confidence=1.5,
    )
    validation = SpatialWorldValidator().validate(reference)
    assert validation.verdict is SpatialWorldVerdict.BLOCKED
    assert "confidence out of range" in validation.issues


def test_replay_generation(tmp_path):
    store = _store()
    reference, validation = _resolve(store)
    save_spatial_world_trace(
        tmp_path,
        "trace-replay",
        current_map=reference.current_map,
        portals=reference.portals,
        locations=reference.nearby_points,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "spatial_world_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["map"] == "射手村"
    assert replay["portals"][0]["portal_id"] == "east_forest"
    assert replay["portals"][0]["x"] == 800
    assert len(replay["locations"]) == 3
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    store = _store()
    reference, _ = _resolve(store)
    context = AgentLoopContext(
        trace_id="trace-spatial",
        status=AgentLoopStatus.OBSERVING,
        spatial_world_reference=reference,
    )
    assert context.spatial_world_reference is not None
    assert context.spatial_world_reference.current_map == "射手村"
    assert context.spatial_world_reference.portals[0].portal_id == (
        "east_forest"
    )


def test_webui_spatial_world_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    store = _store()
    reference, validation = _resolve(store)
    payload = {
        "current_map": reference.current_map,
        "nearby_points": reference.nearby_points,
        "portals": [
            portal.model_dump(mode="json")
            for portal in reference.portals
        ],
        "npc_positions": reference.npc_positions,
        "quest_targets": reference.quest_targets,
        "spatial_confidence": reference.spatial_confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, spatial_world=payload)
    with TestClient(app) as client:
        resp = client.get("/api/spatial-world/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["current_map"] == "射手村"
    assert data["portals"][0]["portal_id"] == "east_forest"
    assert data["npc_positions"][0]["name"] == "赫丽娜"
    assert data["validation"] == "VALID"


def test_webui_spatial_world_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/spatial-world/state")
    assert resp.json()["enabled"] is False
