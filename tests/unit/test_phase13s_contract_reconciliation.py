"""Phase 13-S runtime contract and replay/observation boundary tests."""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.companion_runtime.benchmark import (
    BASE_TIME,
    build_replay_scenarios,
    build_sanitized_graphs,
    build_sanitized_runtime_bundle,
    build_sanitized_source_provenance,
)
from maple_agent.companion_runtime.coordinator import (
    CompanionRuntimeCoordinator,
)
from maple_agent.companion_runtime.knowledge_contract import (
    RuntimeKnowledgeBundle,
    audit_graph_contract,
)
from maple_agent.companion_runtime.observation_adapter import (
    ExistingVisionObservationAdapter,
)
from maple_agent.companion_runtime.session_validation import (
    build_pending_real_session_report,
)
from maple_agent.game_state.models import CurrentObservation
from maple_agent.hybrid_vision.models import PerceptionEvidence
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import KnowledgeEntityProvenance
from maple_agent.knowledge_quality.package import KnowledgeDatasetPackage


def test_source_backed_package_builds_one_runtime_bundle_for_both_graph_views():
    package = KnowledgeDatasetPackage.load("knowledge_dataset")
    bundle = RuntimeKnowledgeBundle.from_dataset_package(package)

    assert bundle.audit.valid is True
    assert bundle.audit.denominator_status == "SUFFICIENT"
    assert bundle.audit.canonical_overlap_count == 400
    assert bundle.audit.canonical_mismatch_count == 0
    assert bundle.audit.alias_conflict_count == 0
    assert bundle.audit.profile_mismatch_count == 0
    assert bundle.audit.provenance_mismatch_count == 0
    assert bundle.provenance.game_profile == "maple-cms-classic-community"
    assert bundle.provenance.server_profile == "cn-nostalgic-community"
    assert bundle.provenance.data_version == "mxdc-cn-community-20260814-v1"


def test_graph_identity_mismatch_is_reported_without_repair():
    resolution_graph, relationship_graph = build_sanitized_graphs()
    incomplete_graph = KnowledgeGraph(
        maps=relationship_graph.maps[:-1],
        npcs=relationship_graph.npcs,
        items=relationship_graph.items,
        quests=relationship_graph.quests,
        relations=relationship_graph.all_relations(),
    )

    audit = audit_graph_contract(
        resolution_graph,
        incomplete_graph,
        provenance=build_sanitized_source_provenance(),
        dataset_id="phase13r-fixture-v1",
    )

    assert audit.valid is False
    assert audit.canonical_mismatch_count == 1
    assert audit.missing_left_count == 1
    assert any("no automatic repair" in issue for issue in audit.issues)


def test_profile_mismatch_is_reported():
    resolution_graph, relationship_graph = build_sanitized_graphs()
    changed_map = relationship_graph.maps[0].model_copy(
        update={
            "provenance": KnowledgeEntityProvenance(
                source_id="phase13r-sanitized-community-fixture",
                source_type="COMMUNITY_DATABASE",
                game_profile="other-profile",
                server_profile="fixture",
                data_version="phase13r-fixture-v1",
                snapshot_version="phase13r-fixture-v1",
                content_hash="sha256:phase13r-sanitized-fixture",
            )
        }
    )
    changed_graph = KnowledgeGraph(
        maps=[changed_map, *relationship_graph.maps[1:]],
        npcs=relationship_graph.npcs,
        items=relationship_graph.items,
        quests=relationship_graph.quests,
        relations=relationship_graph.all_relations(),
    )

    audit = audit_graph_contract(
        resolution_graph,
        changed_graph,
        provenance=build_sanitized_source_provenance(),
        dataset_id="phase13r-fixture-v1",
    )

    assert audit.valid is False
    assert audit.profile_mismatch_count == 1


def test_missing_metadata_is_unknown_not_guessed():
    resolution_graph, relationship_graph = build_sanitized_graphs()
    coordinator = CompanionRuntimeCoordinator(
        resolution_graph,
        relationship_graph,
    )
    snapshot = coordinator.process_observation(
        build_replay_scenarios()[0].observations[0],
        now=BASE_TIME,
    )

    assert snapshot.source_provenance.game_profile == "UNKNOWN"
    assert snapshot.source_provenance.server_profile == "UNKNOWN"
    assert snapshot.source_provenance.data_version == "UNKNOWN"
    assert "UNBOUND" in " ".join(snapshot.data_quality_notes)


def test_existing_vision_observation_adapter_uses_same_coordinator():
    bundle = build_sanitized_runtime_bundle()
    source = build_replay_scenarios()[0].observations[0]
    adapted = ExistingVisionObservationAdapter.from_current_observation(source)
    coordinator = CompanionRuntimeCoordinator(knowledge_bundle=bundle)

    snapshot = coordinator.process_observation(adapted, now=BASE_TIME)

    assert isinstance(adapted, CurrentObservation)
    assert snapshot.observation_id == source.observation_id
    assert snapshot.source_provenance.data_version == "phase13r-fixture-v1"


def test_evidence_adapter_enters_the_same_read_only_observation_contract():
    evidence = PerceptionEvidence(
        evidence_id="adapter-map",
        evidence_type="map",
        value="Henesys Reference",
        confidence=0.9,
        source="EXISTING_VISION_RESULT",
    )
    observation = ExistingVisionObservationAdapter.from_evidence(
        observation_id="adapter-observation",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        evidence=[evidence],
    )
    coordinator = CompanionRuntimeCoordinator(
        knowledge_bundle=build_sanitized_runtime_bundle()
    )
    snapshot = coordinator.process_observation(observation, now=BASE_TIME)

    assert snapshot.observation_id == "adapter-observation"
    assert snapshot.semantic_state.location is not None
    assert snapshot.semantic_state.location.canonical_id == "map_m1"


def test_pending_real_session_report_is_sanitized_and_not_validated():
    report = build_pending_real_session_report()

    assert report.status == "REAL_SESSION_PENDING"
    assert report.observation_count == 0
    assert report.snapshot_count == 0
    assert report.provenance_profile["game_profile"] == "UNKNOWN"
    assert report.sanitized is True
    serialized = report.model_dump_json()
    assert "screenshot" not in serialized.lower()
    assert "ocr" not in serialized.lower()
    assert "PID" not in serialized
    assert "HWND" not in serialized

