"""Phase 13-R end-to-end read-only Companion Loop tests."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

from maple_agent.companion_runtime.benchmark import (
    BASE_TIME,
    build_replay_scenarios,
    build_sanitized_graphs,
    build_sanitized_source_provenance,
    evaluate_scenarios,
    run_long_run_smoke,
)
from maple_agent.companion_runtime.coordinator import (
    CompanionRuntimeCoordinator,
)
from maple_agent.companion_runtime.models import CompanionSession
from maple_agent.companion_runtime.renderer import (
    render_snapshot,
    validate_snapshot_schema,
)
from maple_agent.planning_reference.models import PlanningReferenceType


def test_end_to_end_benchmark_passes_all_scenarios():
    report = evaluate_scenarios()

    assert len(report.results) == 10
    assert all(result.passed for result in report.results)
    assert report.metrics.scenario_pass_rate == 1.0
    assert report.metrics.planning_reference_consistency == 1.0
    assert report.metrics.provenance_preservation_rate == 1.0
    assert report.metrics.snapshot_generation_success_rate == 1.0
    assert report.metrics.action_leakage_count == 0
    assert report.metrics.confidence_bound_violations == 0


def test_normal_observation_composes_resolver_state_context_reference_snapshot():
    scenario = next(item for item in build_replay_scenarios() if item.scenario_id == "A")
    resolution_graph, knowledge_graph = build_sanitized_graphs()
    coordinator = CompanionRuntimeCoordinator(
        resolution_graph,
        knowledge_graph,
        source_provenance=build_sanitized_source_provenance(),
    )

    snapshot = coordinator.process_observation(
        scenario.observations[0], now=BASE_TIME
    )

    assert len(coordinator.last_resolutions) == 4
    assert all(resolution.resolved for resolution in coordinator.last_resolutions)
    assert coordinator.last_semantic_state is not None
    assert coordinator.last_context.context_type.value in {
        "QUEST_RELATED_CONTEXT",
        "ITEM_QUEST_CONTEXT",
    }
    assert snapshot.planning_references[0].reference_type is (
        PlanningReferenceType.QUEST_CONTEXT
    )
    assert snapshot.source_provenance.source_type == "COMMUNITY_DATABASE"
    assert snapshot.semantic_state.unresolved_evidence_count == 0
    assert snapshot.semantic_state.conflict_count == 0


def test_unknown_conflict_and_missing_requirement_are_preserved():
    report = evaluate_scenarios()
    results = {result.scenario_id: result for result in report.results}

    assert results["B"].unknown_preserved is True
    assert results["D"].conflict_preserved is True
    assert results["C"].actual_reference_types == [
        PlanningReferenceType.MISSING_REQUIREMENT
    ]


def test_temporal_continuity_visible_lost_expired():
    report = evaluate_scenarios()
    result = next(item for item in report.results if item.scenario_id == "F")

    assert result.temporal_continuity_correct is True
    assert [item.value for item in result.lifecycle_sequence] == [
        "VISIBLE",
        "LOST",
        "EXPIRED",
    ]


def test_multiple_npcs_are_not_collapsed():
    report = evaluate_scenarios()
    result = next(item for item in report.results if item.scenario_id == "I")

    assert result.planning_reference_consistent is True


def test_low_confidence_and_missing_relation_remain_quality_notes():
    report = evaluate_scenarios()
    results = {result.scenario_id: result for result in report.results}

    assert results["E"].passed is True
    assert results["G"].passed is True
    assert results["E"].confidence_bound_violations == 0
    assert results["G"].provenance_preserved is True


def test_session_continuity_uses_one_history():
    scenario = next(item for item in build_replay_scenarios() if item.scenario_id == "F")
    resolution_graph, knowledge_graph = build_sanitized_graphs()
    coordinator = CompanionRuntimeCoordinator(
        resolution_graph,
        knowledge_graph,
        session=CompanionSession(session_id="session-test"),
    )

    for observation, offset in zip(
        scenario.observations, scenario.now_offsets_seconds
    ):
        coordinator.process_observation(
            observation,
            now=BASE_TIME + timedelta(seconds=offset),
        )

    assert coordinator.session.session_id == "session-test"
    assert coordinator.session.snapshot_count == 3
    assert len(coordinator.history.entries) == 3
    assert len(coordinator.session.history_reference_ids) == 6


def test_empty_observation_is_information_gap():
    scenario = next(item for item in build_replay_scenarios() if item.scenario_id == "J")
    resolution_graph, knowledge_graph = build_sanitized_graphs()
    snapshot = CompanionRuntimeCoordinator(
        resolution_graph, knowledge_graph
    ).process_observation(scenario.observations[0], now=BASE_TIME)

    assert snapshot.information_gaps
    assert snapshot.semantic_state.unresolved_evidence_count == 0
    assert snapshot.context_understanding.context_type.value == "UNKNOWN_CONTEXT"


def test_snapshot_schema_and_renderer_have_no_action_semantics():
    scenario = next(item for item in build_replay_scenarios() if item.scenario_id == "A")
    resolution_graph, knowledge_graph = build_sanitized_graphs()
    snapshot = CompanionRuntimeCoordinator(
        resolution_graph, knowledge_graph
    ).process_observation(scenario.observations[0], now=BASE_TIME)
    rendered = render_snapshot(snapshot)

    assert validate_snapshot_schema(snapshot) == []
    for forbidden in (
        "click(",
        "move(",
        "attack(",
        "pickup(",
        "use_item(",
        "send_key(",
        "去",
        "移动到",
        "攻击",
        "点击",
        "使用",
        "执行",
    ):
        assert forbidden not in rendered
    assert "action" not in snapshot.__class__.model_fields
    assert "command" not in snapshot.__class__.model_fields
    assert "executor" not in snapshot.__class__.model_fields
    assert "input" not in snapshot.__class__.model_fields


def test_snapshot_privacy_excludes_raw_evidence_and_private_paths():
    scenario = next(item for item in build_replay_scenarios() if item.scenario_id == "A")
    resolution_graph, knowledge_graph = build_sanitized_graphs()
    coordinator = CompanionRuntimeCoordinator(
        resolution_graph, knowledge_graph
    )
    snapshot = coordinator.process_observation(scenario.observations[0], now=BASE_TIME)
    serialized = snapshot.model_dump_json()

    assert "raw_value" not in serialized
    assert "private" not in serialized.lower()
    assert "screenshot" not in serialized.lower()
    assert "session.json" not in serialized.lower()
    assert "HWND" not in serialized
    assert "PID" not in serialized
    assert "value" not in snapshot.semantic_state.__class__.model_fields


def test_long_run_smoke_records_101_events_without_threshold_claim():
    smoke = run_long_run_smoke(101)

    assert smoke.event_count == 101
    assert smoke.history_size == 101
    assert smoke.exception_count == 0
    assert smoke.deterministic_context_types is True
    assert smoke.average_observation_latency_ms >= 0
    assert smoke.average_snapshot_latency_ms >= 0
    assert smoke.peak_memory_bytes > 0


def test_companion_runtime_dependency_direction_is_one_way():
    source_root = Path("src/maple_agent")
    frozen_packages = (
        "context_reasoning",
        "game_state",
        "hybrid_vision",
        "knowledge_graph",
        "maple_knowledge",
        "planning_reference",
    )

    for package in frozen_packages:
        for source_file in (source_root / package).rglob("*.py"):
            assert "companion_runtime" not in source_file.read_text(
                encoding="utf-8"
            ), source_file
