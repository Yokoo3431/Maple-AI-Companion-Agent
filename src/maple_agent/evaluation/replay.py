"""Temporal context replay using the existing Phase 13-K state projection."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.context_reasoning.models import ContextType, TemporalState
from maple_agent.context_reasoning.reasoner import ContextReasoner
from maple_agent.game_state.models import EntityLifecycle, SemanticGameState


class TemporalReplayStep(BaseModel):
    """Sanitized result for one lifecycle point in a replay."""

    sequence: int
    state_id: str
    lifecycle: EntityLifecycle
    context_type: ContextType
    active: bool
    historical_reference: bool
    uncertainty_count: int = Field(ge=0)


class TemporalReplayReport(BaseModel):
    """Replay output containing state transitions, never raw evidence."""

    trace_id: str
    lifecycle_sequence: list[EntityLifecycle]
    steps: list[TemporalReplayStep]
    sanitized: bool = True


def run_temporal_replay(
    reasoner: ContextReasoner,
    states: list[SemanticGameState],
    *,
    trace_id: str = "phase13p-semantic-context-replay",
) -> TemporalReplayReport:
    """Evaluate states produced by the existing temporal-memory chain."""
    steps: list[TemporalReplayStep] = []
    lifecycle_sequence: list[EntityLifecycle] = []
    for sequence, state in enumerate(states, start=1):
        temporal = TemporalState.from_semantic_state(state)
        context = reasoner.reason(state, temporal)
        references = [state.location, *state.nearby_entities]
        lifecycles = [
            reference.lifecycle
            for reference in references
            if reference is not None
        ]
        lifecycle = lifecycles[0] if lifecycles else EntityLifecycle.UNKNOWN
        lifecycle_sequence.append(lifecycle)
        steps.append(
            TemporalReplayStep(
                sequence=sequence,
                state_id=state.state_id,
                lifecycle=lifecycle,
                context_type=context.context_type,
                active=context.context_type is not ContextType.UNKNOWN_CONTEXT,
                historical_reference=any(
                    entity.historical_only for entity in context.related_entities
                ),
                uncertainty_count=len(context.uncertainties),
            )
        )
    return TemporalReplayReport(
        trace_id=trace_id,
        lifecycle_sequence=lifecycle_sequence,
        steps=steps,
    )


def write_temporal_replay_report(
    report: TemporalReplayReport,
    output_dir: str | Path,
    *,
    filename: str = "semantic_context_replay_report.json",
) -> Path:
    """Write only the sanitized replay model to a caller-provided directory."""
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / filename
    target.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return target
