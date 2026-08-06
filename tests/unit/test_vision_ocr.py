"""OCR 感知层单测:模型 / Mock / Worker 集成 / Replay / 适配器守卫。"""

import json

import pytest
from pydantic import ValidationError

from maple_agent.events import Event, EventBus, EventType
from maple_agent.providers.base import ProviderError
from maple_agent.providers.ocr import (
    MockOCRProvider,
    OCRBBox,
    OCRRequest,
    OCRResult,
    TesseractOCRProvider,
    WindowsOCRProvider,
)
from maple_agent.vision import MockCaptureProvider, ScreenshotPolicy, VisionWorker


def test_ocr_result_model_fields():
    result = OCRResult(
        text="射手村",
        bbox=OCRBBox(left=10, top=20, width=100, height=30),
        confidence=0.9,
        source="windows.ocr",
        schema_version="1.0",
    )
    assert result.bbox.width == 100
    assert result.schema_version == "1.0"
    with pytest.raises(ValidationError):
        OCRResult(
            text="x",
            bbox=OCRBBox(left=0, top=0, width=1, height=1),
            confidence=1.5,
        )


def test_mock_ocr_lifecycle():
    provider = MockOCRProvider(text="勇士部落", confidence=0.88)
    provider.initialize()
    result = provider.recognize(OCRRequest(image_path=""), trace_id="t-ocr-1")
    assert result.text == "勇士部落"
    assert result.confidence == 0.88
    assert result.source == "mock"
    assert result.schema_version == "1.0"
    assert result.trace_id == "t-ocr-1"
    assert provider.call_count == 1


@pytest.mark.asyncio
async def test_mock_ocr_success_publishes_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockOCRProvider(bus=bus)
    provider.initialize()
    provider.recognize(OCRRequest(image_path=""), trace_id="t-ocr-2")
    await bus.wait_idle()
    assert events[0].event_type is EventType.OCR_COMPLETED
    assert isinstance(events[0].payload, OCRResult)
    assert events[0].trace_id == "t-ocr-2"
    await bus.stop()


@pytest.mark.asyncio
async def test_mock_ocr_failure_publishes_error():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockOCRProvider(bus=bus, raise_on_call=True)
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.recognize(OCRRequest(image_path=""), trace_id="t-ocr-3")
    await bus.wait_idle()
    assert events[0].event_type is EventType.ERROR_OCCURRED
    await bus.stop()


@pytest.mark.asyncio
async def test_worker_ocr_pipeline_and_replay(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    capture = MockCaptureProvider(
        bus=bus,
        policy=ScreenshotPolicy(save_enabled=True, max_images=10),
        sessions_dir=tmp_path / "sessions",
        width=320,
        height=180,
    )
    ocr = MockOCRProvider(bus=bus, text="射手村")
    capture.initialize()
    ocr.initialize()
    worker = VisionWorker(capture, bus, interval=60, ocr=ocr)
    worker.start()
    frame = await worker.tick()
    await bus.wait_idle()
    assert frame is not None
    assert worker.state.value == "IDLE"
    assert len(worker.latest_ocr) == 1
    assert worker.latest_ocr[0].text == "射手村"
    assert worker.latest_vision is not None
    assert len(worker.latest_vision.observation_refs) == 1
    event_types = {e.event_type for e in events}
    assert EventType.SCREEN_CAPTURED in event_types
    assert EventType.OCR_COMPLETED in event_types
    assert EventType.SCREEN_UPDATED in event_types
    traces = {e.trace_id for e in events}
    assert len(traces) == 1

    replay_dir = tmp_path / "sessions" / frame.trace_id
    assert (replay_dir / "frame.png").exists()
    assert (replay_dir / "vision.json").exists()
    replay = json.loads((replay_dir / "vision.json").read_text(encoding="utf-8"))
    assert replay["observations"][0]["element"] == "ocr_text"
    assert replay["vision_state"]["observation_refs"]
    await worker.stop()
    await bus.stop()


def test_windows_ocr_provider_guards():
    provider = WindowsOCRProvider()
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.recognize(OCRRequest(image_path="no-such-file.png"))


def test_tesseract_fallback_unavailable():
    provider = TesseractOCRProvider(tesseract_cmd="/nonexistent/tesseract")
    assert provider.is_available() is False
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.recognize(OCRRequest(image_path="no-such-file.png"))
