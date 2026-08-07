"""Vision Coordinate 单测:schema / 转换 / bbox / invalid / replay / WebUI。"""

import json
import time

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.events import EventBus
from maple_agent.providers.ocr import MockOCRProvider, OCRBBox
from maple_agent.runtime import RuntimeManager
from maple_agent.vision import MockCaptureProvider, ScreenshotPolicy, VisionWorker
from maple_agent.vision.coordinate import (
    CoordinateSpace,
    VisionAlignmentService,
    VisionCoordinateError,
    VisionCoordinateMapper,
    VisionFrameCoordinate,
)
from maple_agent.vision.models import MappedBBox
from maple_agent.webui.app import create_app
from maple_agent.window import (
    WindowBindingService,
    WindowInfo,
    WindowRect,
)


def _bound(dpi_scale: float = 1.25):
    info = WindowInfo(
        title="MapleStory",
        process_name="MapleStory.exe",
        hwnd=12345,
        screen_rect=WindowRect(left=100, top=100, width=1024, height=768),
        client_rect=WindowRect(left=105, top=135, width=1016, height=735),
        dpi_scale=dpi_scale,
    )
    return WindowBindingService().bind(info)


def _mapper(dpi_scale: float = 1.25, source_space=CoordinateSpace.CLIENT_SPACE):
    bound = _bound(dpi_scale)
    coordinate = VisionAlignmentService().align(
        frame_width=1280,
        frame_height=720,
        bound=bound,
        source_space=source_space,
    )
    return VisionCoordinateMapper(coordinate, bound)


def test_vision_frame_coordinate_schema():
    coordinate = VisionFrameCoordinate(frame_width=1280, frame_height=720)
    assert coordinate.source_space is CoordinateSpace.CLIENT_SPACE
    assert coordinate.target_space is CoordinateSpace.CLIENT_LOGICAL_SPACE
    with pytest.raises(ValidationError):
        VisionFrameCoordinate(frame_width=0, frame_height=720)
    with pytest.raises(ValidationError):
        VisionFrameCoordinate(frame_width=1280, frame_height=720, dpi_scale=0)


def test_frame_to_client_logical_dpi():
    mapper = _mapper(dpi_scale=1.25)
    assert mapper.frame_to_client_logical(100, 200) == (80.0, 160.0)
    assert mapper.frame_to_screen(100, 200) == (205.0, 335.0)


@pytest.mark.parametrize("dpi_scale", [1.0, 1.25, 1.5, 2.0])
def test_dpi_conversion(dpi_scale):
    mapper = _mapper(dpi_scale=dpi_scale)
    client = mapper.frame_to_client_logical(100.0, 200.0)
    assert client[0] == pytest.approx(100.0 / dpi_scale)
    assert client[1] == pytest.approx(200.0 / dpi_scale)


def test_screen_space_source_uses_client_offset():
    mapper = _mapper(source_space=CoordinateSpace.SCREEN_SPACE)
    # 帧像素 (0,0) = 屏幕 (offset_x, offset_y) = 客户区原点 → 客户逻辑 (0,0)
    assert mapper.frame_to_client_logical(0, 0) == (0.0, 0.0)
    assert mapper.frame_to_screen(0, 0) == (105.0, 135.0)


def test_bbox_mapping():
    mapper = _mapper(dpi_scale=1.25)
    mapped = mapper.map_bbox(OCRBBox(left=10, top=20, width=100, height=50))
    assert isinstance(mapped, MappedBBox)
    assert mapped.left == pytest.approx(8.0)
    assert mapped.top == pytest.approx(16.0)
    assert mapped.width == pytest.approx(80.0)
    assert mapped.height == pytest.approx(40.0)


def test_invalid_transform_target():
    bound = _bound()
    coordinate = VisionFrameCoordinate(
        frame_width=1280,
        frame_height=720,
        target_space=CoordinateSpace.CLIENT_SPACE,
    )
    mapper = VisionCoordinateMapper(coordinate, bound)
    with pytest.raises(VisionCoordinateError):
        mapper.frame_to_client_logical(10, 10)


@pytest.mark.asyncio
async def test_worker_coordinate_replay(tmp_path):
    bus = EventBus()
    await bus.start()
    capture = MockCaptureProvider(
        policy=ScreenshotPolicy(save_enabled=True, max_images=5),
        sessions_dir=tmp_path / "sessions",
        width=1280,
        height=720,
    )
    capture.initialize()
    ocr = MockOCRProvider(text="射手村", confidence=0.9)
    ocr.initialize()
    worker = VisionWorker(
        capture,
        bus,
        interval=60,
        ocr=ocr,
        coordinate_mapper=_mapper(dpi_scale=1.25),
    )
    worker.start()
    frame = await worker.tick()
    await bus.wait_idle()
    assert worker.latest_vision is not None
    assert worker.latest_vision.observation_refs
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / frame.trace_id
            / "vision_coordinate.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["frame_size"] == {"width": 1280, "height": 720}
    assert replay["dpi_scale"] == 1.25
    assert replay["bbox_mapping"]["mapped"]["left"] == 0.0
    await worker.stop()
    await bus.stop()


def test_webui_vision_coordinate_state(tmp_path):
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    capture = MockCaptureProvider(
        sessions_dir=tmp_path / "sessions",
        width=1280,
        height=720,
    )
    ocr = MockOCRProvider(text="射手村")
    worker = VisionWorker(
        capture,
        bus,
        interval=0.02,
        ocr=ocr,
        coordinate_mapper=_mapper(dpi_scale=1.25),
    )
    app = create_app(runtime=runtime, bus=bus, vision_worker=worker)
    with TestClient(app) as client:
        data = None
        for _ in range(150):
            resp = client.get("/api/vision-coordinate/state")
            data = resp.json()
            if data["enabled"] and "x" in str(data["frame"]):
                break
            time.sleep(0.02)
    assert data["enabled"] is True
    assert data["space"] == "CLIENT_LOGICAL_SPACE"
    assert data["dpi"] == 1.25
    assert data["offset"] == {"x": 0.0, "y": 0.0}


def test_webui_vision_coordinate_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/vision-coordinate/state")
    assert resp.json()["enabled"] is False
