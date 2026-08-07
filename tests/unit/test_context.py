"""Agent Context 单测:schema / build / trace / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient

from maple_agent.context import AgentContext, ContextBuilder
from maple_agent.events import EventBus
from maple_agent.fusion import FusionService
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import setup_logging
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.providers.ocr import MockOCRProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.vision import (
    MockCaptureProvider,
    ScreenshotPolicy,
    VisionState,
    VisionWorker,
)
from maple_agent.webui.app import create_app


def test_agent_context_schema():
    context = AgentContext(
        runtime_state="READY",
        vision_summary="OCR 射手村",
        knowledge_profile="maple-v113",
        trace_id="t-1",
    )
    assert context.runtime_state == "READY"
    assert context.world_state is None


def test_context_builder_build():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    builder = ContextBuilder(knowledge)
    vision = VisionState(frame_id="f-1", trace_id="t-c", summary="OCR 射手村")
    world = WorldState(
        current_map=knowledge.get_map(1),
        known_npcs=knowledge.get_npcs_by_map(1),
        known_monsters=knowledge.get_monsters_by_map(1),
        confidence=0.9,
        trace_id="t-c",
    )
    context = builder.build(
        vision_state=vision,
        world_state=world,
        runtime_state="RUNNING",
        trace_id="t-c",
    )
    assert context.runtime_state == "RUNNING"
    assert context.world_state.current_map.name == "射手村"
    assert context.knowledge_profile == "maple-v113"
    assert context.vision_summary == "OCR 射手村"
    assert context.trace_id == "t-c"


def test_context_builder_without_knowledge():
    builder = ContextBuilder()
    context = builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="READY",
        trace_id="t-2",
    )
    assert context.knowledge_profile == ""
    assert context.vision_summary == ""


def test_context_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    builder = ContextBuilder()
    builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="READY",
        trace_id="trace-ctx-log",
    )
    log = (tmp_path / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "context built: runtime=READY" in log
    assert "trace=trace-ctx-log" in log


@pytest.mark.asyncio
async def test_worker_context_replay(tmp_path):
    bus = EventBus()
    await bus.start()
    capture = MockCaptureProvider(
        policy=ScreenshotPolicy(save_enabled=True, max_images=5),
        sessions_dir=tmp_path / "sessions",
        width=160,
        height=90,
    )
    capture.initialize()
    ocr = MockOCRProvider(text="射手村")
    ocr.initialize()
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    fusion = FusionService(knowledge)
    worker = VisionWorker(
        capture,
        bus,
        interval=60,
        ocr=ocr,
        fusion=fusion,
        context_builder=ContextBuilder(knowledge),
        runtime_state_fn=lambda: "RUNNING",
    )
    worker.start()
    frame = await worker.tick()
    assert worker.latest_context is not None
    assert worker.latest_context.runtime_state == "RUNNING"
    assert worker.latest_context.world_state.current_map.name == "射手村"
    context_file = tmp_path / "sessions" / frame.trace_id / "context.json"
    assert context_file.exists()
    data = json.loads(context_file.read_text(encoding="utf-8"))
    assert data["runtime_state"] == "RUNNING"
    assert data["knowledge_profile"] == "maple-v113"
    await worker.stop()
    await bus.stop()


def test_webui_context_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    capture = MockCaptureProvider(width=160, height=90)
    builder = ContextBuilder(knowledge)
    worker = VisionWorker(
        capture,
        bus,
        interval=60,
        context_builder=builder,
        runtime_state_fn=lambda: runtime.state.value,
    )
    app = create_app(
        runtime=runtime,
        bus=bus,
        knowledge=knowledge,
        vision_worker=worker,
        context_builder=builder,
    )
    with TestClient(app) as client:
        resp = client.get("/api/context/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["runtime_state"] == "OFFLINE"
    assert data["knowledge_profile"] == "maple-v113"


def test_webui_context_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/context/state")
    assert resp.json()["enabled"] is False
