"""Phase 13-I Real Vision Client Benchmark 报告组装(只读输出)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.real_vision.models import RealVisionBenchmarkResult
from maple_agent.safety_vnext.models import RealVisionReadinessReference


def build_real_vision_client_benchmark_report(
    *,
    machine_profile: dict,
    window: dict,
    capture: dict,
    ocr: dict,
    dataset: dict,
    metrics: RealVisionBenchmarkResult,
    readiness: RealVisionReadinessReference,
    failures: list[dict] | None = None,
) -> dict:
    """组装 `real_vision_client_benchmark.json` 完整报告。"""
    metrics_data = metrics.model_dump(mode="json")
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "machine_profile": dict(machine_profile),
        "window": dict(window),
        "capture": dict(capture),
        "ocr": dict(ocr),
        "dataset": dict(dataset),
        "map_metrics": {
            "exact_accuracy": metrics_data.get("map_exact_accuracy"),
            "alias_accuracy": metrics_data.get("map_alias_accuracy"),
            "overall_accuracy": metrics_data.get("map_accuracy"),
            "sample_count": metrics_data.get("sample_count", 0),
            "confidence": None,
            "failure_examples": [],
        },
        "hp_mp_metrics": {
            "hp_mae": metrics_data.get("hp_mae"),
            "mp_mae": metrics_data.get("mp_mae"),
            "accuracy": readiness.hp_mp_accuracy,
            "method": "numeric-ocr",
            "status": "NOT_MEASURED"
            if readiness.hp_mp_accuracy == 0.0
            else "MEASURED",
        },
        "quest_metrics": {
            "quest_state_accuracy": metrics_data.get("quest_state_accuracy"),
            "ui_signal_accuracy": metrics_data.get("ui_signal_accuracy"),
            "status": "NOT_READY",
        },
        "entity_metrics": {
            "npc": "NOT_SUPPORTED",
            "monster": "NOT_SUPPORTED",
            "item": "NOT_SUPPORTED",
            "note": (
                "no real CV detector; knowledge expectation is not "
                "counted as visual detection"
            ),
        },
        "confidence_calibration": {
            "status": metrics_data.get(
                "confidence_calibration_status", "NOT_CALIBRATED"
            ),
            "buckets": metrics_data.get("confidence_buckets", []),
        },
        "latency": {
            "capture": {
                "mean_ms": metrics_data.get("mean_capture_latency_ms"),
                "p50_ms": metrics_data.get("p50_capture_latency_ms"),
                "p95_ms": metrics_data.get("p95_capture_latency_ms"),
            },
            "ocr": {
                "mean_ms": metrics_data.get("mean_ocr_latency_ms"),
                "p50_ms": metrics_data.get("p50_ocr_latency_ms"),
                "p95_ms": metrics_data.get("p95_ocr_latency_ms"),
            },
            "e2e": {
                "mean_ms": metrics_data.get("mean_e2e_latency_ms"),
                "p50_ms": metrics_data.get("p50_e2e_latency_ms"),
                "p95_ms": metrics_data.get("p95_e2e_latency_ms"),
                "max_ms": metrics_data.get("max_e2e_latency_ms"),
            },
        },
        "failures": list(failures or []),
        "failure_taxonomy": metrics_data.get("failure_taxonomy", {}),
        "readiness": readiness.model_dump(mode="json"),
    }


def save_real_vision_client_benchmark(
    sessions_dir: str | Path,
    trace_id: str,
    report: dict,
) -> Path:
    """写入 `real_vision_client_benchmark.json`(LOCAL ONLY,不进仓库)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / "real_vision_client_benchmark.json"
    target.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target


def build_real_vision_webui_state(
    readiness: RealVisionReadinessReference,
    metrics: RealVisionBenchmarkResult,
    *,
    window: dict | None = None,
    ocr_capability: dict | None = None,
    failure_taxonomy: dict[str, int] | None = None,
) -> dict:
    """WebUI `/api/real-vision/state` 状态映射(只读展示)。"""
    return {
        "capture_provider": readiness.capture_provider,
        "ocr_provider": readiness.ocr_provider,
        "real_client_tested": readiness.real_client_tested,
        "window_binding": {
            "status": (window or {}).get("binding", ""),
            "title": (window or {}).get("window_title", ""),
            "hwnd": (window or {}).get("hwnd"),
            "resolution": (window or {}).get("resolution", ""),
            "dpi_scale": (window or {}).get("dpi_scale", 1.0),
            "window_mode": (window or {}).get("window_mode", ""),
            "foreground": (window or {}).get("foreground", False),
        },
        "capture_backend": {
            "method": readiness.capture_provider,
            "success_rate": metrics.capture_success_rate,
            "mean_latency_ms": metrics.mean_capture_latency_ms,
            "p95_latency_ms": metrics.p95_capture_latency_ms,
        },
        "ocr_backend": {
            "backend": (ocr_capability or {}).get(
                "backend", readiness.ocr_provider
            ),
            "available": bool((ocr_capability or {}).get("available", False)),
            "version": (ocr_capability or {}).get("version", ""),
            "languages": (ocr_capability or {}).get("languages", []),
            "chinese_support": bool(
                (ocr_capability or {}).get("chinese_support", False)
            ),
            "english_support": bool(
                (ocr_capability or {}).get("english_support", False)
            ),
            "success_rate": metrics.ocr_success_rate,
            "mean_latency_ms": metrics.mean_ocr_latency_ms,
        },
        "sample_count": readiness.sample_count,
        "capture_success_rate": metrics.capture_success_rate,
        "map_accuracy": readiness.map_detection_accuracy,
        "map_exact_accuracy": metrics.map_exact_accuracy,
        "map_alias_accuracy": metrics.map_alias_accuracy,
        "hp_mp_accuracy": readiness.hp_mp_accuracy,
        "quest_state_accuracy": readiness.quest_state_accuracy,
        "entity_support": {
            "npc": "NOT_SUPPORTED",
            "monster": "NOT_SUPPORTED",
            "item": "NOT_SUPPORTED",
        },
        "latency": {
            "capture_mean_ms": metrics.mean_capture_latency_ms,
            "capture_p95_ms": metrics.p95_capture_latency_ms,
            "ocr_mean_ms": metrics.mean_ocr_latency_ms,
            "ocr_p95_ms": metrics.p95_ocr_latency_ms,
            "e2e_mean_ms": metrics.mean_e2e_latency_ms,
        },
        "confidence_calibration": metrics.confidence_calibration_status,
        "confidence_buckets": [
            bucket.model_dump(mode="json")
            for bucket in metrics.confidence_buckets
        ],
        "failure_taxonomy": dict(failure_taxonomy or {}),
        "validation_status": readiness.validation_status.value,
        "reasons": list(metrics.reasons),
    }
