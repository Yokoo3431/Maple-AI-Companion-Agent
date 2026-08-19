"""Phase 13-Q reference benchmark and quality metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from maple_agent.context_reasoning.models import TemporalState
from maple_agent.context_reasoning.reasoner import ContextReasoner
from maple_agent.evaluation.benchmark import load_benchmark_fixture
from maple_agent.game_state.models import EntityLifecycle
from maple_agent.planning_reference.models import (
    PlanningReferenceCase,
    PlanningReferenceEvaluationReport,
    PlanningReferenceEvaluationResult,
    PlanningReferenceMetrics,
)
from maple_agent.planning_reference.reference import PlanningReferenceEngine


def load_benchmark_cases(
    path: str | Path | None = None,
) -> list[PlanningReferenceCase]:
    """Load the sanitized manifest and reuse the Phase 13-P semantic fixture."""
    manifest_path = Path(path) if path is not None else (
        Path(__file__).parent / "phase13q_benchmark.json"
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    graph, phase13p_cases = load_benchmark_fixture()
    by_id = {case.case_id: case for case in phase13p_cases}
    cases: list[PlanningReferenceCase] = []
    for record in manifest["cases"]:
        base = by_id[record["base_case_id"]]
        state = base.semantic_state
        if record.get("remove_inventory"):
            state = state.model_copy(update={"inventory_references": []})
        reasoner = ContextReasoner(
            graph,
            relation_confidence_threshold=(
                base.relation_confidence_threshold
                if base.relation_confidence_threshold is not None
                else 0.7
            ),
        )
        context = reasoner.reason(state, base.temporal_state)
        cases.append(
            PlanningReferenceCase(
                case_id=record["case_id"],
                description=record["description"],
                expected_reference_types=record["expected_reference_types"],
                semantic_state=state,
                temporal_state=TemporalState.from_semantic_state(state),
                context_understanding=context,
                knowledge_graph=graph,
            )
        )
    return cases


def evaluate_cases(
    cases: list[PlanningReferenceCase],
    *,
    engine: PlanningReferenceEngine | None = None,
    dataset_reference: str = "phase13q-reference-fixture-v1",
) -> PlanningReferenceEvaluationReport:
    """Evaluate references without mutating semantic state or graph."""
    evaluator = engine or PlanningReferenceEngine()
    results: list[PlanningReferenceEvaluationResult] = []
    for case in cases:
        references = evaluator.generate(
            case.semantic_state,
            case.temporal_state,
            case.knowledge_graph,
            case.context_understanding,
        )
        actual_types = [reference.reference_type for reference in references]
        expected_types = case.expected_reference_types
        failures: list[str] = []
        if not set(expected_types).issubset(set(actual_types)):
            failures.append(
                "expected reference category not generated"
            )
        uncertainties_preserved = all(
            bool(reference.uncertainties) for reference in references
        )
        if not uncertainties_preserved:
            failures.append("uncertainty was not preserved")
        expired_excluded = not any(
            entity.lifecycle is EntityLifecycle.EXPIRED
            for reference in references
            for entity in reference.supporting_entities
        )
        if not expired_excluded:
            failures.append("expired entity entered a planning reference")
        input_min = _input_min_confidence(case)
        confidence_violations = sum(
            reference.confidence > input_min + 1e-9
            for reference in references
        )
        if confidence_violations:
            failures.append("reference confidence exceeded weakest input")
        leakage = _action_leakage(references)
        if leakage:
            failures.append("forbidden action semantics leaked into output")
        results.append(
            PlanningReferenceEvaluationResult(
                case_id=case.case_id,
                expected_reference_types=expected_types,
                actual_reference_types=actual_types,
                reference_count=len(references),
                confidence_bound_violations=confidence_violations,
                action_leakage_count=leakage,
                uncertainties_preserved=uncertainties_preserved,
                expired_entities_excluded=expired_excluded,
                passed=not failures,
                failure_reason="; ".join(failures),
            )
        )
    return PlanningReferenceEvaluationReport(
        report_id="phase13q-planning-reference-evaluation",
        dataset_reference=dataset_reference,
        results=results,
        metrics=_metrics(results),
    )


def _input_min_confidence(case: PlanningReferenceCase) -> float:
    state = case.semantic_state
    context = case.context_understanding
    values = [state.confidence, context.confidence]
    values.extend(entity.confidence for entity in context.related_entities)
    values.extend(relation.confidence for relation in context.related_relations)
    return min(values, default=0.0)


def _action_leakage(references: list[Any]) -> int:
    forbidden = (
        "click(",
        "move(",
        "attack(",
        "pickup(",
        "use_item(",
        "send_key(",
        "keyboard",
        "mouse",
        "executor",
        "input provider",
    )
    return sum(
        any(
            token in reference.model_dump_json().lower()
            for token in forbidden
        )
        for reference in references
    )


def _metrics(
    results: list[PlanningReferenceEvaluationResult],
) -> PlanningReferenceMetrics:
    if not results:
        return PlanningReferenceMetrics()
    accurate = [result.passed for result in results]
    uncertainty = [
        result.uncertainties_preserved for result in results
    ]
    return PlanningReferenceMetrics(
        denominator_status="SUFFICIENT",
        denominators={
            "reference_accuracy": len(accurate),
            "uncertainty_preservation_rate": len(uncertainty),
        },
        reference_accuracy=round(sum(accurate) / len(accurate), 4),
        uncertainty_preservation_rate=round(
            sum(uncertainty) / len(uncertainty), 4
        ),
        confidence_bound_violation_count=sum(
            result.confidence_bound_violations for result in results
        ),
        action_leakage_count=sum(
            result.action_leakage_count for result in results
        ),
    )
