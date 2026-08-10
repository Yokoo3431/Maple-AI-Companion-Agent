"""Human Confirmation 层(Phase 6-C,人工授权门控,禁止执行)。"""

from maple_agent.confirmation.gate import HumanConfirmationGate
from maple_agent.confirmation.manager import (
    ConfirmationError,
    ConfirmationManager,
)
from maple_agent.confirmation.models import (
    ConfirmationRequest,
    ConfirmationStatus,
    PermissionToken,
)
from maple_agent.confirmation.validator import (
    ConfirmationValidationResult,
    ConfirmationValidator,
)

__all__ = [
    "ConfirmationError",
    "ConfirmationManager",
    "ConfirmationRequest",
    "ConfirmationStatus",
    "ConfirmationValidationResult",
    "ConfirmationValidator",
    "HumanConfirmationGate",
    "PermissionToken",
]
