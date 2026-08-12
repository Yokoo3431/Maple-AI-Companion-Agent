"""Behavior Planning 层(Phase 12-B,高层行为参考,不执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.behavior.goal import GoalMapper
from maple_agent.behavior.models import (
    BehaviorReference,
    BehaviorStep,
    BehaviorStepType,
)
from maple_agent.behavior.planner import BehaviorPlanner
from maple_agent.behavior.sequence import BehaviorSequenceBuilder
from maple_agent.behavior.validator import (
    BehaviorValidationResult,
    BehaviorValidator,
    BehaviorVerdict,
)


def save_behavior_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    goal: str,
    steps: list[BehaviorStep],
    validation: str,
) -> None:
    """写入 behavior_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "goal": goal,
        "steps": [
            {
                "type": step.step_type.value,
                "description": step.description,
            }
            for step in steps
        ],
        "validation": validation,
    }
    (directory / "behavior_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "BehaviorPlanner",
    "BehaviorReference",
    "BehaviorSequenceBuilder",
    "BehaviorStep",
    "BehaviorStepType",
    "BehaviorValidationResult",
    "BehaviorValidator",
    "BehaviorVerdict",
    "GoalMapper",
    "save_behavior_trace",
]
