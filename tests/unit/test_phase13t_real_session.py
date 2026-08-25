"""Phase 13-T real/replay session validation and runtime hardening tests."""

from __future__ import annotations

from maple_agent.companion_runtime.benchmark import (
    evaluate_scenarios,
    run_long_run_smoke,
)
from maple_agent.companion_runtime.session_validation import (
    build_pending_real_session_report,
)


def test_replay_a_to_j_regression_remains_green():
    report = evaluate_scenarios()

    assert len(report.results) == 10
    assert all(result.passed for result in report.results)
    assert report.metrics.action_leakage_count == 0
    assert report.metrics.confidence_bound_violations == 0


def test_long_run_runtime_hardening_is_append_only_and_deterministic():
    smoke = run_long_run_smoke(101)

    assert smoke.event_count == 101
    assert smoke.snapshot_count == 101
    assert smoke.history_size == 101
    assert smoke.exception_count == 0
    assert smoke.timestamps_monotonic is True
    assert smoke.history_append_only is True
    assert smoke.duplicate_history_entries == 0
    assert smoke.deterministic_context_types is True
    assert smoke.average_observation_interval_ms == 1000.0


def test_pending_real_session_does_not_claim_real_validation():
    report = build_pending_real_session_report()

    assert report.status == "REAL_SESSION_PENDING"
    assert report.observation_count == 0
    assert report.snapshot_count == 0
    assert report.timestamps_monotonic is None
    assert report.history_append_only is None
    assert report.replay_hardening["event_count"] == 101
    assert report.replay_hardening["timestamps_monotonic"] is True


def test_real_session_report_contains_aggregate_fields_only():
    serialized = build_pending_real_session_report().model_dump_json()

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
