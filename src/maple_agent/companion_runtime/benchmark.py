"""Sanitized end-to-end replay scenarios and quality metrics."""

from __future__ import annotations

import time
import tracemalloc
from datetime import UTC, datetime, timedelta

from pydantic import BaseModel, Field

from maple_agent.companion_runtime.coordinator import CompanionRuntimeCoordinator
from maple_agent.companion_runtime.knowledge_contract import (
    RuntimeKnowledgeBundle,
)
from maple_agent.companion_runtime.models import (
    CompanionSnapshot,
    FailureCategory,
    SourceProvenanceSummary,
)
from maple_agent.companion_runtime.renderer import (
    render_snapshot,
    validate_snapshot_schema,
)
from maple_agent.context_reasoning.models import ContextType
from maple_agent.game_state.models import CurrentObservation, EntityLifecycle
from maple_agent.hybrid_vision.models import PerceptionEvidence
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import (
    ItemNode,
    KnowledgeEntityProvenance,
    MapNode,
    NPCNode,
    QuestNode,
    Relation,
    RelationType,
)
from maple_agent.maple_knowledge.knowledge_base import (
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
)
from maple_agent.maple_knowledge.models import (
    KnowledgeEntityProvenance as LegacyProvenance,
)
from maple_agent.maple_knowledge.models import (
    KnowledgeRelation,
    KnowledgeRelationType,
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)
from maple_agent.planning_reference.models import PlanningReferenceType

BASE_TIME = datetime(2026, 1, 1, tzinfo=UTC)


class ReplayScenario(BaseModel):
    """Sanitized scenario definition; no private runtime state."""

    scenario_id: str
    description: str
    observations: list[CurrentObservation]
    now_offsets_seconds: list[int]
    expected_reference_types: list[PlanningReferenceType]
    graph_variant: str = "standard"
    expects_unknown: bool = False
    expects_conflict: bool = False
    expects_temporal_sequence: bool = False
    expects_multiple_npcs: bool = False
    expected_source_type: str = "COMMUNITY_DATABASE"


class CompanionLoopEvaluationResult(BaseModel):
    """Auditable result for one end-to-end scenario."""

    scenario_id: str
    passed: bool
    snapshot_count: int = Field(ge=0)
    expected_reference_types: list[PlanningReferenceType]
    actual_reference_types: list[PlanningReferenceType]
    expects_unknown: bool = False
    expects_conflict: bool = False
    expects_temporal_sequence: bool = False
    lifecycle_sequence: list[EntityLifecycle] = Field(default_factory=list)
    input_evidence_preserved: bool
    unknown_preserved: bool
    conflict_preserved: bool
    temporal_continuity_correct: bool
    planning_reference_consistent: bool
    provenance_preserved: bool
    confidence_bound_violations: int = Field(default=0, ge=0)
    action_leakage_count: int = Field(default=0, ge=0)
    snapshot_generation_success: bool
    failure_categories: list[FailureCategory] = Field(default_factory=list)
    failure_reason: str = ""


class CompanionLoopEvaluationMetrics(BaseModel):
    """Metrics with explicit denominators."""

    denominator_status: str = "INSUFFICIENT_DATA"
    denominators: dict[str, int] = Field(default_factory=dict)
    scenario_pass_rate: float | None = Field(default=None, ge=0, le=1)
    unknown_preservation_rate: float | None = Field(default=None, ge=0, le=1)
    conflict_preservation_rate: float | None = Field(default=None, ge=0, le=1)
    temporal_continuity_accuracy: float | None = Field(default=None, ge=0, le=1)
    planning_reference_consistency: float | None = Field(
        default=None, ge=0, le=1
    )
    provenance_preservation_rate: float | None = Field(
        default=None, ge=0, le=1
    )
    confidence_bound_violations: int = Field(default=0, ge=0)
    action_leakage_count: int = Field(default=0, ge=0)
    snapshot_generation_success_rate: float | None = Field(
        default=None, ge=0, le=1
    )


class LongRunSmokeResult(BaseModel):
    """Observed 100+ event replay baseline, without a pass threshold."""

    event_count: int = Field(ge=0)
    history_size: int = Field(ge=0)
    exception_count: int = Field(default=0, ge=0)
    deterministic_context_types: bool
    average_observation_latency_ms: float
    max_observation_latency_ms: float
    average_snapshot_latency_ms: float
    peak_memory_bytes: int = Field(ge=0)
    snapshot_count: int = Field(default=0, ge=0)
    timestamps_monotonic: bool = True
    history_append_only: bool = True
    duplicate_history_entries: int = Field(default=0, ge=0)
    unknown_count: int = Field(default=0, ge=0)
    unresolved_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    average_observation_interval_ms: float | None = Field(default=None, ge=0)


class CompanionLoopEvaluationReport(BaseModel):
    """Sanitized Phase 13-R benchmark report."""

    report_id: str
    dataset_reference: str
    results: list[CompanionLoopEvaluationResult] = Field(default_factory=list)
    metrics: CompanionLoopEvaluationMetrics
    long_run_smoke: LongRunSmokeResult
    sanitized: bool = True


def build_sanitized_graphs(
    variant: str = "standard",
) -> tuple[MapleKnowledgeGraph, KnowledgeGraph]:
    """Build paired legacy/new graph interfaces from one sanitized fixture."""
    legacy_provenance = LegacyProvenance(
        source_id="phase13r-sanitized-community-fixture",
        source_type="COMMUNITY_DATABASE",
        game_profile="maple-v113-fixture",
        server_profile="fixture",
        data_version="phase13r-fixture-v1",
        snapshot_version="phase13r-fixture-v1",
        content_hash="sha256:phase13r-sanitized-fixture",
    )
    modern_provenance = KnowledgeEntityProvenance(
        source_id="phase13r-sanitized-community-fixture",
        source_type="COMMUNITY_DATABASE",
        game_profile="maple-v113-fixture",
        server_profile="fixture",
        data_version="phase13r-fixture-v1",
        snapshot_version="phase13r-fixture-v1",
        content_hash="sha256:phase13r-sanitized-fixture",
    )
    entity_specs = [
        ("map_m1", MapleKnowledgeType.MAP, "Henesys Reference", 0.95),
        ("map_m2", MapleKnowledgeType.MAP, "Perion Reference", 0.9),
        ("npc_n1", MapleKnowledgeType.NPC, "Henesys Instructor", 0.9),
        ("npc_n2", MapleKnowledgeType.NPC, "Henesys Guide", 0.88),
        ("npc_n3", MapleKnowledgeType.NPC, "Henesys Resident", 0.86),
        ("quest_q1", MapleKnowledgeType.QUEST, "Reference Quest", 0.85),
        ("item_i1", MapleKnowledgeType.ITEM, "Reference Item", 0.85),
    ]
    base = MapleKnowledgeBase()
    for knowledge_id, entity_type, name, confidence in entity_specs:
        base.add_entity(
            MapleKnowledgeEntity(
                knowledge_id=knowledge_id,
                knowledge_type=entity_type,
                name=name,
                aliases=[],
                source="phase13r-sanitized-replay",
                confidence=confidence,
                version="phase13r-fixture-v1",
                provenance=legacy_provenance,
            )
        )
    legacy_relations = [
        ("map_m1", "npc_n1", KnowledgeRelationType.CONTAINS, 0.9),
        ("map_m1", "npc_n2", KnowledgeRelationType.CONTAINS, 0.88),
        ("map_m1", "npc_n3", KnowledgeRelationType.CONTAINS, 0.86),
        ("npc_n1", "quest_q1", KnowledgeRelationType.RELATED_TO, 0.85),
        ("quest_q1", "item_i1", KnowledgeRelationType.REQUIRES, 0.8),
    ]
    for index, (source, target, relation_type, confidence) in enumerate(
        legacy_relations
    ):
        base.add_relation(
            KnowledgeRelation(
                relation_id=f"phase13r-relation-{index}",
                source_id=source,
                target_id=target,
                relation_type=relation_type,
                confidence=confidence,
            )
        )
    modern_maps = [
        MapNode(
            map_id="map_m1",
            name="Henesys Reference",
            confidence=0.95,
            provenance=modern_provenance,
        ),
        MapNode(
            map_id="map_m2",
            name="Perion Reference",
            confidence=0.9,
            provenance=modern_provenance,
        ),
    ]
    modern_npcs = [
        NPCNode(
            npc_id=identifier,
            name=name,
            confidence=confidence,
            provenance=modern_provenance,
        )
        for identifier, name, confidence in [
            ("npc_n1", "Henesys Instructor", 0.9),
            ("npc_n2", "Henesys Guide", 0.88),
            ("npc_n3", "Henesys Resident", 0.86),
        ]
    ]
    modern_quests = [
        QuestNode(
            quest_id="quest_q1",
            name="Reference Quest",
            confidence=0.85,
            provenance=modern_provenance,
        )
    ]
    modern_items = [
        ItemNode(
            item_id="item_i1",
            name="Reference Item",
            confidence=0.85,
            provenance=modern_provenance,
        )
    ]
    relation_confidence = 0.5 if variant == "low_confidence" else 0.9
    relations = [
        Relation(
            source="map",
            source_id="map_m1",
            target="npc",
            target_id="npc_n1",
            relation_type=RelationType.CONTAINS,
            confidence=relation_confidence,
            provenance=modern_provenance,
        ),
    ]
    if variant != "missing_relation":
        relations.extend(
            [
                Relation(
                    source="map",
                    source_id="map_m1",
                    target="npc",
                    target_id="npc_n2",
                    relation_type=RelationType.CONTAINS,
                    confidence=relation_confidence,
                    provenance=modern_provenance,
                ),
                Relation(
                    source="map",
                    source_id="map_m1",
                    target="npc",
                    target_id="npc_n3",
                    relation_type=RelationType.CONTAINS,
                    confidence=relation_confidence,
                    provenance=modern_provenance,
                ),
                Relation(
                    source="npc",
                    source_id="npc_n1",
                    target="quest",
                    target_id="quest_q1",
                    relation_type=RelationType.GIVES,
                    confidence=relation_confidence,
                    provenance=modern_provenance,
                ),
                Relation(
                    source="quest",
                    source_id="quest_q1",
                    target="item",
                    target_id="item_i1",
                    relation_type=RelationType.REQUIRES,
                    confidence=relation_confidence,
                    provenance=modern_provenance,
                ),
            ]
        )
    modern_graph = KnowledgeGraph(
        maps=modern_maps,
        npcs=modern_npcs,
        quests=modern_quests,
        items=modern_items,
        relations=relations,
    )
    return MapleKnowledgeGraph(base), modern_graph


def build_sanitized_source_provenance(
    source_type: str = "COMMUNITY_DATABASE",
) -> SourceProvenanceSummary:
    """Fixture-only metadata; never used as a production default."""
    return SourceProvenanceSummary(
        source_id="phase13r-sanitized-community-fixture",
        source_type=source_type,
        game_profile="maple-v113-fixture",
        server_profile="fixture",
        data_version="phase13r-fixture-v1",
        dataset_reference="phase13p-phase13q-sanitized-fixtures",
        source_reference="fixture://phase13r",
        content_hash="sha256:phase13r-sanitized-fixture",
    )


def build_sanitized_runtime_bundle(
    variant: str = "standard",
) -> RuntimeKnowledgeBundle:
    resolution_graph, relationship_graph = build_sanitized_graphs(variant)
    return RuntimeKnowledgeBundle.from_graphs(
        resolution_graph,
        relationship_graph,
        provenance=build_sanitized_source_provenance(),
        dataset_id="phase13r-fixture-v1",
    )


def build_replay_scenarios() -> list[ReplayScenario]:
    """Return ten deterministic, sanitized end-to-end scenarios."""
    def evidence(
        evidence_id: str,
        evidence_type: str,
        value: str,
        confidence: float = 0.9,
    ) -> PerceptionEvidence:
        return PerceptionEvidence(
            evidence_id=evidence_id,
            evidence_type=evidence_type,
            value=value,
            confidence=confidence,
            source="SANITIZED_REPLAY",
        )

    def observation(
        observation_id: str,
        values: list[tuple[str, str, str, float]],
        offset: int = 0,
    ) -> CurrentObservation:
        return CurrentObservation(
            observation_id=observation_id,
            timestamp=BASE_TIME + timedelta(seconds=offset),
            source="SANITIZED_REPLAY",
            evidence=[evidence(*value) for value in values],
        )

    normal = [
        ("map", "map", "Henesys Reference", 0.9),
        ("npc", "npc", "Henesys Instructor", 0.9),
        ("quest", "quest", "Reference Quest", 0.85),
        ("item", "item", "Reference Item", 0.85),
    ]
    map_npc = normal[:2]
    quest_without_item = normal[:3]
    return [
        ReplayScenario(
            scenario_id="A",
            description="Normal map/NPC/quest context",
            observations=[observation("obs-a", normal)],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.QUEST_CONTEXT],
        ),
        ReplayScenario(
            scenario_id="B",
            description="Unknown NPC remains unresolved",
            observations=[
                observation(
                    "obs-b",
                    [
                        normal[0],
                        ("unknown-npc", "npc", "Unknown Character", 0.8),
                    ],
                )
            ],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.KNOWN_LOCATION],
            expects_unknown=True,
        ),
        ReplayScenario(
            scenario_id="C",
            description="Quest item ownership is not confirmed",
            observations=[observation("obs-c", quest_without_item)],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.MISSING_REQUIREMENT],
        ),
        ReplayScenario(
            scenario_id="D",
            description="Competing location candidates remain a conflict",
            observations=[
                observation(
                    "obs-d",
                    [
                        normal[0],
                        ("map-2", "map", "Perion Reference", 0.9),
                    ],
                )
            ],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.CONFLICT_NOTICE],
            expects_conflict=True,
        ),
        ReplayScenario(
            scenario_id="E",
            description="Low-confidence relation is not promoted",
            observations=[observation("obs-e", map_npc)],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.KNOWN_LOCATION],
            graph_variant="low_confidence",
        ),
        ReplayScenario(
            scenario_id="F",
            description="Temporal visible/lost/expired continuity",
            observations=[
                observation("obs-f-visible", normal, 0),
                observation("obs-f-lost", [], 40),
                observation("obs-f-expired", [], 130),
            ],
            now_offsets_seconds=[0, 40, 130],
            expected_reference_types=[PlanningReferenceType.INFORMATION_GAP],
            expects_temporal_sequence=True,
        ),
        ReplayScenario(
            scenario_id="G",
            description="Knowledge relation is absent from bounded graph",
            observations=[observation("obs-g", normal)],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.KNOWN_LOCATION],
            graph_variant="missing_relation",
        ),
        ReplayScenario(
            scenario_id="H",
            description="Community provenance warning remains visible",
            observations=[observation("obs-h", [normal[0]])],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.KNOWN_LOCATION],
        ),
        ReplayScenario(
            scenario_id="I",
            description="Multiple legitimate nearby NPCs remain visible",
            observations=[
                observation(
                    "obs-i",
                    normal
                    + [("npc-2", "npc", "Henesys Guide", 0.88)],
                )
            ],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.QUEST_CONTEXT],
            expects_multiple_npcs=True,
        ),
        ReplayScenario(
            scenario_id="J",
            description="Empty observation produces insufficient evidence",
            observations=[observation("obs-j", [])],
            now_offsets_seconds=[0],
            expected_reference_types=[PlanningReferenceType.INFORMATION_GAP],
        ),
    ]


def evaluate_scenarios(
    scenarios: list[ReplayScenario] | None = None,
) -> CompanionLoopEvaluationReport:
    scenarios = scenarios or build_replay_scenarios()
    results: list[CompanionLoopEvaluationResult] = []
    for scenario in scenarios:
        bundle = build_sanitized_runtime_bundle(scenario.graph_variant)
        coordinator = CompanionRuntimeCoordinator(
            knowledge_bundle=bundle,
        )
        snapshots: list[CompanionSnapshot] = []
        input_preserved = True
        failure_categories: list[FailureCategory] = []
        for observation, offset in zip(
            scenario.observations, scenario.now_offsets_seconds
        ):
            try:
                snapshot = coordinator.process_observation(
                    observation,
                    now=BASE_TIME + timedelta(seconds=offset),
                )
                snapshots.append(snapshot)
                input_preserved &= (
                    [item.evidence_id for item in observation.evidence]
                    == [
                        item.evidence_id
                        for item in coordinator.last_semantic_state.evidence
                        if item.evidence_id in {
                            evidence.evidence_id
                            for evidence in observation.evidence
                        }
                    ]
                )
            except Exception:
                failure_categories.append(FailureCategory.UNKNOWN)
        actual_types = [
            reference.reference_type
            for snapshot in snapshots
            for reference in snapshot.planning_references
        ]
        expected_consistent = set(scenario.expected_reference_types).issubset(
            set(actual_types)
        )
        unknown_preserved = not scenario.expects_unknown or any(
            snapshot.semantic_state.unknown_count > 0
            or snapshot.semantic_state.unresolved_evidence_count > 0
            for snapshot in snapshots
        )
        conflict_preserved = not scenario.expects_conflict or any(
            snapshot.semantic_state.conflict_count > 0
            or any(
                reference.reference_type
                is PlanningReferenceType.CONFLICT_NOTICE
                for reference in snapshot.planning_references
            )
            for snapshot in snapshots
        )
        lifecycle_sequence = [
            snapshot.temporal_summary.lifecycle_by_entity.get(
                "map_m1", EntityLifecycle.UNKNOWN
            )
            for snapshot in snapshots
        ]
        temporal_correct = not scenario.expects_temporal_sequence or (
            lifecycle_sequence == [
                EntityLifecycle.VISIBLE,
                EntityLifecycle.LOST,
                EntityLifecycle.EXPIRED,
            ]
        )
        multiple_npcs = not scenario.expects_multiple_npcs or (
            len(snapshots[-1].semantic_state.nearby_entities) >= 2
            if snapshots
            else False
        )
        provenance = all(
            snapshot.source_provenance.source_type
            == scenario.expected_source_type
            for snapshot in snapshots
        )
        confidence_violations = sum(
            int(
                snapshot.confidence
                > min(
                    snapshot.semantic_state.confidence,
                    snapshot.context_understanding.confidence,
                )
                + 1e-9
            )
            for snapshot in snapshots
        )
        leakage = sum(
            len(validate_snapshot_schema(snapshot))
            + _text_leakage(render_snapshot(snapshot))
            for snapshot in snapshots
        )
        failures = list(failure_categories)
        if not input_preserved:
            failures.append(FailureCategory.RESOLUTION_FAILURE)
        if not expected_consistent or not multiple_npcs:
            failures.append(FailureCategory.REFERENCE_FAILURE)
        if not unknown_preserved:
            failures.append(FailureCategory.INSUFFICIENT_EVIDENCE)
        if not conflict_preserved:
            failures.append(FailureCategory.CONTEXT_FAILURE)
        if not temporal_correct:
            failures.append(FailureCategory.TEMPORAL_CONTINUITY_FAILURE)
        if not provenance:
            failures.append(FailureCategory.PROVENANCE_MISSING)
        if confidence_violations:
            failures.append(FailureCategory.CONFIDENCE_VIOLATION)
        if leakage:
            failures.append(FailureCategory.ACTION_SEMANTIC_LEAKAGE)
        results.append(
            CompanionLoopEvaluationResult(
                scenario_id=scenario.scenario_id,
                passed=not failures and bool(snapshots),
                snapshot_count=len(snapshots),
                expected_reference_types=scenario.expected_reference_types,
                actual_reference_types=actual_types,
                expects_unknown=scenario.expects_unknown,
                expects_conflict=scenario.expects_conflict,
                expects_temporal_sequence=scenario.expects_temporal_sequence,
                lifecycle_sequence=lifecycle_sequence,
                input_evidence_preserved=input_preserved,
                unknown_preserved=unknown_preserved,
                conflict_preserved=conflict_preserved,
                temporal_continuity_correct=temporal_correct,
                planning_reference_consistent=expected_consistent and multiple_npcs,
                provenance_preserved=provenance,
                confidence_bound_violations=confidence_violations,
                action_leakage_count=leakage,
                snapshot_generation_success=bool(snapshots),
                failure_categories=list(dict.fromkeys(failures)),
                failure_reason="; ".join(category.value for category in failures),
            )
        )
    smoke = run_long_run_smoke()
    return CompanionLoopEvaluationReport(
        report_id="phase13r-companion-loop-evaluation",
        dataset_reference="phase13p-phase13q-sanitized-fixtures",
        results=results,
        metrics=_metrics(results),
        long_run_smoke=smoke,
    )


def run_long_run_smoke(event_count: int = 101) -> LongRunSmokeResult:
    coordinator = CompanionRuntimeCoordinator(
        knowledge_bundle=build_sanitized_runtime_bundle()
    )
    latencies: list[float] = []
    snapshot_latencies: list[float] = []
    exceptions = 0
    context_types: list[ContextType] = []
    snapshot_timestamps: list[datetime] = []
    snapshot_count = 0
    tracemalloc.start()
    for index in range(event_count):
        observation = CurrentObservation(
            observation_id=f"long-run-{index}",
            timestamp=BASE_TIME + timedelta(seconds=index),
            source="SANITIZED_REPLAY",
            evidence=[
                PerceptionEvidence(
                    evidence_id=f"long-run-evidence-{index}",
                    evidence_type="map",
                    value="Henesys Reference",
                    confidence=0.9,
                    source="SANITIZED_REPLAY",
                )
            ],
        )
        started = time.perf_counter()
        try:
            snapshot = coordinator.process_observation(
                observation,
                now=BASE_TIME + timedelta(seconds=index),
            )
            context_types.append(snapshot.context_understanding.context_type)
            snapshot_timestamps.append(snapshot.timestamp)
            snapshot_count += 1
            snapshot_latencies.append(
                getattr(coordinator, "last_snapshot_latency_ms", 0.0)
            )
        except Exception:
            exceptions += 1
        latencies.append((time.perf_counter() - started) * 1000)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    history_ids = [entry.observation_id for entry in coordinator.history.entries]
    duplicate_history_entries = len(history_ids) - len(set(history_ids))
    timestamp_monotonic = all(
        left <= right
        for left, right in zip(snapshot_timestamps, snapshot_timestamps[1:])
    )
    final_snapshot = coordinator.session.current_snapshot
    average_interval = (
        round(
            sum(
                (right - left).total_seconds() * 1000
                for left, right in zip(
                    snapshot_timestamps, snapshot_timestamps[1:]
                )
            )
            / (len(snapshot_timestamps) - 1),
            4,
        )
        if len(snapshot_timestamps) > 1
        else None
    )
    return LongRunSmokeResult(
        event_count=event_count,
        history_size=len(coordinator.history.entries),
        exception_count=exceptions,
        deterministic_context_types=len(set(context_types)) <= 1,
        average_observation_latency_ms=round(sum(latencies) / len(latencies), 4),
        max_observation_latency_ms=round(max(latencies), 4),
        average_snapshot_latency_ms=round(
            sum(snapshot_latencies) / len(snapshot_latencies), 4
        ),
        peak_memory_bytes=peak,
        snapshot_count=snapshot_count,
        timestamps_monotonic=timestamp_monotonic,
        history_append_only=duplicate_history_entries == 0,
        duplicate_history_entries=duplicate_history_entries,
        unknown_count=(
            final_snapshot.semantic_state.unknown_count
            if final_snapshot is not None
            else 0
        ),
        unresolved_count=(
            final_snapshot.semantic_state.unresolved_evidence_count
            if final_snapshot is not None
            else 0
        ),
        stale_count=(
            final_snapshot.semantic_state.stale_count
            if final_snapshot is not None
            else 0
        ),
        average_observation_interval_ms=average_interval,
    )


def _text_leakage(text: str) -> int:
    forbidden = (
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
    )
    return sum(token in text for token in forbidden)


def _metrics(
    results: list[CompanionLoopEvaluationResult],
) -> CompanionLoopEvaluationMetrics:
    if not results:
        return CompanionLoopEvaluationMetrics()

    def rate(values: list[bool]) -> float | None:
        return round(sum(values) / len(values), 4) if values else None

    unknown = [
        result.unknown_preserved
        for result in results
        if result.expects_unknown
    ]
    conflict = [
        result.conflict_preserved
        for result in results
        if result.expects_conflict
    ]
    temporal = [
        result.temporal_continuity_correct
        for result in results
        if result.expects_temporal_sequence
    ]
    planning = [result.planning_reference_consistent for result in results]
    provenance = [result.provenance_preserved for result in results]
    generation = [result.snapshot_generation_success for result in results]
    return CompanionLoopEvaluationMetrics(
        denominator_status="SUFFICIENT",
        denominators={
            "scenario_pass_rate": len(results),
            "unknown_preservation_rate": len(unknown),
            "conflict_preservation_rate": len(conflict),
            "temporal_continuity_accuracy": len(temporal),
            "planning_reference_consistency": len(planning),
            "provenance_preservation_rate": len(provenance),
            "snapshot_generation_success_rate": len(generation),
        },
        scenario_pass_rate=rate([result.passed for result in results]),
        unknown_preservation_rate=rate(unknown),
        conflict_preservation_rate=rate(conflict),
        temporal_continuity_accuracy=rate(temporal),
        planning_reference_consistency=rate(planning),
        provenance_preservation_rate=rate(provenance),
        confidence_bound_violations=sum(
            result.confidence_bound_violations for result in results
        ),
        action_leakage_count=sum(
            result.action_leakage_count for result in results
        ),
        snapshot_generation_success_rate=rate(generation),
    )
