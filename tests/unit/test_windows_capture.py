"""Windows Capture 单测:模型 / mock 兼容 / dpi / size / error / replay / WebUI。"""

import json
import time

import pytest
from fastapi.testclient import TestClient

from maple_agent.events import Event, EventBus, EventType
from maple_agent.providers import CaptureError, WindowsCaptureProvider
from maple_agent.providers.base import ErrorPayload
from maple_agent.runtime import RuntimeManager
from maple_agent.vision import MockCaptureProvider, ScreenshotPolicy, VisionWorker
from maple_agent.webui.app import create_app
from maple_agent.window import (
    WindowBindingService,
    WindowInfo,
    WindowRect,
)


def test_screen_frame_capture_fields():
    # 直接构造验证默认值(向后兼容)
    from maple_agent.vision.models import ScreenFrame

    minimal = ScreenFrame(
        frame_id="f-1",
        captured_at="2026-08-07T00:00:00Z",
        width=800,
        height=600,
    )
    assert minimal.window_hwnd is None
    assert minimal.capture_space == ""
    assert minimal.capture_width is None


def test_mock_capture_sets_capture_size():
    capture = MockCaptureProvider(width=800, height=600)
    capture.initialize()
    frame = capture.capture_frame(trace_id="t-mock")
    assert frame.capture_width == 800
    assert frame.capture_height == 600
    assert frame.width == 800


def test_mock_capture_dpi():
    capture = MockCaptureProvider(width=800, height=600, dpi_scale=1.25)
    capture.initialize()
    frame = capture.capture_frame(trace_id="t-dpi")
    assert frame.dpi_scale == 1.25


def test_windows_capture_requires_bound():
    provider = WindowsCaptureProvider()
    provider.initialize()
    with pytest.raises(CaptureError):
        provider.capture_frame()


def test_windows_capture_invalid_hwnd():
    bound = WindowBindingService().bind(
        WindowInfo(
            title="MapleStory",
            process_name="MapleStory.exe",
            hwnd=0,
            screen_rect=WindowRect(left=0, top=0, width=800, height=600),
            client_rect=WindowRect(left=0, top=0, width=800, height=600),
        )
    )
    provider = WindowsCaptureProvider(bound=bound)
    provider.initialize()
    with pytest.raises(CaptureError):
        provider.capture_frame()


@pytest.mark.asyncio
async def test_capture_error_publishes_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = WindowsCaptureProvider(bus=bus)
    provider.initialize()
    with pytest.raises(CaptureError):
        provider.capture_frame(trace_id="trace-cap-fail")
    await bus.wait_idle()
    assert events[0].event_type is EventType.ERROR_OCCURRED
    assert isinstance(events[0].payload, ErrorPayload)
    assert events[0].trace_id == "trace-cap-fail"
    await bus.stop()


class FakeWindowsProvider(MockCaptureProvider):
    """模拟真实捕获 Provider:带 bound 与 last_capture_method。"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.last_capture_method = "BITBLT"
        info = WindowInfo(
            title="MapleStory",
            process_name="MapleStory.exe",
            hwnd=12345,
            screen_rect=WindowRect(left=100, top=100, width=1024, height=768),
            client_rect=WindowRect(left=105, top=135, width=1016, height=735),
            dpi_scale=1.25,
        )
        self.bound = WindowBindingService().bind(info)

    def _capture_image(self, tid: str):
        image, meta = super()._capture_image(tid)
        meta["window_hwnd"] = 12345
        meta["capture_space"] = "CLIENT_SPACE"
        meta["dpi_scale"] = 1.25
        return image, meta


@pytest.mark.asyncio
async def test_worker_real_mode_capture_replay(tmp_path):
    bus = EventBus()
    await bus.start()
    capture = FakeWindowsProvider(
        policy=ScreenshotPolicy(save_enabled=True, max_images=5),
        sessions_dir=tmp_path / "sessions",
        width=1280,
        height=720,
    )
    capture.initialize()
    worker = VisionWorker(
        capture,
        bus,
        interval=60,
        capture_mode="WINDOW_REAL",
    )
    worker.start()
    frame = await worker.tick()
    await bus.wait_idle()
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / frame.trace_id
            / "capture_context.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["capture_method"] == "BITBLT"
    assert replay["hwnd"] == 12345
    assert replay["frame_size"] == {"width": 1280, "height": 720}
    assert replay["dpi"] == 1.25
    await worker.stop()
    await bus.stop()


def test_webui_capture_state_endpoint(tmp_path):
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    capture = MockCaptureProvider(
        sessions_dir=tmp_path / "sessions",
        width=800,
        height=600,
    )
    worker = VisionWorker(capture, bus, interval=0.02, capture_mode="MOCK")
    app = create_app(runtime=runtime, bus=bus, vision_worker=worker)
    with TestClient(app) as client:
        data = None
        for _ in range(150):
            resp = client.get("/api/capture/state")
            data = resp.json()
            if data["enabled"] and data["size"] != "-":
                break
            time.sleep(0.02)
    assert data["mode"] == "MOCK"
    assert data["size"] == "800x600"
    assert data["dpi"] == 1.0


def test_webui_capture_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/capture/state")
    assert resp.json()["enabled"] is False
