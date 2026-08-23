"""Composition-only coordinator for the read-only Companion Loop."""

from __future__ import annotations

import time
from datetime import UTC, datetime

from maple_agent.companion_runtime.models import (
    CompanionEntitySummary,
    CompanionSession,
    CompanionSnapshot,
    SemanticStateSummary,
    SourceProvenanceSummary,
    TemporalSummary,
)
from maple_agent.companion_runtime.session import CompanionSessionStore
from maple_agent.context_reasoning.models import (
    ContextUnderstanding,
    TemporalState,
)
from maple_agent.context_reasoning.reasoner import ContextReasoner
from maple_agent.game_state.models import CurrentObservation, SemanticGameState
from maple_agent.game_state.temporal import ObservationHistory, StateReducer
from maple_agent.hybrid_vision.knowledge_resolution import EvidenceResolver
from maple_agent.hybrid_vision.models import EvidenceResolution
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import KnowledgeEntityProvenance
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.planning_reference.models import PlanningReferenceType
from maple_agent.planning_reference.reference import PlanningReferenceEngine


class CompanionRuntimeCoordinator:
    """Connect existing components without reproducing their internal rules."""

    def __init__(
        self,
        resolution_graph: MapleKnowledgeGraph,
        knowledge_graph: KnowledgeGraph,
        *,
        evidence_resolver: EvidenceResolver | None = None,
        context_reasoner: ContextReasoner | None = None,
        planning_reference_engine: PlanningReferenceEngine | None = None,
        session: CompanionSession | None = None,
        source_provenance: SourceProvenanceSummary | None = None,
        stale_after_seconds: float = 30.0,
        expiry_after_seconds: float = 120.0,
        relation_confidence_threshold: float = 0.7,
    ) -> None:
        self.resolution_graph = resolution_graph
        self.knowledge_graph = knowledge_graph
        self.evidence_resolver = evidence_resolver or EvidenceResolver()
        self.reducer = StateReducer(
            resolution_graph,
            evidence_resolver=self.evidence_resolver,
            stale_after_seconds=stale_after_seconds,
            expiry_after_seconds=expiry_after_seconds,
        )
        self.context_reasoner = context_reasoner or ContextReasoner(
            knowledge_graph,
            relation_confidence_threshold=relation_confidence_threshold,
        )
        self.planning_reference_engine = (
            planning_reference_engine or PlanningReferenceEngine()
        )
        self.history = ObservationHistory()
        self.session_store = CompanionSessionStore(session)
        self.source_provenance = source_provenance or SourceProvenanceSummary(
            source_id="phase13r-sanitized-community-fixture",
            source_type="COMMUNITY_DATABASE",
            game_profile="maple-v113",
            server_profile="cn-nostalgic-community",
            data_version="phase13r-fixture-v1",
            dataset_reference="phase13p-phase13q-sanitized-fixtures",
        )
        self.last_resolutions: list[EvidenceResolution] = []
        self.last_semantic_state: SemanticGameState | None = None
        self.last_temporal_state: TemporalState | None = None
        self.last_context = None
        self.last_planning_references = []
        self.last_observation_latency_ms = 0.0
        self.last_snapshot_latency_ms = 0.0

    @property
    def session(self) -> CompanionSession:
        return self.session_store.session

    def process_observation(
        self,
        observation: CurrentObservation,
        *,
        now: datetime | None = None,
    ) -> CompanionSnapshot:
        """Process one existing observation through every approved layer."""
        started = time.perf_counter()
        self.last_resolutions = [
            self.evidence_resolver.resolve(evidence, self.resolution_graph)
            for evidence in observation.evidence
        ]
        self.history.add_observation(
            observation,
            self.last_resolutions,
            source=observation.source or self.source_provenance.source_type,
        )
        self.reducer.now = now or datetime.now(UTC)
        state = self.reducer.reduce(self.history)
        temporal = TemporalState.from_semantic_state(state)
        context = self.context_reasoner.reason(state, temporal)
        references = self.planning_reference_engine.generate(
            state,
            temporal,
            self.knowledge_graph,
            context,
        )
        snapshot_started = time.perf_counter()
        snapshot = self._build_snapshot(state, temporal, context, references)
        self.last_snapshot_latency_ms = (
            time.perf_counter() - snapshot_started
        ) * 1000
        self.last_semantic_state = state
        self.last_temporal_state = temporal
        self.last_context = context
        self.last_planning_references = references
        self.session_store.record(snapshot, state_id=state.state_id)
        self.last_observation_latency_ms = (time.perf_counter() - started) * 1000
        return snapshot

    def _build_snapshot(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        context,
        references,
    ) -> CompanionSnapshot:
        promoted_confidence = [
            state.confidence,
            context.confidence,
            *(reference.confidence for reference in references),
        ]
        confidence = round(min(promoted_confidence), 4)
        information_gaps = [
            reference.description
            for reference in references
            if reference.reference_type is PlanningReferenceType.INFORMATION_GAP
        ]
        if state.unresolved_evidence_ids:
            information_gaps.append(
                f"未解析证据数量：{len(state.unresolved_evidence_ids)}"
            )
        uncertainties = list(
            dict.fromkeys(
                [
                    *context.uncertainties,
                    *(
                        uncertainty
                        for reference in references
                        for uncertainty in reference.uncertainties
                    ),
                ]
            )
        )
        return CompanionSnapshot(
            snapshot_id=f"companion-{state.state_id}",
            timestamp=state.timestamp,
            observation_id=state.observation_id,
            semantic_state=SemanticStateSummary(
                state_id=state.state_id,
                observation_id=state.observation_id,
                timestamp=state.timestamp,
                location=self._entity_summary(state.location),
                nearby_entities=[
                    self._entity_summary(reference)
                    for reference in state.nearby_entities
                ],
                quest_context=[
                    self._entity_summary(reference)
                    for reference in state.quest_context
                ],
                inventory_references=[
                    self._entity_summary(reference)
                    for reference in state.inventory_references
                ],
                unknown_count=len(state.unknown_references),
                unresolved_evidence_count=len(state.unresolved_evidence_ids),
                conflict_count=len(state.conflict_evidence_ids),
                stale_count=len(state.stale_evidence_ids),
                history_size=state.history_size,
                confidence=state.confidence,
            ),
            temporal_summary=TemporalSummary.from_temporal_state(temporal),
            context_understanding=self._safe_context(context),
            planning_references=[
                self._safe_reference(reference) for reference in references
            ],
            information_gaps=list(dict.fromkeys(information_gaps)),
            uncertainties=uncertainties,
            confidence=confidence,
            data_quality_notes=[
                f"Knowledge source type: {self.source_provenance.source_type}",
                "Knowledge readiness: FOUNDATION_ONLY",
                "Real Vision readiness: FOUNDATION_ONLY",
                "当前知识为有限快照，未承诺完整覆盖",
            ],
            readiness_notes=[
                "Companion Loop: FOUNDATION",
                "Overall: NOT_READY",
                "只读状态，不提供行为决定",
            ],
            source_provenance=self.source_provenance,
        )

    def _entity_summary(self, reference) -> CompanionEntitySummary | None:
        if reference is None:
            return None
        return CompanionEntitySummary(
            canonical_id=reference.canonical_id,
            entity_type=reference.entity_type,
            display_name=reference.display_name,
            lifecycle=reference.lifecycle,
            confidence=reference.confidence,
            reason=reference.reason,
        )

    def _safe_provenance(self) -> KnowledgeEntityProvenance:
        """Expose only configured, path-free dataset provenance."""
        return KnowledgeEntityProvenance(
            source_id=self.source_provenance.source_id,
            source_type=self.source_provenance.source_type,
            source_name=self.source_provenance.dataset_reference,
            game_profile=self.source_provenance.game_profile,
            server_profile=self.source_provenance.server_profile,
            data_version=self.source_provenance.data_version,
            snapshot_version=self.source_provenance.data_version,
        )

    def _safe_context(self, context: ContextUnderstanding) -> ContextUnderstanding:
        provenance = self._safe_provenance()
        return context.model_copy(
            deep=True,
            update={
                "related_entities": [
                    entity.model_copy(update={"provenance": provenance})
                    for entity in context.related_entities
                ],
                "related_relations": [
                    relation.model_copy(update={"provenance": provenance})
                    for relation in context.related_relations
                ],
            },
        )

    def _safe_reference(self, reference):
        provenance = self._safe_provenance()
        return reference.model_copy(
            deep=True,
            update={
                "supporting_entities": [
                    entity.model_copy(update={"provenance": provenance})
                    for entity in reference.supporting_entities
                ],
                "supporting_relations": [
                    relation.model_copy(update={"provenance": provenance})
                    for relation in reference.supporting_relations
                ],
            },
        )
