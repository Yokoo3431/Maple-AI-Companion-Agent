"""Aggregated quality metrics for deterministic context understanding."""

from __future__ import annotations

from collections import Counter

from pydantic import BaseModel, Field

from maple_agent.context_reasoning.models import ContextType, ContextUnderstanding


class ContextReasoningBenchmarkResult(BaseModel):
    """Metrics with explicit denominators for a context-evaluation batch."""

    total_contexts: int = Field(default=0, ge=0)
    promoted_contexts: int = Field(default=0, ge=0)
    uncertain_contexts: int = Field(default=0, ge=0)
    context_type_counts: dict[str, int] = Field(default_factory=dict)
    promotion_rate: float | None = None
    uncertainty_rate: float | None = None
    relation_provenance_coverage: float | None = None


class ContextReasoningBenchmark:
    """Evaluate only supplied context outputs; never fabricates a denominator."""

    @staticmethod
    def evaluate(
        contexts: list[ContextUnderstanding],
    ) -> ContextReasoningBenchmarkResult:
        total = len(contexts)
        promoted = sum(
            context.context_type is not ContextType.UNKNOWN_CONTEXT
            for context in contexts
        )
        uncertain = sum(bool(context.uncertainties) for context in contexts)
        relations = [
            relation
            for context in contexts
            for relation in context.related_relations
        ]
        complete_provenance = sum(
            bool(
                relation.provenance.source_id
                and relation.provenance.source_type
                and relation.provenance.data_version
            )
            for relation in relations
        )
        return ContextReasoningBenchmarkResult(
            total_contexts=total,
            promoted_contexts=promoted,
            uncertain_contexts=uncertain,
            context_type_counts=dict(
                Counter(context.context_type.value for context in contexts)
            ),
            promotion_rate=round(promoted / total, 4) if total else None,
            uncertainty_rate=round(uncertain / total, 4) if total else None,
            relation_provenance_coverage=(
                round(complete_provenance / len(relations), 4)
                if relations
                else None
            ),
        )
