"""Vision Runtime 单测:捕获/OCR接口/检测/解析/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.vision_runtime import (
    GameStateParser,
    MockOCRProvider,
    MockScreenshotProvider,
    VisionDetector,
    VisionRuntimeValidator,
    VisionRuntimeVerdict,
    VisionSource,
    save_vision_runtime_trace,
)
from maple_agent.webui.app import create_app


def _provider(**overrides) -> MockScreenshotProvider:
    config = {
        "map_name": "射手村",
        "npcs": ["赫丽娜"],
        "monsters": ["绿水灵"],
        "items": ["红药水"],
        "ui_elements": ["任务提示"],
        "hp_ratio": 0.8,
        "mp_ratio": 0.6,
        "quests": ["新手任务"],
        "confidence": 0.9,
    }
    config.update(overrides)
    return MockScreenshotProvider(**config)


def _run(**overrides):
    provider = _provider(**overrides)
    frame = provider.capture(trace_id="trace-vision")
    ocr = MockOCRProvider(
        text=provider.mock_ocr_text(),
        confidence=0.9,
    ).recognize(frame)
    elements = VisionDetector().detect(frame, ocr)
    observation = GameStateParser().parse(frame, ocr, elements)
    validation = VisionRuntimeValidator().validate(frame, observation)
    return provider, frame, ocr, elements, observation, validation


def test_capture():
    provider = _provider()
    frame = provider.capture(trace_id="trace-capture")
    assert frame.frame_id
    assert frame.source is VisionSource.MOCK_SCREENSHOT
    assert frame.image_reference.startswith("mock://")
    assert frame.confidence == 0.9
    reference = provider.capture_reference()
    assert reference is not None
    assert reference.window_title == "MapleStory"
    assert reference.window_rect["width"] == 800
    assert provider.call_count == 1


def test_ocr_interface():
    provider = _provider()
    frame = provider.capture()
    ocr = MockOCRProvider(
        text=provider.mock_ocr_text(),
        confidence=0.85,
    ).recognize(frame)
    assert ocr.lines
    assert ocr.confidence == 0.85
    assert ocr.source == "mock"
    assert any("地图:射手村" in line for line in ocr.lines)


def test_detector_classification():
    _, frame, ocr, elements, _, _ = _run()
    types = {
        (element.element_type, element.name) for element in elements
    }
    assert ("MAP_LABEL", "射手村") in types
    assert ("NPC", "赫丽娜") in types
    assert ("MONSTER", "绿水灵") in types
    assert ("ITEM", "红药水") in types
    assert ("UI_ELEMENT", "任务提示") in types
    # 元信息行(HP/MP/任务)不应被当作画面元素
    assert not any(element.name.startswith("80") for element in elements)


def test_parser_full_observation():
    _, _, _, _, observation, _ = _run()
    assert observation.visible_map == "射手村"
    assert observation.visible_entities == ["赫丽娜", "绿水灵", "红药水"]
    assert observation.ui_elements == ["任务提示"]
    assert observation.hp_reference == 0.8
    assert observation.mp_reference == 0.6
    assert observation.quest_reference == ["新手任务"]
    assert observation.confidence == 0.9


def test_parser_ratio_variants():
    frame = _provider(hp_ratio=0.8, mp_ratio=0.6).capture()
    ocr = MockOCRProvider(
        text="HP 80%\nMP 60%",
        confidence=0.9,
    ).recognize(frame)
    observation = GameStateParser().parse(
        frame,
        ocr,
        VisionDetector().detect(frame, ocr),
    )
    assert observation.hp_reference == 0.8
    assert observation.mp_reference == 0.6


def test_validator_valid():
    _, frame, _, _, observation, validation = _run()
    assert validation.verdict is VisionRuntimeVerdict.VALID
    assert validation.issues == []
    assert observation.visible_map == "射手村"


def test_validator_warning_missing_hp_mp():
    _, frame, _, _, observation, validation = _run(
        hp_ratio=None,
        mp_ratio=None,
    )
    assert validation.verdict is VisionRuntimeVerdict.WARNING
    assert any("missing hp" in issue for issue in validation.issues)
    assert any("missing mp" in issue for issue in validation.issues)


def test_validator_blocked():
    provider = _provider()
    frame = provider.capture()
    ocr = MockOCRProvider(
        text=provider.mock_ocr_text(),
    ).recognize(frame)
    elements = VisionDetector().detect(frame, ocr)
    observation = GameStateParser().parse(frame, ocr, elements)
    malformed = frame.model_copy(update={"frame_id": ""})
    validation = VisionRuntimeValidator().validate(malformed, observation)
    assert validation.verdict is VisionRuntimeVerdict.BLOCKED
    assert "missing frame id" in validation.issues


def test_replay_generation(tmp_path):
    _, frame, _, _, observation, validation = _run()
    save_vision_runtime_trace(
        tmp_path,
        "trace-replay",
        frame=frame,
        observation=observation,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "vision_runtime_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["frame"]["frame_id"] == frame.frame_id
    assert replay["observation"]["visible_map"] == "射手村"
    assert replay["observation"]["hp_reference"] == 0.8
    assert replay["observation"]["quest_reference"] == ["新手任务"]
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    _, _, _, _, observation, _ = _run()
    context = AgentLoopContext(
        trace_id="trace-vision",
        status=AgentLoopStatus.OBSERVING,
        vision_reference=observation,
    )
    assert context.vision_reference is not None
    assert context.vision_reference.visible_map == "射手村"
    assert context.vision_reference.hp_reference == 0.8


def test_webui_vision_runtime_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    _, frame, _, _, observation, validation = _run()
    payload = {
        "frame_id": frame.frame_id,
        "source": frame.source.value,
        "image_reference": frame.image_reference,
        "visible_map": observation.visible_map,
        "visible_entities": observation.visible_entities,
        "ui_elements": observation.ui_elements,
        "hp_reference": observation.hp_reference,
        "mp_reference": observation.mp_reference,
        "quest_reference": observation.quest_reference,
        "confidence": observation.confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, vision_runtime=payload)
    with TestClient(app) as client:
        resp = client.get("/api/vision-runtime/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["visible_map"] == "射手村"
    assert "赫丽娜" in data["visible_entities"]
    assert data["hp_reference"] == 0.8
    assert data["mp_reference"] == 0.6
    assert data["validation"] == "VALID"


def test_webui_vision_runtime_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/vision-runtime/state")
    assert resp.json()["enabled"] is False
