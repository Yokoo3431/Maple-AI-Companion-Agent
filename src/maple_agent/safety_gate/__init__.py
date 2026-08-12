"""Safety Gate 层(Phase 13-A,动作安全审核,只读,不执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.safety_gate.evaluator import SafetyEvaluator
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.safety_gate.rules import SafetyRules
from maple_agent.safety_gate.validator import (
    SafetyGateValidationResult,
    SafetyGateValidator,
    SafetyGateVerdict,
)


def save_safety_gate_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    action: str,
    decision: str,
    risk_factors: list[str],
    validation: str,
) -> None:
    """写入 safety_gate_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "action": action,
        "decision": decision,
        "risk_factors": risk_factors,
        "validation": validation,
    }
    (directory / "safety_gate_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "SafetyDecisionType",
    "SafetyEvaluationReference",
    "SafetyEvaluator",
    "SafetyGateValidationResult",
    "SafetyGateValidator",
    "SafetyGateVerdict",
    "SafetyRules",
    "save_safety_gate_trace",
]
