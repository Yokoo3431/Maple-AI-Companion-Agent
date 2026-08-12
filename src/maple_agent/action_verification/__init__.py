"""Action Outcome Verification 层(Phase 13-C,只验证结果,不执行动作)。"""

import json
from pathlib import Path

from maple_agent.action_verification.comparator import GameStateComparator
from maple_agent.action_verification.expectation import (
    ActionExpectationBuilder,
)
from maple_agent.action_verification.models import (
    ActionOutcomeReference,
    ActionOutcomeStatus,
    ExpectedOutcomeReference,
    OutcomeEvidence,
)
from maple_agent.action_verification.timeout import OutcomeTimeoutPolicy
from maple_agent.action_verification.validator import (
    ActionOutcomeValidationResult,
    ActionOutcomeValidator,
    ActionOutcomeVerdict,
)
from maple_agent.action_verification.verifier import ActionOutcomeVerifier
from maple_agent.architecture import TRACE_SCHEMA_VERSION


def save_action_verification_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    action: dict,
    expectation: dict,
    before_state: dict,
    after_state: dict,
    evidence: list[OutcomeEvidence],
    outcome: ActionOutcomeReference,
    validation: str,
) -> None:
    """写入 action_verification_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "action": action,
        "expectation": expectation,
        "before_state": before_state,
        "after_state": after_state,
        "evidence": [
            item.model_dump(mode="json") for item in evidence
        ],
        "outcome": {
            "status": outcome.status.value,
            "confidence": outcome.confidence,
            "recovery_required": outcome.recovery_required,
        },
        "validation": validation,
    }
    (directory / "action_verification_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "ActionExpectationBuilder",
    "ActionOutcomeReference",
    "ActionOutcomeStatus",
    "ActionOutcomeValidationResult",
    "ActionOutcomeValidator",
    "ActionOutcomeVerdict",
    "ActionOutcomeVerifier",
    "ExpectedOutcomeReference",
    "GameStateComparator",
    "OutcomeEvidence",
    "OutcomeTimeoutPolicy",
    "save_action_verification_trace",
]
