"""WebUI 单测:Dashboard 渲染 / Runtime API / 状态快照 / WebSocket 推送。"""

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.providers import MockLLMProvider, MockVisionProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


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
