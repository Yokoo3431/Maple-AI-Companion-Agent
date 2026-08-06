"""Vision-Knowledge Fusion 单测:OCR 地图名 / alias / knowledge lookup / WorldState / trace。"""

import json

import pytest

from maple_agent.events import EventBus
from maple_agent.fusion import FusionService, WorldState
from maple_agent.logging_setup import setup_logging
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.providers.ocr import MockOCRProvider
from maple_agent.vision import (
    MockCaptureProvider,
    Observation,
    ScreenshotPolicy,
    VisionState,
    VisionWorker,
)


def test_vision_state_location_fields():
    state = VisionState(
        frame_id="f-1",
        trace_id="t-1",
        map_name="射手村",
        map_id=1,
        region="冒险岛世界",
        map_confidence=0.9,
    )
    assert state.map_id == 1
    assert state.region == "冒险岛世界"
    assert state.map_confidence == 0.9


def test_fusion_resolves_alias_to_map():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    service = FusionService(knowledge)
    observations = [
        Observation(
            element="ocr_text",
            type="text",
            raw_value="Henesys",
            normalized_value="Henesys",
            confidence=0.9,
            source="mock",
        )
    ]
    world = service.fuse(observations, trace_id="trace-fusion-1")
    assert isinstance(world, WorldState)
    assert world.current_map is not None
    assert world.current_map.name == "射手村"
    assert [npc.name for npc in world.known_npcs] == ["赫丽娜"]
    assert [monster.name for monster in world.known_monsters] == ["绿水灵"]
    assert world.confidence == 0.9
    assert world.trace_id == "trace-fusion-1"


def test_fusion_map_name_observation_direct():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    service = FusionService(knowledge)
    observations = [
        Observation(
            element="map_name",
            type="text",
            raw_value="勇士部落",
            normalized_value="勇士部落",
            confidence=0.8,
            source="mock",
        )
    ]
    world = service.fuse(observations)
    assert world.current_map.map_id == 2
    assert world.confidence == 0.8


def test_fusion_unknown_text():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    service = FusionService(knowledge)
    observations = [
        Observation(
            element="ocr_text",
            type="text",
            raw_value="某某杂讯",
            normalized_value="某某杂讯",
            confidence=0.7,
            source="mock",
        )
    ]
    world = service.fuse(observations)
    assert world.current_map is None
    assert world.known_npcs == []
    assert world.known_monsters == []
    assert world.confidence == 0.0


def test_knowledge_queries_by_map():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    assert [npc.name for npc in knowledge.get_npcs_by_map(1)] == ["赫丽娜"]
    assert [monster.name for monster in knowledge.get_monsters_by_map(1)] == ["绿水灵"]
    assert knowledge.get_npcs_by_map(999) == []


def test_fusion_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    service = FusionService(knowledge)
    observations = [
        Observation(
            element="ocr_text",
            type="text",
            raw_value="射手村",
            normalized_value="射手村",
            confidence=0.9,
            source="mock",
        )
    ]
    service.fuse(observations, trace_id="trace-fusion-log")
    log = (tmp_path / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "fusion complete: map=射手村" in log
    assert "trace=trace-fusion-log" in log


@pytest.mark.asyncio
async def test_worker_fusion_pipeline_and_replay(tmp_path):
    bus = EventBus()
    await bus.start()
    capture = MockCaptureProvider(
        policy=ScreenshotPolicy(save_enabled=True, max_images=5),
        sessions_dir=tmp_path / "sessions",
        width=320,
        height=180,
    )
    capture.initialize()
    ocr = MockOCRProvider(text="Henesys", confidence=0.9)
    ocr.initialize()
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    fusion = FusionService(knowledge)
    worker = VisionWorker(capture, bus, interval=60, ocr=ocr, fusion=fusion)
    worker.start()
    frame = await worker.tick()
    await bus.wait_idle()
    assert worker.latest_world is not None
    assert worker.latest_world.current_map.name == "射手村"
    assert worker.latest_vision.map_name == "射手村"
    assert worker.latest_vision.map_confidence == 0.9
    replay = json.loads(
        (tmp_path / "sessions" / frame.trace_id / "vision.json").read_text(encoding="utf-8")
    )
    assert replay["world_state"]["current_map"]["name"] == "射手村"
    await worker.stop()
    await bus.stop()
