"""CrossMachineVisionBenchmark:跨机器(Home vs Office)视觉泛化对比(Phase 13-I.2)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class CrossMachineEntry(BaseModel):
    """单台机器视觉能力条目(无法评估输出 None/N/A)。"""

    machine: str
    resolution: str = ""
    dpi: float = Field(default=1.0, ge=0)
    capture_provider: str = ""
    hp_error: float | None = None
    mp_error: float | None = None
    map_top1_accuracy: float | None = None
    template_margin: float | None = None
    capture_latency_ms: float | None = None
    geometry_latency_ms: float | None = None
    template_latency_ms: float | None = None
    ocr_latency_ms: float | None = None
    profile_transform_status: str = ""


class CrossMachineVisionBenchmark(BaseModel):
    """跨机器对比结果。"""

    schema_version: str = "1.0"
    entries: list[CrossMachineEntry] = Field(default_factory=list)
    generalization: dict[str, str] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


def _status(
    home_value,
    office_value,
    *,
    degraded_threshold: float | None = None,
) -> str:
    """按数据判定 PASS/DEGRADED/FAIL/N/A(不制造魔法总分)。"""
    if home_value is None and office_value is None:
        return "N/A"
    if office_value is None:
        return "N/A"
    if home_value is None:
        return "PASS"
    if degraded_threshold is not None:
        if office_value <= degraded_threshold:
            return "PASS"
        return "DEGRADED"
    return "PASS"


def build_cross_machine_benchmark(
    *,
    home: dict,
    office: dict,
) -> CrossMachineVisionBenchmark:
    """HOME 使用 sanitized 13-I.1 数据;OFFICE 使用当前实测。"""
    entries = [
        CrossMachineEntry(machine="HOME", **home),
        CrossMachineEntry(machine="OFFICE", **office),
    ]
    home_entry = entries[0]
    office_entry = entries[1]
    generalization = {
        "resolution": (
            "PASS"
            if office_entry.resolution
            else "N/A"
        ),
        "dpi": "PASS" if office_entry.dpi > 0 else "N/A",
        "capture_provider": (
            "PASS"
            if office_entry.capture_provider
            else "N/A"
        ),
        "hp_error": _status(
            home_entry.hp_error,
            office_entry.hp_error,
            degraded_threshold=0.05,
        ),
        "mp_error": _status(
            home_entry.mp_error,
            office_entry.mp_error,
            degraded_threshold=0.10,
        ),
        "map_top1_accuracy": _status(
            home_entry.map_top1_accuracy,
            office_entry.map_top1_accuracy,
            degraded_threshold=0.5,
        ),
        "template_margin": _status(
            home_entry.template_margin,
            office_entry.template_margin,
            degraded_threshold=0.05,
        ),
        "capture_latency_ms": _status(
            home_entry.capture_latency_ms,
            office_entry.capture_latency_ms,
            degraded_threshold=300.0,
        ),
        "geometry_latency_ms": _status(
            home_entry.geometry_latency_ms,
            office_entry.geometry_latency_ms,
            degraded_threshold=300.0,
        ),
        "template_latency_ms": _status(
            home_entry.template_latency_ms,
            office_entry.template_latency_ms,
            degraded_threshold=50.0,
        ),
        "ocr_latency_ms": _status(
            home_entry.ocr_latency_ms,
            office_entry.ocr_latency_ms,
            degraded_threshold=2000.0,
        ),
        "profile_transform": (
            "PASS"
            if office_entry.profile_transform_status == "OK"
            else (
                "FAIL"
                if office_entry.profile_transform_status
                else "N/A"
            )
        ),
    }
    return CrossMachineVisionBenchmark(
        entries=entries,
        generalization=generalization,
    )
