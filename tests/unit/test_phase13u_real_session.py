"""Phase 13-U real-session evidence gating and privacy tests."""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.companion_runtime.benchmark import evaluate_scenarios
from maple_agent.companion_runtime.session_validation import (
    build_pending_real_session_report,
)

REPORT_PATH = (
    Path(__file__).parents[2]
    / "docs"
    / "architecture"
    / "companion"
    / "phase13u_real_session_report.json"
)


def test_real_session_pending_is_explicit_and_has_no_real_counts():
    report = build_pending_real_session_report()

    assert report.status == "REAL_SESSION_PENDING"
    assert report.machine_profile == "NOTEBOOK"
    assert report.observation_count == 0
    assert report.snapshot_count == 0
    assert report.session_duration_seconds == 0
    assert report.timestamps_monotonic is None
    assert report.history_append_only is None
    assert report.provenance_profile == {
        "game_profile": "UNKNOWN",
        "server_profile": "UNKNOWN",
        "dataset_version": "UNKNOWN",
    }


def test_pending_report_keeps_replay_hardening_separate_from_real_evidence():
    report = build_pending_real_session_report()
    hardening = report.replay_hardening

    assert hardening["event_count"] == 101
    assert hardening["snapshot_count"] == 101
    assert hardening["history_append_only"] is True
    assert hardening["timestamps_monotonic"] is True
    assert hardening["exception_count"] == 0
    assert report.observation_count == 0
    assert report.snapshot_count == 0


def test_phase13u_report_is_sanitized_aggregate_only():
    payload = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    serialized = json.dumps(payload, ensure_ascii=False)

    assert payload["status"] == "REAL_SESSION_PENDING"
    assert payload["sanitized"] is True
    for forbidden in (
        "screenshot",
        "ocr",
        "raw_observation",
        "character_name",
        "account",
        "PID",
        "HWND",
        "absolute_path",
    ):
        assert forbidden.lower() not in serialized.lower()


def test_phase13r_replay_contract_remains_green_during_u():
    report = evaluate_scenarios()

    assert len(report.results) == 10
    assert all(result.passed for result in report.results)
    assert report.metrics.action_leakage_count == 0
    assert report.metrics.confidence_bound_violations == 0
