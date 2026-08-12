"""Safety Architecture vNext 层(Phase 13-E,仅契约与就绪参考,不启用执行)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.safety_vnext.models import (
    ControlledExecutionGateReference,
    ControlledExecutionPolicyReference,
    ControlledExecutionReadinessReference,
    ExecutionBudgetReference,
    ExecutionMode,
    ExecutionSessionReference,
    GameWindowBindingReference,
    GateCheckReference,
    GateCheckStatus,
    GateInputReference,
    GateVerdict,
    KillSwitchReference,
    KillSwitchState,
    KillSwitchType,
    KnowledgeReadinessReference,
    PermissionPolicyV2,
    PermissionScopeV2,
    ReadinessStatus,
    RealVisionReadinessReference,
    SafetyArchitectureVersion,
)
from maple_agent.safety_vnext.policy import SafetyVNextPolicyService
from maple_agent.safety_vnext.validator import (
    ControlledExecutionGateEvaluator,
    aggregate_readiness,
)


def save_controlled_execution_gate_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    action: str,
    checks: list[GateCheckReference],
    verdict: str,
    blocked_reasons: list[str],
) -> None:
    """写入 controlled_execution_gate_trace.json(只读审计,无执行数据)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "action": action,
        "checks": [
            {
                "gate": check.gate_name,
                "result": check.status.value,
                "reason": check.reason,
            }
            for check in checks
        ],
        "verdict": verdict,
        "blocked_reasons": blocked_reasons,
    }
    (directory / "controlled_execution_gate_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

__all__ = [
    "ControlledExecutionGateEvaluator",
    "ControlledExecutionGateReference",
    "ControlledExecutionPolicyReference",
    "ControlledExecutionReadinessReference",
    "ExecutionBudgetReference",
    "ExecutionMode",
    "ExecutionSessionReference",
    "GateCheckReference",
    "GateCheckStatus",
    "GateInputReference",
    "GameWindowBindingReference",
    "GateVerdict",
    "KillSwitchReference",
    "KillSwitchState",
    "KillSwitchType",
    "KnowledgeReadinessReference",
    "PermissionPolicyV2",
    "PermissionScopeV2",
    "ReadinessStatus",
    "RealVisionReadinessReference",
    "SafetyArchitectureVersion",
    "SafetyVNextPolicyService",
    "aggregate_readiness",
    "save_controlled_execution_gate_trace",
]
