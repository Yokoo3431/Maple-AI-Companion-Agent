"""Phase 13-P evaluation and sanitized temporal replay tests."""

from __future__ import annotations

import json

from maple_agent.context_reasoning.models import ContextType
from maple_agent.context_reasoning.reasoner import ContextReasoner
from maple_agent.evaluation import (
    evaluate_cases,
    load_benchmark_fixture,
    run_temporal_replay,
    write_temporal_replay_report,
)
from maple_agent.game_state.models import EntityLifecycle
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import RelationType


def _fixture():
    graph, cases = load_benchmark_fixture()
    return graph, cases, ContextReasoner(graph)


def test_benchmark_loading_is_structured_and_sanitized():
    graph, cases, _ = _fixture()

    assert len(cases) == 7
    assert {case.case_id for case in cases} == set("ABCDEFG")
    assert len(graph.maps) == 2
    assert all(not case.semantic_state.evidence for case in cases)
    assert all("screenshot" not in case.model_dump_json() for case in cases)


def test_context_evaluation_passes_all_required_cases():
    graph, cases, reasoner = _fixture()

    report = evaluate_cases(cases, reasoner)

    assert report.sanitized is True
    assert all(result.passed for result in report.results)
    assert report.metrics.context_accuracy == 1.0
    assert report.metrics.denominators["context_accuracy"] == 7


def test_unknown_and_conflict_are_preserved():
    graph, cases, reasoner = _fixture()

    report = evaluate_cases([cases[2], cases[5]], reasoner)

    assert all(result.actual_context is ContextType.UNKNOWN_CONTEXT for result in report.results)
    assert report.metrics.unknown_preservation_rate == 1.0
    assert report.metrics.conflict_preservation_rate == 1.0


def test_expired_is_excluded_and_lost_is_historical():
    graph, cases, reasoner = _fixture()

    report = evaluate_cases([cases[3], cases[4]], reasoner)

    assert report.metrics.expired_exclusion_rate == 1.0
    assert report.metrics.lost_handling_accuracy == 1.0
    assert report.results[0].actual_active is False
    assert report.results[1].actual_active is False


def test_low_confidence_relation_is_not_promoted():
    graph, cases, reasoner = _fixture()

    result = evaluate_cases([cases[6]], reasoner).results[0]

    assert result.passed is True
    assert result.actual_context is ContextType.LOCATION_CONTEXT
    assert result.actual_uncertainty is True


def test_confidence_never_exceeds_weakest_input():
    graph, cases, _ = _fixture()
    relation = next(
        item
        for item in graph.all_relations()
        if item.relation_type is RelationType.REQUIRES
    ).model_copy(update={"confidence": 0.5})
    low_confidence_graph = KnowledgeGraph(
        maps=graph.maps,
        npcs=graph.npcs,
        quests=graph.quests,
        items=graph.items,
        relations=[relation],
    )
    reasoner = ContextReasoner(
        low_confidence_graph,
        relation_confidence_threshold=0.4,
    )
    case = cases[1].model_copy(
        update={"input_confidences": [0.9, 0.8, 0.5]}
    )

    result = evaluate_cases([case], reasoner).results[0]

    assert result.confidence <= 0.5
    assert result.confidence_bound_violations == 0


def test_temporal_replay_visible_lost_expired():
    graph, cases, reasoner = _fixture()
    visible = cases[0].semantic_state
    lost = visible.model_copy(
        update={
            "state_id": "state-replay-lost",
            "observation_id": "observation-replay-lost",
            "location": visible.location.model_copy(
                update={"lifecycle": EntityLifecycle.LOST}
            ),
            "nearby_entities": [
                visible.nearby_entities[0].model_copy(
                    update={"lifecycle": EntityLifecycle.LOST}
                )
            ],
        }
    )
    expired = lost.model_copy(
        update={
            "state_id": "state-replay-expired",
            "observation_id": "observation-replay-expired",
            "location": lost.location.model_copy(
                update={"lifecycle": EntityLifecycle.EXPIRED}
            ),
            "nearby_entities": [
                lost.nearby_entities[0].model_copy(
                    update={"lifecycle": EntityLifecycle.EXPIRED}
                )
            ],
        }
    )

    report = run_temporal_replay(reasoner, [visible, lost, expired])

    assert report.lifecycle_sequence == [
        EntityLifecycle.VISIBLE,
        EntityLifecycle.LOST,
        EntityLifecycle.EXPIRED,
    ]
    assert report.steps[0].context_type is ContextType.QUEST_RELATED_CONTEXT
    assert report.steps[1].historical_reference is True
    assert report.steps[2].active is False


def test_replay_report_is_sanitized(tmp_path):
    graph, cases, reasoner = _fixture()
    report = run_temporal_replay(reasoner, [cases[0].semantic_state])

    output = write_temporal_replay_report(report, tmp_path)
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert output.name == "semantic_context_replay_report.json"
    assert payload["sanitized"] is True
    serialized = json.dumps(payload, ensure_ascii=False)
    for forbidden in ("screenshot", "raw_evidence", "private_path", "keyboard", "mouse"):
        assert forbidden not in serialized.lower()


def test_empty_metrics_do_not_claim_accuracy():
    graph, _, reasoner = _fixture()

    report = evaluate_cases([], reasoner)

    assert report.metrics.denominator_status == "INSUFFICIENT_DATA"
    assert report.metrics.context_accuracy is None
    assert report.metrics.unknown_preservation_rate is None


def test_evaluation_output_has_no_action_semantics():
    graph, cases, reasoner = _fixture()
    result = evaluate_cases([cases[0]], reasoner).results[0]
    serialized = result.model_dump_json().lower()

    for forbidden in ("command", "action", "input provider", "executor", "key", "mouse"):
        assert forbidden not in serialized
