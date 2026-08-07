"""Window Binding 单测:schema / detector / dpi / coordinate / lost / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.events import Event, EventBus, EventType
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app
from maple_agent.window import (
    BoundWindow,
    CoordinateTransformer,
    MockWindowDetector,
    WindowBindingService,
    WindowBindingStatus,
    WindowInfo,
    WindowRect,
)


def _window(dpi_scale: float = 1.0, trace_id: str = "") -> WindowInfo:
    return WindowInfo(
        title="MapleStory",
        process_name="MapleStory.exe",
        hwnd=12345,
        screen_rect=WindowRect(left=100, top=100, width=1024, height=768),
        client_rect=WindowRect(left=105, top=135, width=1016, height=735),
        dpi_scale=dpi_scale,
        trace_id=trace_id,
    )


def test_window_info_schema():
    info = _window()
    assert info.hwnd == 12345
    assert info.dpi_scale == 1.0
    with pytest.raises(ValidationError):
        _window(dpi_scale=0)  # dpi 必须 > 0


def test_mock_detector():
    detector = MockWindowDetector(_window())
    info = detector.find_window(trace_id="trace-win")
    assert info.title == "MapleStory"
    assert info.trace_id == "trace-win"
    assert MockWindowDetector().find_window() is None


def test_binding_service_bound_window():
    service = WindowBindingService()
    bound = service.bind(_window(dpi_scale=1.25))
    assert isinstance(bound, BoundWindow)
    assert bound.client_offset == (105, 135)
    assert bound.screen_offset == (100, 100)
    assert bound.dpi_scale == 1.25
    assert bound.coordinate_space == "client_logical"


@pytest.mark.parametrize("dpi_scale", [1.0, 1.25, 1.5, 2.0])
def test_dpi_conversion_roundtrip(dpi_scale):
    bound = WindowBindingService().bind(_window(dpi_scale=dpi_scale))
    transformer = CoordinateTransformer(bound)
    screen = transformer.client_to_screen(100.0, 200.0)
    back = transformer.screen_to_client(*screen)
    assert back[0] == pytest.approx(100.0)
    assert back[1] == pytest.approx(200.0)


def test_coordinate_transform_origin():
    bound = WindowBindingService().bind(_window(dpi_scale=1.5))
    transformer = CoordinateTransformer(bound)
    assert transformer.screen_to_client(105, 135) == (0.0, 0.0)
    assert transformer.client_to_screen(0, 0) == (105, 135)
    assert transformer.screen_to_client(105 + 150, 135 + 300) == (100.0, 200.0)


def test_binding_replay(tmp_path):
    service = WindowBindingService(sessions_dir=tmp_path / "sessions")
    service.bind(_window(dpi_scale=1.25, trace_id="trace-win-replay"))
    replay = json.loads(
        (tmp_path / "sessions" / "trace-win-replay" / "window_context.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["window"]["title"] == "MapleStory"
    assert replay["dpi_scale"] == 1.25
    assert replay["client_offset"] == [105, 135]


@pytest.mark.asyncio
async def test_runtime_window_lost_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    runtime = RuntimeManager(bus=bus)
    assert runtime.binding_status is WindowBindingStatus.UNBOUND
    runtime.bind_window(_window(), trace_id="trace-bind")
    assert runtime.binding_status is WindowBindingStatus.BOUND
    runtime.mark_window_lost(trace_id="trace-lost")
    await bus.wait_idle()
    assert runtime.binding_status is WindowBindingStatus.LOST
    lost = [event for event in events if event.event_type is EventType.WINDOW_BIND_LOST]
    assert lost and lost[0].trace_id == "trace-lost"
    await bus.stop()


def test_webui_window_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    runtime.bind_window(_window(dpi_scale=1.25))
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/window/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["status"] == "BOUND"
    assert data["window"]["title"] == "MapleStory"
    assert data["window"]["dpi_scale"] == 1.25
    assert data["mode"] == "READ ONLY"
