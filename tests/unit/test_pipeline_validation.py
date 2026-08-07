"""Pipeline Validation 单测:window / size / coordinate / OCR / fusion / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.providers.ocr import MockOCRProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.validation import (
    PipelineValidationError,
    VisionPipelineValidator,
)
from maple_agent.vision import MockCaptureProvider
from maple_agent.vision.coordinate import VisionCoordinateError
from maple_agent.vision.coordinate.alignment import VisionAlignmentService
from maple_agent.webui.app import create_app
from maple_agent.window import MockWindowDetector, WindowInfo, WindowRect


def _window(client_w: int = 800, client_h: int = 600) -> WindowInfo:
    return WindowInfo(
        title="MapleStory",
        process_name="MapleStory.exe",
        hwnd=12345,
        screen_rect=WindowRect(left=100, top=100, width=client_w, height=client_h),
        client_rect=WindowRect(left=105, top=135, width=client_w, height=client_h),
        dpi_scale=1.0,
    )


def _validator(
    *,
    detector=None,
    capture=None,
    ocr=None,
    knowledge=None,
    sessions_dir=None,
):
    capture = capture or MockCaptureProvider(width=800, height=600)
    ocr = ocr or MockOCRProvider(text="射手村")
    knowledge = knowledge or MockKnowledgeProvider()
    capture.initialize()
    ocr.initialize()
    knowledge.initialize()
    return VisionPipelineValidator(
        detector=detector or MockWindowDetector(_window()),
        capture=capture,
        knowledge=knowledge,
        ocr=ocr,
        sessions_dir=sessions_dir or "sessions",
    )


def test_window_missing():
    validator = _validator(detector=MockWindowDetector())
    with pytest.raises(PipelineValidationError, match="窗口"):
        validator.validate_once()


def test_capture_size_mismatch():
    validator = _validator(
        capture=MockCaptureProvider(width=1280, height=720),
    )
    with pytest.raises(PipelineValidationError, match="尺寸不一致"):
        validator.validate_once()


def test_coordinate_mismatch(monkeypatch):
    validator = _validator()

    def bad_align(self, **kwargs):
        raise VisionCoordinateError("坐标不匹配")

    monkeypatch.setattr(VisionAlignmentService, "align", bad_align)
    with pytest.raises(PipelineValidationError, match="坐标不匹配"):
        validator.validate_once()


def test_ocr_failure():
    validator = _validator(ocr=MockOCRProvider(raise_on_call=True))
    with pytest.raises(PipelineValidationError, match="pipeline 校验失败"):
        validator.validate_once()


def test_fusion_failure():
    class FailingKnowledge(MockKnowledgeProvider):
        def get_map(self, ref, *, trace_id=None):
            raise RuntimeError("knowledge boom")

    validator = _validator(knowledge=FailingKnowledge())
    with pytest.raises(PipelineValidationError, match="pipeline 校验失败"):
        validator.validate_once()


def test_pipeline_success_and_replay(tmp_path):
    validator = _validator(
        sessions_dir=tmp_path / "sessions",
    )
    result = validator.validate_once(trace_id="trace-pipeline-ok")
    assert result.status.overall == "OK"
    assert result.status.window == "CONNECTED"
    assert result.status.ocr == "OK"
    assert result.status.world == "READY"
    assert result.ocr is not None
    assert result.world is not None
    assert result.world.current_map.name == "射手村"
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / "trace-pipeline-ok"
            / "pipeline_validation.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["window"]["hwnd"] == 12345
    assert replay["capture"]["method"] == "-"
    assert replay["ocr"]["text"] == "射手村"
    assert replay["fusion"]["map"] == "射手村"
    assert replay["fusion"]["npcs"] == ["赫丽娜"]
    assert replay["fusion"]["monsters"] == ["绿水灵"]


def test_webui_pipeline_state_endpoint(tmp_path):
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    validator = _validator(sessions_dir=tmp_path / "sessions")
    validator.validate_once(trace_id="trace-pipeline-web")
    app = create_app(runtime=runtime, bus=bus, pipeline_validator=validator)
    with TestClient(app) as client:
        resp = client.get("/api/pipeline/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["overall"] == "OK"
    assert data["window"] == "CONNECTED"
    assert data["ocr"] == "OK"
    assert data["world"] == "READY"


def test_webui_pipeline_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/pipeline/state")
    assert resp.json()["enabled"] is False
