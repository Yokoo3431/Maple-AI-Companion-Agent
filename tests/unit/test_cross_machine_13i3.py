"""Phase 13-I.3 Cross-machine Evidence Gate 单测(CI 安全,fixtures only)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.hybrid_vision import (
    BenchmarkPrivacySanitizer,
    VisionProfileRegistry,
    build_cross_machine_benchmark,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_display_resolution_separated_from_client_resolution():
    registry = VisionProfileRegistry()
    office = registry.get("office_pc_1920x1080")
    assert office is not None
    assert office.resolution == "1366x768"  # GAME CLIENT(transform 目标)
    assert office.display_resolution == "1920x1080"  # 显示器(仅元数据)
    assert office.resolution != office.display_resolution


def test_home_office_entries_kept_separate():
    home = {
        "resolution": "2560x1440",
        "dpi": 1.0,
        "capture_provider": "wgc+imagegrab",
        "hp_error": 0.87,
        "mp_error": 0.93,
        "map_top1_accuracy": 1.0,
        "template_margin": 0.86,
        "capture_latency_ms": 169.0,
        "geometry_latency_ms": 145.0,
        "template_latency_ms": 4.5,
        "ocr_latency_ms": 719.0,
        "profile_transform_status": "OK",
    }
    office = {
        "resolution": "1366x768",
        "dpi": 1.0,
        "capture_provider": "wgc",
        "hp_error": None,  # OFFICE 无真实 HP dataset -> N/A,禁止用 HOME 补
        "mp_error": None,
        "map_top1_accuracy": None,
        "capture_latency_ms": 405.0,
        "profile_transform_status": "OK",
    }
    benchmark = build_cross_machine_benchmark(home=home, office=office)
    assert [entry.machine for entry in benchmark.entries] == ["HOME", "OFFICE"]
    assert benchmark.entries[0].hp_error == 0.87
    assert benchmark.entries[1].hp_error is None
    assert benchmark.generalization["hp_error"] == "N/A"
    assert benchmark.generalization["mp_error"] == "N/A"


def test_office_na_not_fabricated_with_home_values():
    office = {
        "resolution": "1366x768",
        "dpi": 1.0,
        "capture_provider": "wgc",
        "hp_error": None,
        "mp_error": None,
        "map_top1_accuracy": None,
        "profile_transform_status": "OK",
    }
    home = {
        "resolution": "2560x1440",
        "dpi": 1.0,
        "capture_provider": "wgc",
        "hp_error": 0.87,
        "mp_error": 0.93,
        "map_top1_accuracy": 1.0,
        "profile_transform_status": "OK",
    }
    benchmark = build_cross_machine_benchmark(home=home, office=office)
    office_entry = benchmark.entries[1]
    assert office_entry.hp_error is None
    assert office_entry.mp_error is None
    assert office_entry.map_top1_accuracy is None


def test_public_report_exists_and_is_privacy_safe():
    report_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i3_public.json"
    )
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    sanitizer = BenchmarkPrivacySanitizer()
    sanitizer.assert_safe(payload)
    rendered = json.dumps(payload, ensure_ascii=False)
    assert ":\\" not in rendered
    assert "sessions" not in rendered
    assert '"pid"' not in rendered
    assert '"hwnd"' not in rendered


def test_public_report_has_provenance_and_generalization():
    report_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i3_public.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert payload["map"]["HOME"]["evidence_provenance"] == "REAL_HOME"
    assert payload["map"]["OFFICE"]["evidence_provenance"] == "N/A"
    assert payload["hp_mp"]["OFFICE"]["evidence_provenance"] == "N/A"
    assert payload["generalization"]["HP"] in ("PASS", "DEGRADED", "FAIL", "N/A")
    assert payload["generalization"]["MP"] in ("PASS", "DEGRADED", "FAIL", "N/A")
    assert payload["generalization"]["WGC"] == "PASS"
    assert payload["generalization"]["PROFILE_TRANSFORM"] == "PASS"
    assert payload["readiness"]["real_vision"] == "FOUNDATION_ONLY"
    assert payload["readiness"]["overall_controlled_execution"] == "NOT_READY"


def test_collector_default_output_is_private():
    collector = (
        REPO_ROOT / "scripts" / "collect_real_vision_frames.py"
    ).read_text(encoding="utf-8")
    assert "sessions/13i3_" in collector
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "sessions/" in gitignore


def test_home_condition_matrix_recorded():
    report_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i3_public.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    conditions = payload["capture_conditions"]["HOME"]
    assert conditions["FOREGROUND"]["status"] == "OK"
    assert conditions["BACKGROUND_VISIBLE"]["status"] == "OK"
    assert conditions["BACKGROUND_OCCLUDED"]["status"] == "OK"
    assert conditions["MINIMIZED"]["status"] == "NOT_SUPPORTED"
    office_conditions = payload["capture_conditions"]["OFFICE"]
    assert office_conditions["MINIMIZED"]["status"] == "NOT_SUPPORTED"
