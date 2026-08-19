"""Phase 13-Q read-only planning reference tests."""

from __future__ import annotations

import json

from maple_agent.planning_reference import (
    PlanningReferenceEngine,
    evaluate_cases,
    load_benchmark_cases,
)
from maple_agent.planning_reference.models import PlanningReferenceType


def _cases():
    return load_benchmark_cases()


def test_benchmark_loading_is_sanitized_and_structured():
    cases = _cases()

    assert {case.case_id for case in cases} == {"A", "B", "C", "D", "F", "G"}
    assert all(not case.semantic_state.evidence for case in cases)
    assert all("screenshot" not in case.model_dump_json().lower() for case in cases)


def test_reference_benchmark_passes_all_required_categories():
    report = evaluate_cases(_cases())

    assert report.sanitized is True
    assert all(result.passed for result in report.results)
    assert report.metrics.reference_accuracy == 1.0
    assert report.metrics.uncertainty_preservation_rate == 1.0
    assert report.metrics.denominator_status == "SUFFICIENT"


def test_quest_context_reference_is_information_only():
    case = _cases()[0]
    reference = PlanningReferenceEngine().generate(
        case.semantic_state,
        case.temporal_state,
        case.knowledge_graph,
        case.context_understanding,
    )[0]

    assert reference.reference_type is PlanningReferenceType.QUEST_CONTEXT
    assert reference.supporting_relations
    assert reference.uncertainties
    assert reference.limitations
    assert "行为" in "".join(reference.limitations)


def test_missing_requirement_says_not_confirmed_not_missing():
    case = next(case for case in _cases() if case.case_id == "B")
    reference = PlanningReferenceEngine().generate(
        case.semantic_state,
        case.temporal_state,
        case.knowledge_graph,
        case.context_understanding,
    )[0]

    assert reference.reference_type is PlanningReferenceType.MISSING_REQUIREMENT
    assert "未确认拥有" in reference.description
    assert "缺少" not in reference.description
    assert "未确认拥有" in "".join(reference.uncertainties)


def test_unknown_and_conflict_are_not_resolved_into_facts():
    cases = _cases()
    report = evaluate_cases(
        [
            next(case for case in cases if case.case_id == "C"),
            next(case for case in cases if case.case_id == "F"),
        ]
    )

    assert report.results[0].actual_reference_types == [
        PlanningReferenceType.INFORMATION_GAP
    ]
    assert report.results[1].actual_reference_types == [
        PlanningReferenceType.CONFLICT_NOTICE
    ]


def test_expired_entity_is_excluded_from_supporting_entities():
    case = next(case for case in _cases() if case.case_id == "D")
    reference = PlanningReferenceEngine().generate(
        case.semantic_state,
        case.temporal_state,
        case.knowledge_graph,
        case.context_understanding,
    )[0]

    assert reference.reference_type is PlanningReferenceType.INFORMATION_GAP
    assert all(
        entity.lifecycle.value != "EXPIRED"
        for entity in reference.supporting_entities
    )


def test_low_confidence_is_propagated_without_increasing_confidence():
    case = next(case for case in _cases() if case.case_id == "A")
    context = case.context_understanding.model_copy(
        update={
            "confidence": 0.5,
            "related_relations": [
                case.context_understanding.related_relations[0].model_copy(
                    update={"confidence": 0.5}
                )
            ],
        }
    )
    reference = PlanningReferenceEngine().generate(
        case.semantic_state,
        case.temporal_state,
        case.knowledge_graph,
        context,
    )[0]

    assert reference.confidence <= 0.5
    assert reference.uncertainties


def test_empty_denominator_is_insufficient_data():
    report = evaluate_cases([])

    assert report.metrics.denominator_status == "INSUFFICIENT_DATA"
    assert report.metrics.reference_accuracy is None


def test_no_action_leakage():
    report = evaluate_cases(_cases())
    serialized = json.dumps(report.model_dump(mode="json"), ensure_ascii=False).lower()

    for forbidden in (
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
    ):
        assert forbidden not in serialized
    assert report.metrics.action_leakage_count == 0
