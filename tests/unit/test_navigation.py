"""Navigation 单测:路由/BFS/Portal/NPC 目标/成本/校验/replay/context/WebUI。"""

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
from maple_agent.navigation import (
    CostCalculator,
    NavigationPlanner,
    NavigationReference,
    NavigationValidator,
    NavigationVerdict,
    RouteGraph,
    RouteStep,
    RouteStepType,
    save_navigation_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.spatial_world import (
    SpatialMapStore,
    SpatialWorldBuilder,
    load_demo_spatial_map,
)
from maple_agent.webui.app import create_app
from maple_agent.world_knowledge import (
    WorldKnowledgeImporter,
    WorldKnowledgeResolver,
    load_demo_world_map,
)


def _game_state(current_map: str = "射手村") -> GameStateReference:
    return GameStateReference(
        state_id="state-nav",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name=current_map,
            known_map=True,
        ),
        confidence=0.9,
    )


def _inputs(current_map: str = "射手村"):
    game_state = _game_state(current_map)
    world_graph = WorldKnowledgeImporter().import_data(
        load_demo_world_map()
    )
    world_knowledge = WorldKnowledgeResolver(world_graph).resolve(
        game_state_reference=game_state,
    )
    spatial = SpatialWorldBuilder(
        SpatialMapStore.from_data(load_demo_spatial_map())
    ).resolve(
        world_knowledge_reference=world_knowledge,
        game_state_reference=game_state,
    )
    return game_state, spatial, world_knowledge


def _plan(target: str, current_map: str = "射手村"):
    game_state, spatial, world_knowledge = _inputs(current_map)
    reference = NavigationPlanner().plan(
        target=target,
        game_state_reference=game_state,
        spatial_world_reference=spatial,
        world_knowledge_reference=world_knowledge,
    )
    validation = NavigationValidator().validate(reference)
    return reference, validation


def test_route_step_creation():
    step = RouteStep(
        step_type=RouteStepType.LOCAL_MOVE_REFERENCE,
        source="射手村",
        target="赫丽娜",
        metadata={"x": 120, "y": 80},
    )
    assert step.step_type is RouteStepType.LOCAL_MOVE_REFERENCE
    assert step.metadata["x"] == 120


def test_navigation_reference_creation():
    reference = NavigationReference(
        navigation_id="nav-1",
        start_location="射手村",
        target_location="赫丽娜",
        confidence=0.9,
    )
    assert reference.start_location == "射手村"
    assert reference.route_steps == []
    assert reference.confidence == 0.9


def test_route_graph_bfs():
    _, _, world_knowledge = _inputs()
    graph = RouteGraph.build_from_connections(
        world_knowledge.map_connections
    )
    assert graph.node_count() == 3
    assert graph.find_path("射手村", "魔法密林") == [
        "射手村",
        "东部森林",
        "魔法密林",
    ]
    assert graph.find_path("射手村", "不存在") == []


def test_cost_calculation():
    steps = [
        RouteStep(
            step_type=RouteStepType.PORTAL_REFERENCE,
            source="射手村",
            target="东部森林",
        ),
        RouteStep(
            step_type=RouteStepType.PORTAL_REFERENCE,
            source="东部森林",
            target="魔法密林",
        ),
    ]
    assert CostCalculator().calculate(steps) == 2.0


def test_planner_npc_target():
    reference, validation = _plan("赫丽娜")
    assert reference.start_location == "射手村"
    assert reference.target_location == "赫丽娜"
    assert len(reference.route_steps) == 1
    step = reference.route_steps[0]
    assert step.step_type is RouteStepType.LOCAL_MOVE_REFERENCE
    assert step.metadata["x"] == 120
    assert reference.confidence == 0.9
    assert validation.verdict is NavigationVerdict.VALID


def test_planner_map_target_portal_route():
    reference, validation = _plan("魔法密林")
    assert [step.step_type for step in reference.route_steps] == [
        RouteStepType.PORTAL_REFERENCE,
        RouteStepType.PORTAL_REFERENCE,
    ]
    assert reference.route_steps[0].target == "东部森林"
    assert reference.route_steps[1].target == "魔法密林"
    assert reference.estimated_cost == 2.0
    assert reference.confidence == 0.85
    assert validation.verdict is NavigationVerdict.VALID


def test_planner_unknown_target():
    reference, validation = _plan("未知目标")
    assert reference.route_steps == []
    assert validation.verdict is NavigationVerdict.WARNING
    assert any("empty route" in issue for issue in validation.issues)


def test_validator_blocked():
    reference = NavigationReference(
        navigation_id="",
        start_location="射手村",
        target_location="赫丽娜",
        confidence=0.9,
    )
    validation = NavigationValidator().validate(reference)
    assert validation.verdict is NavigationVerdict.BLOCKED
    assert "missing navigation id" in validation.issues


def test_replay_generation(tmp_path):
    reference, validation = _plan("赫丽娜")
    save_navigation_trace(
        tmp_path,
        "trace-replay",
        start=reference.start_location,
        target=reference.target_location,
        route=reference.route_steps,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "navigation_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["start"] == "射手村"
    assert replay["target"] == "赫丽娜"
    assert replay["route"][0]["type"] == "LOCAL_MOVE_REFERENCE"
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    reference, _ = _plan("赫丽娜")
    context = AgentLoopContext(
        trace_id="trace-nav",
        status=AgentLoopStatus.OBSERVING,
        navigation_reference=reference,
    )
    assert context.navigation_reference is not None
    assert context.navigation_reference.target_location == "赫丽娜"


def test_webui_navigation_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    reference, validation = _plan("赫丽娜")
    payload = {
        "navigation_id": reference.navigation_id,
        "start_location": reference.start_location,
        "target_location": reference.target_location,
        "route_steps": [
            step.model_dump(mode="json")
            for step in reference.route_steps
        ],
        "estimated_cost": reference.estimated_cost,
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, navigation=payload)
    with TestClient(app) as client:
        resp = client.get("/api/navigation/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["start_location"] == "射手村"
    assert data["target_location"] == "赫丽娜"
    assert data["route_steps"][0]["step_type"] == "LOCAL_MOVE_REFERENCE"
    assert data["confidence"] == 0.9
    assert data["validation"] == "VALID"


def test_webui_navigation_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/navigation/state")
    assert resp.json()["enabled"] is False
