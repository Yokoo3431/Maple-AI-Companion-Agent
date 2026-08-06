"""WebUI 单测:Dashboard 渲染 / Runtime API / 状态快照 / WebSocket 推送。"""

import logging
import time

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.providers import (
    MockKnowledgeProvider,
    MockLLMProvider,
    MockOCRProvider,
    MockVisionProvider,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.vision import MockCaptureProvider, VisionWorker
from maple_agent.webui.app import create_app

# 保证 INFO 级日志可流入 WebSocket(避免依赖其他测试先设置级别)
logging.getLogger().setLevel(logging.INFO)


def _build_app():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    detector = MockGameWindowDetector(
        WindowInfo(
            handle=1,
            title="MapleStory",
            process_name="MapleStory.exe",
            rect=WindowRect(left=0, top=0, width=800, height=600),
        )
    )
    providers = {
        "llm": MockLLMProvider(),
        "vision": MockVisionProvider(),
    }
    app = create_app(runtime=runtime, bus=bus, providers=providers, detector=detector)
    return app, runtime, detector


def test_dashboard_page_renders():
    app, _, _ = _build_app()
    with TestClient(app) as client:
        resp = client.get("/")
    assert resp.status_code == 200
    assert "Maple AI Companion Agent" in resp.text
    assert "START" in resp.text
    assert "实时日志" in resp.text


def test_api_runtime_flow_and_illegal_transition():
    app, runtime, detector = _build_app()
    with TestClient(app) as client:
        resp = client.post("/api/runtime/start")
        assert resp.status_code == 200
        assert resp.json()["state"] == "READY"

        # READY -> PAUSED 非法,返回 409
        resp = client.post("/api/runtime/pause")
        assert resp.status_code == 409
        assert resp.json()["ok"] is False

        runtime.confirm()
        runtime.start_agent(detector=detector)
        resp = client.post("/api/runtime/pause")
        assert resp.status_code == 200
        assert resp.json()["state"] == "PAUSED"

        resp = client.post("/api/runtime/stop")
        assert resp.status_code == 200
        assert resp.json()["state"] == "OFFLINE"


def test_api_state_snapshot():
    app, _, _ = _build_app()
    with TestClient(app) as client:
        resp = client.get("/api/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["runtime"]["state"] == "OFFLINE"
    assert data["providers"] == {"llm": "CREATED", "vision": "CREATED"}
    assert data["window"]["detected"] is True
    assert data["window"]["info"]["title"] == "MapleStory"
    assert "events" in data
    assert "logs" in data


def test_health_endpoint():
    app, _, _ = _build_app()
    with TestClient(app) as client:
        resp = client.get("/api/health")
    data = resp.json()
    assert resp.status_code == 200
    assert data["runtime"]["state"] == "OFFLINE"
    assert data["providers"] == {"llm": "CREATED", "vision": "CREATED"}
    assert data["system"]["status"] == "ok"
    assert data["system"]["detector"] == "mock"
    assert data["system"]["version"]


def test_knowledge_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    app = create_app(runtime=runtime, bus=bus, knowledge=knowledge)
    with TestClient(app) as client:
        resp = client.get("/api/knowledge/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["game_profile"] == "maple-v113"
    assert data["version"] == "v113"
    assert data["counts"]["maps"] == 2


def test_vision_state_endpoint_disabled():
    app, _, _ = _build_app()
    with TestClient(app) as client:
        resp = client.get("/api/vision/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is False
    assert data["latest_frame"] is None


def test_vision_worker_publishes_frames_and_ocr_to_webui(tmp_path):
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    capture = MockCaptureProvider(
        width=800,
        height=600,
        sessions_dir=tmp_path / "sessions",
    )
    worker = VisionWorker(
        capture,
        bus,
        interval=0.02,
        ocr=MockOCRProvider(text="射手村"),
    )
    app = create_app(runtime=runtime, bus=bus, vision_worker=worker)
    with TestClient(app) as client:
        latest = None
        ocr_results = []
        for _ in range(150):
            resp = client.get("/api/vision/state")
            data = resp.json()
            if data["enabled"] and data["latest_frame"] is not None and data["latest_ocr"]:
                latest = data["latest_frame"]
                ocr_results = data["latest_ocr"]
                break
            time.sleep(0.02)
    assert latest is not None
    assert latest["width"] == 800
    assert latest["height"] == 600
    assert ocr_results and ocr_results[0]["text"] == "射手村"


def test_websocket_pushes_runtime_and_log_events():
    app, _, _ = _build_app()
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as ws:
            client.post("/api/runtime/start")
            messages = [ws.receive_json() for _ in range(6)]

    types = [m["type"] for m in messages]
    assert "event" in types
    assert "log" in types
    events = [m for m in messages if m["type"] == "event"]
    event_types = {e["event"]["event_type"] for e in events}
    assert "runtime.starting" in event_types
    assert "runtime.ready" in event_types
