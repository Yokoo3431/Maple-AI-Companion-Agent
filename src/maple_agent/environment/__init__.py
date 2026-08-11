"""Environment State 层(Phase 8-A,环境状态建模,只读)。"""

from maple_agent.environment.collector import EnvironmentCollector
from maple_agent.environment.models import (
    EnvironmentSnapshot,
    EnvironmentState,
)
from maple_agent.environment.snapshot import EnvironmentSnapshotManager
from maple_agent.environment.state import (
    EnvironmentStateManager,
    save_environment_trace,
)
from maple_agent.environment.validator import (
    EnvironmentValidationResult,
    EnvironmentValidator,
    EnvironmentVerdict,
)

__all__ = [
    "EnvironmentCollector",
    "EnvironmentSnapshot",
    "EnvironmentSnapshotManager",
    "EnvironmentState",
    "EnvironmentStateManager",
    "EnvironmentValidationResult",
    "EnvironmentValidator",
    "EnvironmentVerdict",
    "save_environment_trace",
]
