"""EnvironmentReasoner:环境状态/历史/事件 -> 语义解释(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.context.models import KnowledgeState
from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_reasoning.models import (
    EnvironmentInterpretation,
    EnvironmentRiskReference,
    OpportunityReference,
)
from maple_agent.world_model.models import (
    EnvironmentEvent,
    EnvironmentHistory,
)


class EnvironmentReasoner:
    """把环境状态与变化历史解释为语义含义。"""

    def interpret(
        self,
        *,
        environment_state: EnvironmentState,
        environment_history: EnvironmentHistory | None = None,
        world_events: list[EnvironmentEvent] | None = None,
        knowledge_state: KnowledgeState | None = None,
    ) -> EnvironmentInterpretation:
        meaning_parts: list[str] = []
        causes: list[str] = []
        if environment_state.location:
            meaning_parts.append(f"当前位于 {environment_state.location}")
        if environment_state.visible_entities:
            meaning_parts.append(
                "可见实体: " + ", ".join(environment_state.visible_entities)
            )
        if environment_state.resources:
            meaning_parts.append(
                "可用资源: " + ", ".join(environment_state.resources)
            )
        if world_events:
            for event in world_events[:3]:
                causes.append(f"{event.event_type.value}: {event.detail}")
        if environment_state.world_context:
            meaning_parts.append(environment_state.world_context)
        event_boost = min(0.1, len(world_events or []) * 0.02)
        semantic_confidence = round(
            min(1.0, environment_state.confidence + event_boost),
            4,
        )
        return EnvironmentInterpretation(
            meaning="。".join(meaning_parts) if meaning_parts else "环境信息不足",
            possible_causes=causes or ["无明确变化原因"],
            semantic_confidence=semantic_confidence,
        )


def save_environment_reasoning_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    interpretation: EnvironmentInterpretation,
    opportunities: list[OpportunityReference],
    risks: list[EnvironmentRiskReference],
) -> None:
    """写入 environment_reasoning_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "interpretation": interpretation.model_dump(mode="json"),
        "opportunities": [
            opportunity.model_dump(mode="json")
            for opportunity in opportunities
        ],
        "risks": [
            risk.model_dump(mode="json") for risk in risks
        ],
    }
    (directory / "environment_reasoning_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
