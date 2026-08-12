"""Navigation Planning 层(Phase 12-A,只读导航参考,不执行移动)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.navigation.cost import CostCalculator
from maple_agent.navigation.models import (
    NavigationReference,
    RouteStep,
    RouteStepType,
)
from maple_agent.navigation.planner import NavigationPlanner
from maple_agent.navigation.resolver import TargetResolver
from maple_agent.navigation.route_graph import RouteGraph
from maple_agent.navigation.validator import (
    NavigationValidationResult,
    NavigationValidator,
    NavigationVerdict,
)


def save_navigation_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    start: str,
    target: str,
    route: list[RouteStep],
    validation: str,
) -> None:
    """写入 navigation_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "start": start,
        "target": target,
        "route": [
            {
                "type": step.step_type.value,
                "source": step.source,
                "target": step.target,
            }
            for step in route
        ],
        "validation": validation,
    }
    (directory / "navigation_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "CostCalculator",
    "NavigationPlanner",
    "NavigationReference",
    "NavigationValidationResult",
    "NavigationValidator",
    "NavigationVerdict",
    "RouteGraph",
    "RouteStep",
    "RouteStepType",
    "TargetResolver",
    "save_navigation_trace",
]
