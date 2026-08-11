"""EnvironmentHistoryManager:环境历史时间序列(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.environment.models import EnvironmentState
from maple_agent.logging_setup import new_id
from maple_agent.world_model.models import (
    EnvironmentEvent,
    EnvironmentHistory,
    EnvironmentTransition,
    PredictedEnvironmentState,
)


class EnvironmentHistoryManager:
    """追加环境快照与事件,维护时间序列。"""

    def __init__(self, history_id: str | None = None) -> None:
        self.history = EnvironmentHistory(
            history_id=history_id or new_id(),
        )

    def append(self, state: EnvironmentState) -> None:
        self.history.snapshots.append(state)
        self.history.environment_id = state.environment_id

    def add_event(self, event: EnvironmentEvent) -> None:
        self.history.timeline.append(event)

    def last_state(self) -> EnvironmentState | None:
        return (
            self.history.snapshots[-1]
            if self.history.snapshots
            else None
        )

    def previous_state(self) -> EnvironmentState | None:
        if len(self.history.snapshots) > 1:
            return self.history.snapshots[-2]
        return None


def save_world_model_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    history: EnvironmentHistory,
    transition: EnvironmentTransition | None,
    events: list[EnvironmentEvent],
    prediction: PredictedEnvironmentState | None,
) -> None:
    """写入 world_model_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "history": history.model_dump(mode="json"),
        "transition": (
            transition.model_dump(mode="json")
            if transition is not None
            else {}
        ),
        "events": [
            event.model_dump(mode="json") for event in events
        ],
        "prediction": (
            prediction.model_dump(mode="json")
            if prediction is not None
            else {}
        ),
    }
    (directory / "world_model_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
