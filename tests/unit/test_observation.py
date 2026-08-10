"""Observation 沙箱单测:frame 生成 / OCR 解析 / validator / replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.observation import (
    ObservationAdapter,
    ObservationCollector,
    ObservationFrame,
    ObservationValidator,
    ObservationVerdict,
)
from maple_agent.providers import MockKnowledgeProvider, MockOCRProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _adapter(text: str = "射手村", confidence: float = 0.95) -> ObservationAdapter:
    ocr = MockOCRProvider(text=text, confidence=confidence)
    ocr.initialize()
    return ObservationAdapter(ocr=ocr)


def _knowledge() -> MockKnowledgeProvider:
    provider = MockKnowledgeProvider()
    provider.initialize()
    provider.load_dataset()
    return provider


def test_frame_generation():
    adapter = _adapter()
    frame = adapter.adapt(image_path="screenshot.png", source="test")
    assert frame.frame_id
    assert frame.image_available is True
    assert frame.source == "test"
    assert frame.ocr_text == "射手村"
    assert frame.confidence == 0.95
    assert frame.metadata["ocr_source"] == "mock"
    assert adapter.last_frame is frame


def test_ocr_parsing_from_bytes():
    adapter = _adapter()
    frame = adapter.adapt(image_bytes=b"mock-image-bytes", source="test")
    assert frame.image_available is True
    assert frame.ocr_text == "射手村"
    assert frame.confidence == 0.95
    assert frame.metadata.get("image_bytes_saved") is True


def test_validator_valid():
    adapter = _adapter()
    frame = adapter.adapt(image_path="x.png", source="test")
    result = ObservationValidator().validate(frame)
    assert result.verdict is ObservationVerdict.VALID
    assert result.issues == []


def test_validator_empty_frame_blocked():
    frame = ObservationFrame(frame_id="", image_available=False)
    result = ObservationValidator().validate(frame)
    assert result.verdict is ObservationVerdict.BLOCKED
    assert any("空 frame" in issue for issue in result.issues)


def test_validator_low_confidence_warning():
    adapter = _adapter(confidence=0.3)
    frame = adapter.adapt(image_path="x.png", source="test")
    result = ObservationValidator().validate(frame)
    assert result.verdict is ObservationVerdict.WARNING
    assert any("低置信" in issue for issue in result.issues)


def test_validator_conflict_blocked():
    frame = ObservationFrame(
        frame_id="f1",
        image_available=False,
        metadata={"conflict": True},
    )
    result = ObservationValidator().validate(frame)
    assert result.verdict is ObservationVerdict.BLOCKED
    assert any("信息冲突" in issue for issue in result.issues)


def test_collector_state_build():
    adapter = _adapter()
    collector = ObservationCollector(
        adapter,
        knowledge=_knowledge(),
        sessions_dir="sessions",
    )
    frame = collector.collect(image_path="x.png", source="test")
    state = collector.build_state(frame)
    assert state.map_name == "射手村"
    assert state.confidence == 0.95
    assert state.observations == ["射手村"]
    assert isinstance(state.visible_entities, list)


def test_replay_generation(tmp_path):
    adapter = _adapter()
    collector = ObservationCollector(adapter, sessions_dir=tmp_path)
    state = collector.collect_and_save(
        image_path="x.png",
        source="test",
        trace_id="trace-obs",
    )
    replay = json.loads(
        (tmp_path / "trace-obs" / "observation_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["frame_id"]
    assert replay["ocr"] == "射手村"
    assert replay["confidence"] == 0.95
    assert replay["state"] == "射手村"
    assert "observation_state" in replay
    assert state.map_name == "射手村"


def test_webui_observation_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    adapter = _adapter()
    collector = ObservationCollector(adapter, sessions_dir="sessions")
    state = collector.collect_and_save(
        image_path="x.png",
        source="test",
        trace_id="trace-webui",
    )
    validation = ObservationValidator().validate(collector.last_frame)
    payload = {
        "frame": collector.last_frame.model_dump(mode="json"),
        "state": state.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, observation=payload)
    with TestClient(app) as client:
        resp = client.get("/api/observation/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["frame"]["ocr_text"] == "射手村"
    assert data["state"]["map_name"] == "射手村"
    assert data["validation"]["verdict"] == "VALID"


def test_webui_observation_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/observation/state")
    assert resp.json()["enabled"] is False
