"""Real Vision Validation 单测:Provider/OCR/ROI/Dataset/Benchmark/Readiness/集成(仅 fixtures)。"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from maple_agent.events import EventBus
from maple_agent.game_state import GameStateExtractor
from maple_agent.game_state.models import GameStateReference
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.real_vision import (
    CaptureStatus,
    RealOCRProvider,
    RealVisionBenchmark,
    RealVisionBenchmarkResult,
    TesseractOCRAdapter,
    VisionGroundTruth,
    VisionValidationDataset,
    VisionValidationSample,
    WindowsScreenshotProvider,
    build_real_vision_client_benchmark_report,
    build_real_vision_readiness,
    build_real_vision_webui_state,
    load_vision_profiles,
    save_real_vision_client_benchmark,
    save_real_vision_validation_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_vnext.models import ReadinessStatus
from maple_agent.vision_runtime.models import ScreenObservation
from maple_agent.webui.app import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = REPO_ROOT / "tests" / "fixtures" / "real_vision"


def _sample(
    sample_id: str,
    *,
    map_name: str = "射手村",
    aliases: tuple[str, ...] = ("Henesys",),
    hp: float = 0.8,
    mp: float = 0.6,
    npcs: tuple[str, ...] = ("赫丽娜",),
    monsters: tuple[str, ...] = ("绿水灵",),
    quest: str = "ACTIVE",
    ui: tuple[str, ...] = ("任务提示",),
) -> VisionValidationSample:
    return VisionValidationSample(
        sample_id=sample_id,
        game_profile="maple-v113",
        resolution="800x600",
        window_mode="windowed",
        dpi_scale=1.0,
        image_reference=f"file://{sample_id}.png",
        ground_truth=VisionGroundTruth(
            map_name=map_name,
            aliases=list(aliases),
            hp=hp,
            mp=mp,
            visible_npcs=list(npcs),
            visible_monsters=list(monsters),
            quest_state=quest,
            ui_signals=list(ui),
        ),
    )


def _predict(
    sample: VisionValidationSample,
    *,
    correct: bool = True,
    confidence: float = 0.95,
    ocr_ok: bool = True,
) -> dict:
    gt = sample.ground_truth
    return {
        "visible_map": gt.map_name if correct else "错误地图",
        "visible_entities": [
            {"name": name, "type": "NPC"} for name in gt.visible_npcs
        ]
        + [
            {"name": name, "type": "MONSTER"}
            for name in gt.visible_monsters
        ],
        "hp_reference": gt.hp,
        "mp_reference": gt.mp,
        "quest_state": gt.quest_state,
        "ui_elements": list(gt.ui_signals),
        "confidence": confidence,
        "ocr_ok": ocr_ok,
    }


def test_real_provider_contract():
    provider = WindowsScreenshotProvider(
        window_rect={
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        }
    )
    assert provider.binding_status() == "BOUND"
    frame = provider.capture()
    assert frame.frame_id
    reference = provider.capture_reference()
    assert reference is not None
    # 环境无关:失败尝试也是有效 capture attempt(不要求 headless 成功截图)
    if provider.last_status != CaptureStatus.OK:
        assert frame.confidence == 0.0
        assert reference.confidence == 0.0
    else:
        assert reference.confidence > 0


def test_invalid_window():
    provider = WindowsScreenshotProvider()
    # win32 可用时 binding 为 DISCOVERABLE,但指定窗口不存在时 capture 仍须失败安全
    assert provider.binding_status() in ("NOT_FOUND", "DISCOVERABLE")
    frame = provider.capture()
    assert frame.confidence == 0.0
    assert "unavailable" in frame.image_reference
    reference = provider.capture_reference()
    assert reference is not None
    assert reference.confidence == 0.0
    assert reference.source == "windows/unavailable"


def test_zero_size_window():
    provider = WindowsScreenshotProvider(
        window_rect={"left": 0, "top": 0, "width": 0, "height": 0}
    )
    frame = provider.capture()
    assert frame.confidence == 0.0
    reference = provider.capture_reference()
    assert reference is not None
    assert reference.confidence == 0.0


def test_capture_failure_unsupported_method():
    provider = WindowsScreenshotProvider(
        method="bogus",
        window_rect={
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        },
    )
    frame = provider.capture()
    assert frame.confidence == 0.0
    assert "method-not-supported" in frame.image_reference
    reference = provider.capture_reference()
    assert reference is not None
    assert reference.confidence == 0.0
    assert reference.source == "windows/capture-failed"


def test_headless_capture_failure_deterministic(monkeypatch):
    provider = WindowsScreenshotProvider(
        window_rect={
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        }
    )
    monkeypatch.setattr(
        provider,
        "_capture_region",
        lambda rect: (
            "unavailable://capture-failed",
            CaptureStatus.CAPTURE_FAILED,
        ),
    )
    frame = provider.capture()
    assert frame.confidence == 0.0
    assert provider.last_status is CaptureStatus.CAPTURE_FAILED
    reference = provider.capture_reference()
    assert reference is not None
    assert reference.confidence == 0.0


def test_printwindow_fallback_to_imagegrab(monkeypatch):
    provider = WindowsScreenshotProvider(
        window_rect={
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        }
    )
    monkeypatch.setattr(
        provider,
        "_printwindow",
        lambda rect: (
            "unavailable://printwindow-black",
            CaptureStatus.UNAVAILABLE,
        ),
    )
    reference, status = provider._capture_region(
        {"left": 0, "top": 0, "width": 800, "height": 600}
    )
    assert status is CaptureStatus.OK
    assert provider.capture_method == "imagegrab"
    assert "imagegrab fallback" in provider.fallback_reason


def test_printwindow_success_sets_method(monkeypatch):
    provider = WindowsScreenshotProvider(
        window_rect={
            "left": 0,
            "top": 0,
            "width": 800,
            "height": 600,
        }
    )
    monkeypatch.setattr(
        provider,
        "_printwindow",
        lambda rect: (
            "capture://printwindow/123",
            CaptureStatus.OK,
        ),
    )
    reference, status = provider._capture_region(
        {"left": 0, "top": 0, "width": 800, "height": 600}
    )
    assert status is CaptureStatus.OK
    assert reference == "capture://printwindow/123"
    assert provider.capture_method == "printwindow"


def test_win32_client_to_screen_coordinates():
    provider = WindowsScreenshotProvider(window_title="MapleStory")
    fake_win32 = SimpleNamespace(
        FindWindow=lambda *args: 123,
        GetClientRect=lambda handle: (0, 0, 800, 600),
        ClientToScreen=lambda handle, point: (100, 50),
    )
    provider._win32 = fake_win32
    rect = provider._resolve_rect()
    assert rect == {
        "left": 100,
        "top": 50,
        "width": 800,
        "height": 600,
    }


def test_ocr_backend_adapter():
    provider = RealOCRProvider()
    from maple_agent.vision_runtime.models import VisionFrame

    if provider.available:
        capability = provider.capability()
        assert capability["available"] is True
        assert capability["backend"] in ("tesseract", "windows")
    else:
        result = provider.recognize(VisionFrame(frame_id="f1"))
        assert result.confidence == 0.0
        assert result.source == "ocr-unavailable"


def test_ocr_capability_detection():
    adapter = TesseractOCRAdapter()
    capability = adapter.capability()
    assert capability["backend"] == "tesseract"
    assert capability["available"] is adapter.available
    assert isinstance(capability["languages"], list)
    if adapter.available:
        assert capability["version"]
        assert any(
            language in capability["languages"]
            for language in ("eng", "chi_sim")
        )


def test_ocr_failure():
    provider = RealOCRProvider(backend="windows")
    from maple_agent.vision_runtime.models import VisionFrame

    result = provider.recognize(VisionFrame(frame_id="f1"))
    assert result.text == ""
    assert result.confidence == 0.0


def test_roi_profile():
    profiles = load_vision_profiles()
    assert "default-800x600" in profiles
    profile = profiles["default-800x600"]
    assert profile.map_label_roi
    assert profile.hp_roi
    assert profile.quest_roi
    assert profile.dpi_scale == 1.0


def test_dataset_manifest(tmp_path):
    dataset = VisionValidationDataset.from_manifest(
        FIXTURES / "manifest.json"
    )
    assert dataset.count() == 0
    dataset.add_sample(_sample("s1"))
    assert dataset.count() == 1
    manifest_path = tmp_path / "manifest.json"
    dataset.save_manifest(manifest_path)
    loaded = VisionValidationDataset.from_manifest(manifest_path)
    assert loaded.count() == 1
    assert loaded.samples[0].sample_id == "s1"


def test_benchmark_map_metric():
    samples = [_sample("s1"), _sample("s2")]
    result = RealVisionBenchmark().evaluate(
        samples,
        lambda sample: _predict(sample),
    )
    assert result.map_accuracy == 1.0
    assert result.map_exact_accuracy == 1.0
    assert result.map_alias_accuracy == 0.0


def test_benchmark_hp_metric():
    samples = [
        _sample("s1", hp=0.8, mp=0.6),
        _sample("s2", hp=0.5, mp=0.4),
    ]

    def predict(sample):
        pred = _predict(sample)
        pred["hp_reference"] = sample.ground_truth.hp - 0.05
        pred["mp_reference"] = sample.ground_truth.mp + 0.05
        return pred

    result = RealVisionBenchmark().evaluate(samples, predict)
    assert result.hp_mae == 0.05
    assert result.mp_mae == 0.05


def test_benchmark_quest_metric():
    samples = [_sample("s1", quest="ACTIVE"), _sample("s2", quest="ACTIVE")]

    def predict(sample):
        pred = _predict(sample)
        pred["quest_state"] = "AVAILABLE"
        return pred

    result = RealVisionBenchmark().evaluate(samples, predict)
    assert result.quest_state_accuracy == 0.0


def test_benchmark_entity_precision_recall():
    samples = [
        _sample("s1", npcs=("赫丽娜",), monsters=("绿水灵",)),
        _sample("s2", npcs=("赫丽娜",), monsters=()),
    ]

    def predict(sample):
        pred = _predict(sample)
        pred["visible_entities"] = [
            {"name": "赫丽娜", "type": "NPC"},
            {"name": "错误怪物", "type": "MONSTER"},
        ]
        return pred

    result = RealVisionBenchmark().evaluate(samples, predict)
    assert result.npc_precision == 1.0
    assert result.npc_recall == 1.0
    assert result.monster_precision == 0.0
    assert result.monster_recall == 0.0


def test_benchmark_latency_metrics():
    samples = [_sample("s1")]
    result = RealVisionBenchmark().evaluate(
        samples,
        _predict,
        capture_latencies_ms=[10.0, 20.0, 30.0, 40.0, 50.0],
        ocr_latencies_ms=[5.0, 15.0],
        capture_success_rate=1.0,
        ocr_success_rate=1.0,
    )
    assert result.mean_capture_latency_ms == 30.0
    assert result.p95_capture_latency_ms == 50.0
    assert result.mean_ocr_latency_ms == 10.0


def test_benchmark_latency_percentiles_and_taxonomy():
    samples = [_sample("s1")]
    result = RealVisionBenchmark().evaluate(
        samples,
        _predict,
        capture_latencies_ms=[10.0, 20.0, 30.0, 40.0],
        ocr_latencies_ms=[5.0, 15.0, 25.0],
        e2e_latencies_ms=[15.0, 35.0, 55.0, 75.0],
        capture_success_rate=1.0,
        ocr_success_rate=1.0,
        failure_taxonomy={"BLACK_FRAME": 1},
    )
    assert result.p50_capture_latency_ms == 25.0
    assert result.p95_capture_latency_ms == 40.0
    assert result.p50_ocr_latency_ms == 15.0
    assert result.p95_ocr_latency_ms == 25.0
    assert result.mean_e2e_latency_ms == 45.0
    assert result.p95_e2e_latency_ms == 75.0
    assert result.max_e2e_latency_ms == 75.0
    assert result.failure_taxonomy == {"BLACK_FRAME": 1}
    assert result.confidence_calibration_status == "CALIBRATED"


def test_benchmark_confidence_calibration():
    samples = [_sample("s1"), _sample("s2")]
    result = RealVisionBenchmark().evaluate(
        samples,
        lambda sample: _predict(sample, confidence=0.95),
    )
    assert len(result.confidence_buckets) == 1
    bucket = result.confidence_buckets[0]
    assert bucket.bucket == "0.9-1.0"
    assert bucket.sample_count == 2
    assert bucket.accuracy == 1.0


def test_readiness_not_ready_without_real_client():
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
    )
    assert readiness.validation_status is ReadinessStatus.NOT_READY
    assert readiness.real_client_tested is False


def test_readiness_foundation_only_insufficient():
    samples = [_sample("s1"), _sample("s2")]
    metrics = RealVisionBenchmark().evaluate(
        samples,
        lambda sample: _predict(sample),
    )
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=True,
        capture_provider="windows",
        ocr_provider="tesseract",
    )
    assert readiness.validation_status is ReadinessStatus.FOUNDATION_ONLY


def test_readiness_passed_thresholds():
    samples = [_sample(f"s{i}") for i in range(12)]
    metrics = RealVisionBenchmark().evaluate(
        samples,
        lambda sample: _predict(sample, confidence=0.95),
        capture_success_rate=1.0,
        ocr_success_rate=1.0,
    )
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=True,
        capture_provider="windows",
        ocr_provider="tesseract",
    )
    assert readiness.validation_status is ReadinessStatus.PASSED
    assert readiness.sample_count == 12
    assert readiness.map_detection_accuracy == 1.0


def test_game_state_integration():
    graph = MapleKnowledgeGraph()
    entities, relations = load_demo_knowledge()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    observation = ScreenObservation(
        visible_map="射手村",
        visible_entities=["赫丽娜", "绿水灵"],
        ui_elements=["任务提示"],
        hp_reference=0.8,
        mp_reference=0.6,
        quest_reference=["新手任务"],
        confidence=0.9,
    )
    reference = GameStateExtractor(graph).extract(observation)
    assert isinstance(reference, GameStateReference)
    assert reference.current_map.map_name == "射手村"
    assert reference.player_state.hp == 0.8


def test_replay_generation(tmp_path):
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
    )
    save_real_vision_validation_trace(
        tmp_path,
        "trace-replay",
        provider={"capture_provider": "windows", "ocr_provider": "none"},
        window={"title": "MapleStory"},
        dataset={"sample_count": 0},
        metrics=metrics,
        readiness=readiness.model_dump(mode="json"),
        validation="NOT_READY",
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "real_vision_validation_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["provider"]["capture_provider"] == "windows"
    assert replay["metrics"]["sample_count"] == 0
    assert replay["readiness"]["validation_status"] == "NOT_READY"
    assert replay["validation"] == "NOT_READY"


def test_client_benchmark_report_builder(tmp_path):
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
    )
    report = build_real_vision_client_benchmark_report(
        machine_profile={"host": "home-pc"},
        window={"binding": "NOT_FOUND"},
        capture={"method": "imagegrab"},
        ocr={"backend": "none"},
        dataset={"sample_count": 0},
        metrics=metrics,
        readiness=readiness,
        failures=[{"type": "WINDOW_NOT_FOUND", "message": "window missing"}],
    )
    assert report["schema_version"] == "1.0"
    assert report["window"]["binding"] == "NOT_FOUND"
    assert report["entity_metrics"]["npc"] == "NOT_SUPPORTED"
    assert report["readiness"]["validation_status"] == "NOT_READY"
    path = save_real_vision_client_benchmark(tmp_path, "trace-report", report)
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["machine_profile"]["host"] == "home-pc"
    assert loaded["failure_taxonomy"] == {}


def test_webui_state_mapper():
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
        capture_provider="windows",
        ocr_provider="none",
    )
    state = build_real_vision_webui_state(
        readiness,
        metrics,
        window={
            "binding": "BOUND",
            "window_title": "冒险岛怀旧服",
            "resolution": "2560x1440",
            "dpi_scale": 1.0,
            "window_mode": "fullscreen-windowed",
            "foreground": False,
        },
        ocr_capability={
            "backend": "tesseract",
            "available": True,
            "version": "5.4.0",
            "languages": ["eng"],
            "chinese_support": False,
            "english_support": True,
        },
    )
    assert state["real_client_tested"] is False
    assert state["window_binding"]["title"] == "冒险岛怀旧服"
    assert state["window_binding"]["resolution"] == "2560x1440"
    assert state["ocr_backend"]["backend"] == "tesseract"
    assert state["entity_support"]["npc"] == "NOT_SUPPORTED"
    assert state["confidence_calibration"] == "NOT_CALIBRATED"


def test_webui_real_vision_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
        capture_provider="windows",
        ocr_provider="none",
    )
    payload = {
        "capture_provider": readiness.capture_provider,
        "ocr_provider": readiness.ocr_provider,
        "real_client_tested": readiness.real_client_tested,
        "sample_count": readiness.sample_count,
        "capture_success_rate": metrics.capture_success_rate,
        "map_accuracy": readiness.map_detection_accuracy,
        "hp_mp_accuracy": readiness.hp_mp_accuracy,
        "quest_state_accuracy": readiness.quest_state_accuracy,
        "npc_precision": metrics.npc_precision,
        "npc_recall": metrics.npc_recall,
        "mean_capture_latency_ms": metrics.mean_capture_latency_ms,
        "mean_ocr_latency_ms": metrics.mean_ocr_latency_ms,
        "validation_status": readiness.validation_status.value,
        "reasons": [],
    }
    app = create_app(runtime=runtime, bus=bus, real_vision=payload)
    with TestClient(app) as client:
        resp = client.get("/api/real-vision/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["real_client_tested"] is False
    assert data["validation_status"] == "NOT_READY"


def test_webui_real_vision_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/real-vision/state")
    assert resp.json()["enabled"] is False


def test_smoke_script_no_client(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "scripts/validate_real_vision.py",
            "--frames",
            "1",
            "--output",
            str(tmp_path),
        ],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        timeout=90,
    )
    assert "REAL CLIENT NOT AVAILABLE" in result.stdout
    assert "NOT_READY" in result.stdout
    assert result.returncode == 0
