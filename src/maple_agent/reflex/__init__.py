"""L1 Reflex 层(Phase 10-B,快速状态感知参考,只读,不执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.reflex.detector import ReflexStateDetector
from maple_agent.reflex.event import DangerEventDetector
from maple_agent.reflex.models import (
    DangerEventReference,
    DangerEventType,
    HpMpReference,
    ReflexReference,
    ReflexStateType,
)
from maple_agent.reflex.threshold import ReflexThresholds
from maple_agent.reflex.validator import (
    ReflexValidationResult,
    ReflexValidator,
    ReflexVerdict,
)


def save_reflex_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    state: ReflexReference,
    hp_reference: HpMpReference | None,
    mp_reference: HpMpReference | None,
    danger_events: list[DangerEventReference],
    thresholds: dict,
    validation: str,
) -> None:
    """写入 reflex_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "state": state.model_dump(mode="json"),
        "hp_reference": (
            hp_reference.model_dump(mode="json")
            if hp_reference is not None
            else {}
        ),
        "mp_reference": (
            mp_reference.model_dump(mode="json")
            if mp_reference is not None
            else {}
        ),
        "danger_events": [
            event.model_dump(mode="json") for event in danger_events
        ],
        "thresholds": thresholds,
        "validation": validation,
    }
    (directory / "reflex_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "DangerEventDetector",
    "DangerEventReference",
    "DangerEventType",
    "HpMpReference",
    "ReflexReference",
    "ReflexStateDetector",
    "ReflexStateType",
    "ReflexThresholds",
    "ReflexValidationResult",
    "ReflexValidator",
    "ReflexVerdict",
    "save_reflex_trace",
]
