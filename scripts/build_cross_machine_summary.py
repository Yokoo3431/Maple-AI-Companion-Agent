"""Cross-machine 汇总 + repository-safe public report(Phase 13-I.3)。

HOME 使用本地 benchmark 结果;OFFICE 使用 pause checkpoint 保留的真实证据。
证据来源标注 REAL_HOME / REAL_OFFICE / N/A,不制造统一掩盖差异的结论。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.hybrid_vision import (  # noqa: E402
    BenchmarkPrivacySanitizer,
    build_cross_machine_benchmark,
)
from maple_agent.real_vision import (  # noqa: E402
    RealVisionBenchmarkResult,
    build_real_vision_readiness,
)

OFFICE_PAUSE_EVIDENCE = {
    "resolution": "1366x768",
    "dpi": 1.0,
    "capture_provider": "wgc",
    "hp_error": None,
    "mp_error": None,
    "map_top1_accuracy": None,
    "template_margin": None,
    "capture_latency_ms": 405.0,
    "geometry_latency_ms": None,
    "template_latency_ms": None,
    "ocr_latency_ms": None,
    "profile_transform_status": "OK",
}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Cross-machine 汇总(只读,生成 public report)"
    )
    parser.add_argument(
        "--home-benchmark",
        default=(
            "sessions/hybrid_benchmark_13i3_home_multi_v2/"
            "hybrid_vision_benchmark_raw.json"
        ),
    )
    parser.add_argument(
        "--output-dir", default="docs/architecture/vision"
    )
    args = parser.parse_args()
    home_raw = json.loads(
        Path(args.home_benchmark).read_text(encoding="utf-8")
    )
    home = {
        "resolution": home_raw["machine_profile"]["client_resolution"],
        "dpi": home_raw["machine_profile"]["dpi_scale"],
        "capture_provider": "wgc+imagegrab",
        "hp_error": round(
            abs(1.0 - home_raw["providers"]["hpmp_geometry"]["hp_mean_ratio"])
            if home_raw["providers"]["hpmp_geometry"]["hp_mean_ratio"]
            is not None
            else None,
            4,
        ),
        "mp_error": round(
            abs(1.0 - home_raw["providers"]["hpmp_geometry"]["mp_mean_ratio"])
            if home_raw["providers"]["hpmp_geometry"]["mp_mean_ratio"]
            is not None
            else None,
            4,
        ),
        "map_top1_accuracy": home_raw["metrics"][
            "multi_map_top1_accuracy"
        ],
        "template_margin": home_raw["metrics"]["multi_map_margin_mean"]
        if home_raw["metrics"].get("multi_map_margin_mean") is not None
        else home_raw["providers"]["template"].get("margin"),
        "capture_latency_ms": 169.0,  # WGC foreground 实测均值
        "geometry_latency_ms": home_raw["providers"]["hpmp_geometry"][
            "latency"
        ]["mean_ms"],
        "template_latency_ms": home_raw["providers"]["template"]["latency"][
            "mean_ms"
        ],
        "ocr_latency_ms": home_raw["providers"]["tesseract_roi"]["latency"][
            "mean_ms"
        ],
        "profile_transform_status": home_raw["machine_profile"][
            "profile_transform_status"
        ],
    }
    benchmark = build_cross_machine_benchmark(
        home=home,
        office=dict(OFFICE_PAUSE_EVIDENCE),
    )
    wgc_home = {
        "FOREGROUND": {"status": "OK", "latency_ms": 165.6},
        "BACKGROUND_VISIBLE": {"status": "OK", "latency_ms": 388.5},
        "BACKGROUND_OCCLUDED": {"status": "OK", "latency_ms": 392.4},
        "MINIMIZED": {"status": "NOT_SUPPORTED", "frames": 0},
    }
    wgc_office = {
        "FOREGROUND": {"status": "OK", "latency_ms": 405.0},
        "MINIMIZED": {
            "status": "NOT_SUPPORTED",
            "frames": 25,
            "note": "25 frames all WINDOW_INVALID",
        },
    }
    event_trace = None
    trace_path = Path(
        "sessions/event_trace_13i3_home/event_trace_public.json"
    )
    if trace_path.is_file():
        event_trace = json.loads(trace_path.read_text(encoding="utf-8"))
    public_report = {
        "schema_version": "1.0",
        "privacy": "REPOSITORY SAFE - no raw screenshots, no absolute paths, no PID/HWND",
        "phase": "13-I.3",
        "cross_machine": benchmark.model_dump(mode="json"),
        "capture_conditions": {
            "HOME": wgc_home,
            "OFFICE": wgc_office,
        },
        "generalization": {
            "PROFILE_TRANSFORM": "PASS",
            "WGC": "PASS",
            "HP": "FAIL",
            "MP": "FAIL",
            "MAP": "PASS",
            "EVENT_SCHEDULER": "PASS",
        },
        "hp_mp": {
            "HOME": {
                "evidence_provenance": "REAL_HOME",
                "color_mode": "green",
                "hp_gt": 1.0,
                "hp_mean": home_raw["providers"]["hpmp_geometry"][
                    "hp_mean_ratio"
                ],
                "hp_error": home["hp_error"],
                "mp_gt": 1.0,
                "mp_mean": home_raw["providers"]["hpmp_geometry"][
                    "mp_mean_ratio"
                ],
                "mp_error": home["mp_error"],
                "blocker": (
                    "segmented green bar model: median-row-extent reads "
                    "segment length, not fill ratio; requires 13-I.4 "
                    "bar-model calibration (no post-hoc compensation)"
                ),
            },
            "OFFICE": {
                "evidence_provenance": "N/A",
                "note": "no real HP/MP dataset collected on OFFICE",
            },
        },
        "map": {
            "HOME": {
                "evidence_provenance": "REAL_HOME",
                "real_maps": ["射手村", "射手村集市"],
                "queries": 28,
                "top1_accuracy": home_raw["metrics"][
                    "multi_map_top1_accuracy"
                ],
                "unknown_rate": home_raw["metrics"][
                    "multi_map_unknown_rate"
                ],
                "false_positive_rate": home_raw["metrics"][
                    "multi_map_false_positive_rate"
                ],
                "margin_mean": home_raw["metrics"].get(
                    "multi_map_margin_mean"
                ),
                "ocr_accuracy": home_raw["metrics"][
                    "map_ocr_exact_accuracy"
                ],
            },
            "OFFICE": {
                "evidence_provenance": "N/A",
                "note": "no real map dataset collected on OFFICE",
            },
        },
        "event_scheduler": (
            event_trace["summary"] if event_trace else None
        ),
        "latency": {
            "HOME": {
                "wgc_foreground_ms": 165.6,
                "imagegrab_foreground_ms": 335.5,
                "change_detector_ms": home_raw["providers"][
                    "change_detector"
                ]["latency_ms"]["mean"],
                "geometry_ms": home["geometry_latency_ms"],
                "template_ms": home["template_latency_ms"],
                "ocr_ms": home["ocr_latency_ms"],
            },
            "OFFICE": {
                "wgc_foreground_ms": 405.0,
            },
        },
    }
    metrics = RealVisionBenchmarkResult(
        sample_count=28,
        map_accuracy=home["map_top1_accuracy"],
        capture_success_rate=1.0,
        mean_capture_latency_ms=home["capture_latency_ms"],
        mean_ocr_latency_ms=home["ocr_latency_ms"],
    )
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=True,
        capture_provider="wgc+imagegrab",
        ocr_provider="tesseract",
    )
    public_report["readiness"] = {
        "real_vision": readiness.validation_status.value,
        "knowledge": "FOUNDATION_ONLY",
        "overall_controlled_execution": "NOT_READY",
        "reasons": readiness.reasons if hasattr(readiness, "reasons") else [],
    }
    sanitizer = BenchmarkPrivacySanitizer()
    sanitizer.assert_safe(public_report)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "real_vision_13i3_public.json"
    target.write_text(
        json.dumps(public_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(public_report["generalization"], ensure_ascii=False))
    print(
        "readiness:",
        readiness.validation_status.value,
        "| map_top1:",
        home["map_top1_accuracy"],
        "| hp_error:",
        home["hp_error"],
        "| mp_error:",
        home["mp_error"],
    )
    print(f"PUBLIC REPORT: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
