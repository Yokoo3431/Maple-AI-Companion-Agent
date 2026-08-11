"""EnvironmentStateManager:环境状态持有与更新(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.environment.models import EnvironmentSnapshot, EnvironmentState
from maple_agent.environment.validator import EnvironmentValidationResult


class EnvironmentStateManager:
    """维护当前环境状态(支持前后比较)。"""

    def __init__(self) -> None:
        self._current: EnvironmentState | None = None

    @property
    def current(self) -> EnvironmentState | None:
        return self._current

    def update(self, state: EnvironmentState) -> None:
        self._current = state


def save_environment_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    environment_state: EnvironmentState,
    snapshot: EnvironmentSnapshot | None,
    validation: EnvironmentValidationResult,
) -> None:
    """写入 environment_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "environment_state": environment_state.model_dump(mode="json"),
        "snapshot": (
            snapshot.model_dump(mode="json")
            if snapshot is not None
            else {}
        ),
        "validation": validation.verdict.value,
    }
    (directory / "environment_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
