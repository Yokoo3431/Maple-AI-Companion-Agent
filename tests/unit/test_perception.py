"""Perception Binding 单测:模型/Mock/实体检测/知识绑定/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.perception import (
    MaplePerceptionBinder,
    MockVisionProvider,
    ObservationAnalyzer,
    ObservationBuilder,
    ObservationSource,
    PerceivedEntityType,
    PerceptionValidator,
    PerceptionVerdict,
    VisualObservation,
    save_perception_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_demo_knowledge()
    graph = MapleKnowledgeGraph()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph


def _bind(
    graph: MapleKnowledgeGraph,
    *,
    location: str = "射手村",
    visible: list[str] | None = None,
    ui_state: str = "quest_available",
    confidence: float = 0.9,
):
    observation = MockVisionProvider(
        location=location,
        visible_entities=visible or ["赫丽娜"],
        ui_state=ui_state,
        confidence=confidence,
    ).capture()
    binder = MaplePerceptionBinder(knowledge=graph)
    reference = binder.bind(observation)
    return observation, reference


def test_visual_observation_creation():
    observation = ObservationBuilder.build(
        source=ObservationSource.IMAGE_REFERENCE,
        location="射手村",
        visible_entities=["赫丽娜"],
        ui_state="quest_available",
        confidence=0.85,
    )
    assert observation.observation_id
    assert observation.source is ObservationSource.IMAGE_REFERENCE
    assert "射手村" in observation.detected_elements
    assert observation.context["location"] == "射手村"
    assert observation.confidence == 0.85


def test_mock_vision_provider_output():
    provider = MockVisionProvider(
        location="射手村",
        visible_entities=["赫丽娜"],
        ui_state="quest_available",
        confidence=0.9,
    )
    observation = provider.capture()
    assert observation.source is ObservationSource.MOCK_SCREENSHOT
    assert observation.image_reference == "mock://screenshot"
    assert "赫丽娜" in observation.detected_elements
    assert provider.call_count == 1


def test_entity_detection():
    graph = _graph()
    observation = MockVisionProvider(
        location="射手村",
        visible_entities=["赫丽娜", "绿水灵"],
        ui_state="quest_available",
        confidence=0.9,
    ).capture()
    entities = ObservationAnalyzer().analyze(observation, graph)
    types = {entity.entity_type for entity in entities}
    assert PerceivedEntityType.MAP_LABEL in types
    assert PerceivedEntityType.NPC in types
    assert PerceivedEntityType.MONSTER in types
    assert PerceivedEntityType.UI_ELEMENT in types
    npc = next(
        entity
        for entity in entities
        if entity.entity_type is PerceivedEntityType.NPC
    )
    assert npc.name == "赫丽娜"


def test_knowledge_binding():
    graph = _graph()
    observation, reference = _bind(graph)
    assert reference.visible_map == "射手村"
    assert reference.visible_entities
    assert "赫丽娜" in reference.related_knowledge["npc"]
    assert "射手村" in reference.related_knowledge["map"]
    assert "新手任务" in reference.related_knowledge["quest"]
    assert reference.confidence >= 0.8
    assert reference.reasoning


def test_binding_unknown_entity():
    graph = _graph()
    observation, reference = _bind(
        graph,
        location="未知地图",
        visible=["不存在的NPC"],
        ui_state="",
    )
    assert reference.visible_map == "未知地图"
    assert reference.related_knowledge["npc"] == []
    assert reference.confidence == observation.confidence


def test_agent_loop_integration():
    graph = _graph()
    _, reference = _bind(graph)
    context = AgentLoopContext(
        trace_id="trace-perception",
        status=AgentLoopStatus.OBSERVING,
        perception_reference=reference,
    )
    assert context.perception_reference is not None
    assert context.perception_reference.visible_map == "射手村"
    assert context.perception_reference.observation_id


def test_validator_valid():
    graph = _graph()
    observation, reference = _bind(graph)
    result = PerceptionValidator().validate(observation, reference)
    assert result.verdict is PerceptionVerdict.VALID
    assert result.issues == []


def test_validator_warning_missing_knowledge():
    graph = _graph()
    observation, reference = _bind(
        graph,
        location="未知地图",
        visible=["不存在的NPC"],
        ui_state="",
    )
    result = PerceptionValidator().validate(observation, reference)
    assert result.verdict is PerceptionVerdict.WARNING
    assert "missing knowledge match" in result.issues


def test_validator_blocked():
    graph = _graph()
    observation, reference = _bind(graph)
    malformed = observation.model_copy(update={"observation_id": ""})
    result = PerceptionValidator().validate(malformed, reference)
    assert result.verdict is PerceptionVerdict.BLOCKED
    assert "malformed observation" in result.issues


def test_replay_generation(tmp_path):
    graph = _graph()
    observation, reference = _bind(graph)
    save_perception_trace(
        tmp_path,
        "trace-replay",
        observation=observation,
        entities=reference.visible_entities,
        knowledge_binding=reference,
        validation="VALID",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "perception_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["observation"]["observation_id"] == observation.observation_id
    assert replay["entities"]
    assert replay["knowledge_binding"]["visible_map"] == "射手村"
    assert replay["validation"] == "VALID"


def test_webui_perception_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph = _graph()
    _, reference = _bind(graph)
    payload = {
        "observation_id": reference.observation_id,
        "visible_entities": [
            entity.model_dump(mode="json")
            for entity in reference.visible_entities
        ],
        "visible_map": reference.visible_map,
        "ui_state_reference": reference.ui_state_reference,
        "related_knowledge": reference.related_knowledge,
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, perception=payload)
    with TestClient(app) as client:
        resp = client.get("/api/perception/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["visible_map"] == "射手村"
    assert "赫丽娜" in data["related_knowledge"]["npc"]
    assert data["validation"] == "VALID"


def test_webui_perception_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/perception/state")
    assert resp.json()["enabled"] is False


def test_visual_observation_serializable():
    observation = VisualObservation(
        observation_id="obs-serial",
        source=ObservationSource.MOCK_SCREENSHOT,
        confidence=0.7,
        detected_elements=["赫丽娜"],
        context={"location": "射手村"},
    )
    dumped = observation.model_dump(mode="json")
    assert dumped["source"] == "MOCK_SCREENSHOT"
    assert dumped["detected_elements"] == ["赫丽娜"]
