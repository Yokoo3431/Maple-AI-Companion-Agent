"""World Knowledge 单测:模型/导入/图谱查询/可达/关联/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.game_state.models import (
    GameStateReference,
    MapStateReference,
    PlayerStateReference,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app
from maple_agent.world_knowledge import (
    MapConnectionReference,
    MapConnectionType,
    MapGraph,
    MapNodeReference,
    WorldKnowledgeImporter,
    WorldKnowledgeResolver,
    WorldKnowledgeValidator,
    WorldKnowledgeVerdict,
    load_demo_world_map,
    save_world_knowledge_trace,
)


def _graph() -> MapGraph:
    return WorldKnowledgeImporter().import_data(load_demo_world_map())


def _game_state(current_map: str = "射手村") -> GameStateReference:
    return GameStateReference(
        state_id="state-1",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name=current_map,
            known_map=True,
        ),
        confidence=0.9,
    )


def _resolve(graph: MapGraph, current_map: str = "射手村"):
    reference = WorldKnowledgeResolver(graph).resolve(
        game_state_reference=_game_state(current_map),
    )
    validation = WorldKnowledgeValidator().validate(reference)
    return reference, validation


def test_map_node_creation():
    node = MapNodeReference(
        map_id="map_100000000",
        map_name="射手村",
        aliases=["Henesys"],
        map_type="TOWN",
        npc_references=["赫丽娜"],
        confidence=0.95,
    )
    assert node.map_id == "map_100000000"
    assert node.map_name == "射手村"
    assert node.map_type == "TOWN"
    assert node.confidence == 0.95


def test_map_connection_creation():
    connection = MapConnectionReference(
        source_map="射手村",
        target_map="东部森林",
        connection_type=MapConnectionType.PORTAL,
        confidence=0.95,
    )
    assert connection.connection_type is MapConnectionType.PORTAL
    assert connection.source_map == "射手村"
    assert connection.direction_reference == {}


def test_json_import():
    graph = _graph()
    assert graph.node_count() == 3
    assert graph.connection_count() == 2
    assert set(graph.known_map_names()) == {
        "东部森林",
        "射手村",
        "魔法密林",
    }


def test_yaml_import():
    yaml_text = """
maps:
  - name: 测试村
    type: TOWN
connections:
  - from: 测试村
    to: 测试林
"""
    graph = WorldKnowledgeImporter().import_data(yaml_text)
    assert graph.node_count() == 1
    assert graph.find_map("测试村") is not None


def test_graph_find_map_by_alias():
    graph = _graph()
    assert graph.find_map("射手村").map_id == "map_100000000"
    assert graph.find_map("Henesys").map_name == "射手村"
    assert graph.find_map("不存在") is None


def test_graph_find_connections():
    graph = _graph()
    connections = graph.find_connections("射手村")
    assert len(connections) == 1
    assert connections[0].target_map == "东部森林"


def test_graph_reachable():
    graph = _graph()
    assert graph.find_reachable_maps("射手村") == ["东部森林"]
    assert set(graph.find_reachable_maps("东部森林")) == {
        "射手村",
        "魔法密林",
    }


def test_graph_related_entities():
    graph = _graph()
    assert graph.find_related_npcs("射手村") == ["赫丽娜"]
    assert graph.find_related_monsters("射手村") == ["绿水灵"]
    assert graph.find_related_quests("射手村") == ["新手任务"]


def test_resolver_full():
    graph = _graph()
    reference, validation = _resolve(graph)
    assert reference.current_map == "射手村"
    assert reference.reachable_maps == ["东部森林"]
    assert "赫丽娜" in reference.related_npcs
    assert "新手任务" in reference.related_quests
    assert reference.confidence == 0.95
    assert validation.verdict is WorldKnowledgeVerdict.VALID


def test_validator_warning_unknown_map():
    graph = _graph()
    _, validation = _resolve(graph, current_map="未知地图")
    assert validation.verdict is WorldKnowledgeVerdict.WARNING
    assert any("unknown current map" in issue for issue in validation.issues)


def test_validator_blocked_empty_graph():
    reference, validation = _resolve(MapGraph(), current_map="射手村")
    assert validation.verdict is WorldKnowledgeVerdict.BLOCKED
    assert "empty world graph" in validation.issues


def test_replay_generation(tmp_path):
    graph = _graph()
    reference, validation = _resolve(graph)
    save_world_knowledge_trace(
        tmp_path,
        "trace-replay",
        current_map=reference.current_map,
        known_maps=reference.known_maps,
        connections=reference.map_connections,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "world_knowledge_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["current_map"] == "射手村"
    assert replay["known_maps"] == ["东部森林", "射手村", "魔法密林"]
    assert replay["connections"][0] == {
        "from": "射手村",
        "to": "东部森林",
    }
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    graph = _graph()
    reference, _ = _resolve(graph)
    context = AgentLoopContext(
        trace_id="trace-world",
        status=AgentLoopStatus.OBSERVING,
        world_knowledge_reference=reference,
    )
    assert context.world_knowledge_reference is not None
    assert context.world_knowledge_reference.reachable_maps == [
        "东部森林"
    ]


def test_webui_world_knowledge_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph = _graph()
    reference, validation = _resolve(graph)
    payload = {
        "current_map": reference.current_map,
        "known_maps": reference.known_maps,
        "reachable_maps": reference.reachable_maps,
        "map_connections": [
            connection.model_dump(mode="json")
            for connection in reference.map_connections
        ],
        "related_npcs": reference.related_npcs,
        "related_monsters": reference.related_monsters,
        "related_quests": reference.related_quests,
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, world_knowledge=payload)
    with TestClient(app) as client:
        resp = client.get("/api/world-knowledge/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["current_map"] == "射手村"
    assert data["reachable_maps"] == ["东部森林"]
    assert "赫丽娜" in data["related_npcs"]
    assert data["validation"] == "VALID"


def test_webui_world_knowledge_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/world-knowledge/state")
    assert resp.json()["enabled"] is False
