"""Vision Evaluation 单测:OCR / entity / consistency / risk / benchmark / replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.observation.models import ObservationFrame, ObservationState
from maple_agent.providers import MockKnowledgeProvider
from maple_agent.runtime import RuntimeManager
from maple_agent.vision_eval import (
    RiskLevel,
    VisionBenchmark,
    VisionEvaluator,
    consistency_score,
    entity_quality_score,
    ocr_quality_score,
)
from maple_agent.webui.app import create_app


def _evaluator() -> VisionEvaluator:
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    knowledge.load_dataset()
    return VisionEvaluator(knowledge=knowledge)


def _frame(
    text: str = "射手村",
    confidence: float = 0.95,
    frame_id: str = "f1",
) -> ObservationFrame:
    return ObservationFrame(
        frame_id=frame_id,
        image_available=True,
        ocr_text=text,
        confidence=confidence,
    )


def _state(
    map_name: str = "射手村",
    entities: list[str] | None = None,
    confidence: float = 0.95,
) -> ObservationState:
    return ObservationState(
        map_name=map_name,
        visible_entities=entities or [],
        confidence=confidence,
    )


def test_ocr_quality_score():
    normal = ocr_quality_score("射手村", 0.95)
    assert normal.score > 0.9
    empty = ocr_quality_score("", 0.9)
    assert empty.score == 0.0
    assert "空" in empty.reason


def test_entity_quality_score():
    none = entity_quality_score([], 0.0)
    assert none.score == 0.0
    matched = entity_quality_score(["赫丽娜", "绿水灵"], 1.0)
    assert matched.score > 0.7


def test_consistency_score():
    consistent = consistency_score(
        "射手村",
        ["赫丽娜"],
        ["赫丽娜", "玛雅", "绿水灵"],
    )
    assert consistent.score == 1.0
    conflicting = consistency_score(
        "射手村",
        ["废弃都市NPC"],
        ["赫丽娜"],
    )
    assert conflicting.score < 0.5


def test_evaluator_normal_high_score():
    evaluator = _evaluator()
    result = evaluator.evaluate(
        frame=_frame(),
        state=_state(entities=["赫丽娜", "绿水灵"]),
    )
    assert result.overall_score > 0.8
    assert result.risk_level is RiskLevel.LOW
    assert result.ocr_score > 0.9


def test_evaluator_empty_high_risk():
    evaluator = _evaluator()
    result = evaluator.evaluate(
        frame=_frame(text="", confidence=0.0),
        state=_state(map_name="", entities=[]),
    )
    assert result.overall_score < 0.4
    assert result.risk_level is RiskLevel.HIGH
    assert any("OCR 文本为空" in issue for issue in result.issues)


def test_risk_judgment():
    assert VisionEvaluator._risk_level(0.9) is RiskLevel.LOW
    assert VisionEvaluator._risk_level(0.6) is RiskLevel.MEDIUM
    assert VisionEvaluator._risk_level(0.3) is RiskLevel.HIGH


def test_benchmark_runs_all_cases():
    benchmark = VisionBenchmark(_evaluator())
    cases = benchmark.load_cases()
    assert len(cases) >= 30
    sources = {case.source for case in cases}
    assert {
        "normal",
        "ocr_error",
        "empty",
        "low_confidence",
        "wrong_entity",
        "conflict",
    } <= sources
    result = benchmark.run()
    assert result.total_cases >= 30
    assert result.accuracy == 1.0
    assert result.failure_count == 0
    assert result.average_score > 0


def test_replay_generation(tmp_path):
    evaluator = _evaluator()
    evaluator.sessions_dir = tmp_path
    evaluator.evaluate(
        frame=_frame(),
        state=_state(entities=["赫丽娜", "绿水灵"]),
        trace_id="trace-vis",
    )
    replay = json.loads(
        (tmp_path / "trace-vis" / "vision_evaluation.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["frame_id"] == "f1"
    assert replay["overall_score"] > 0.8
    assert replay["risk_level"] == "LOW"
    assert "ocr_score" in replay
    assert "entity_score" in replay
    assert "consistency_score" in replay


def test_webui_vision_evaluation_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    evaluator = _evaluator()
    result = evaluator.evaluate(
        frame=_frame(),
        state=_state(entities=["赫丽娜", "绿水灵"]),
    )
    payload = {"result": result.model_dump(mode="json")}
    app = create_app(
        runtime=runtime,
        bus=bus,
        vision_evaluation=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/vision-evaluation/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["result"]["overall_score"] > 0.8
    assert data["result"]["risk_level"] == "LOW"


def test_webui_vision_evaluation_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/vision-evaluation/state")
    assert resp.json()["enabled"] is False
