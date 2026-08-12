"""Action Proposal 层(Phase 12-C,动作建议参考,不执行)。"""

import json
from pathlib import Path

from maple_agent.action_proposal.mapper import ActionProposalMapper
from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.action_proposal.resolver import ActionTargetResolver
from maple_agent.action_proposal.validator import (
    ActionProposalValidationResult,
    ActionProposalValidator,
    ActionProposalVerdict,
)
from maple_agent.architecture import TRACE_SCHEMA_VERSION


def save_action_proposal_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    actions: list[ActionProposalReference],
    validation: str,
) -> None:
    """写入 action_proposal_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "actions": [
            {
                "type": action.action_type.value,
                "target": action.target_reference,
                "source_behavior": action.source_behavior,
            }
            for action in actions
        ],
        "validation": validation,
    }
    (directory / "action_proposal_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "ActionProposalMapper",
    "ActionProposalReference",
    "ActionProposalValidationResult",
    "ActionProposalValidator",
    "ActionProposalVerdict",
    "ActionTargetResolver",
    "ActionType",
    "save_action_proposal_trace",
]
