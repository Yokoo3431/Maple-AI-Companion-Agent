"""Sanitized validation reports for real-session readiness."""

from __future__ import annotations

from pydantic import BaseModel, Field


class RealSessionReport(BaseModel):
    """Aggregate-only real-session evidence; raw captures never enter this model."""

    status: str
    machine_profile: str
    capture_backend: str
    window_state: str
    session_duration_seconds: float = Field(ge=0)
    observation_count: int = Field(ge=0)
    snapshot_count: int = Field(ge=0)
    failure_counts: dict[str, int] = Field(default_factory=dict)
    average_observation_interval_ms: float | None = Field(default=None, ge=0)
    average_cognitive_latency_ms: float | None = Field(default=None, ge=0)
    average_snapshot_latency_ms: float | None = Field(default=None, ge=0)
    history_size: int = Field(ge=0)
    memory_growth_bytes: int | None = Field(default=None, ge=0)
    stale_count: int = Field(default=0, ge=0)
    unknown_count: int = Field(default=0, ge=0)
    resolved_evidence_count: int = Field(default=0, ge=0)
    unresolved_evidence_count: int = Field(default=0, ge=0)
    provenance_profile: dict[str, str] = Field(default_factory=dict)
    privacy_status: str = "RAW_VISION_DATA=LOCAL_PRIVATE"
    safety_status: str = "MOCK_ONLY_READ_ONLY_NO_EXECUTION"
    sanitized: bool = True


def build_pending_real_session_report() -> RealSessionReport:
    """Notebook-safe report when no Maple client/session evidence is available."""
    return RealSessionReport(
        status="REAL_SESSION_PENDING",
        machine_profile="NOTEBOOK",
        capture_backend="NOT_RUN_NO_MAPLE_CLIENT_EVIDENCE",
        window_state="NOT_OBSERVED",
        session_duration_seconds=0,
        observation_count=0,
        snapshot_count=0,
        failure_counts={"REAL_SESSION_NOT_AVAILABLE": 1},
        history_size=0,
        provenance_profile={
            "game_profile": "UNKNOWN",
            "server_profile": "UNKNOWN",
            "dataset_version": "UNKNOWN",
        },
    )
