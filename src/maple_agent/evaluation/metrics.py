"""统一评分:Overall Score 加权公式。"""

from __future__ import annotations

WEIGHTS = {
    "decision": 0.25,
    "planning": 0.20,
    "execution": 0.20,
    "reflection": 0.20,
    "experience": 0.15,
}


def overall_score(
    decision: float,
    planning: float,
    execution: float,
    reflection: float,
    memory: float,
) -> float:
    """Overall = D*0.25 + P*0.20 + E*0.20 + R*0.20 + M*0.15。"""
    raw = (
        decision * WEIGHTS["decision"]
        + planning * WEIGHTS["planning"]
        + execution * WEIGHTS["execution"]
        + reflection * WEIGHTS["reflection"]
        + memory * WEIGHTS["experience"]
    )
    return round(max(0.0, min(1.0, raw)), 4)
