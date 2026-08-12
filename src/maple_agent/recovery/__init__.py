"""Failure Recovery 层(Phase 13-B,失败检测与恢复建议,只读,不执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.recovery.detector import FailureDetector
from maple_agent.recovery.models import (
    FailureType,
    RecoveryReference,
    RecoveryType,
)
from maple_agent.recovery.planner import RecoveryPlanner
from maple_agent.recovery.validator import (
    RecoveryValidationResult,
    RecoveryValidator,
    RecoveryVerdict,
)


def save_recovery_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    action: str,
    failure: str,
    recovery: str,
    validation: str,
) -> None:
    """写入 recovery_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "action": action,
        "failure": failure,
        "recovery": recovery,
        "validation": validation,
    }
    (directory / "recovery_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "FailureDetector",
    "FailureType",
    "RecoveryReference",
    "RecoveryType",
    "RecoveryValidationResult",
    "RecoveryValidator",
    "RecoveryVerdict",
    "RecoveryPlanner",
    "save_recovery_trace",
]
