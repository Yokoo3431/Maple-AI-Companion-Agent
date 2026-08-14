"""Temporal semantic memory and deterministic state reduction (Phase 13-K)."""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.game_state.models import (
    CurrentObservation,
    EntityLifecycle,
    PlayerStateReference,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.hybrid_vision.knowledge_resolution import EvidenceResolver
from maple_agent.hybrid_vision.models import EvidenceResolution, PerceptionEvidence
from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class ObservationHistoryEntry(BaseModel):
    """One append-only observation and its already computed resolutions."""

    observation_id: str
    timestamp: datetime
    evidence: list[PerceptionEvidence] = Field(default_factory=list)
    resolutions: list[EvidenceResolution] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""
    player_status: PlayerStateReference | None = None


class ObservationHistory(BaseModel):
    """Append-only temporal memory; old entries are never deleted."""

    entries: list[ObservationHistoryEntry] = Field(default_factory=list)

    def append(self, entry: ObservationHistoryEntry) -> ObservationHistoryEntry:
        """Append an entry without pruning or replacing existing history."""
        self.entries.append(entry)
        return entry

    def add_observation(
        self,
        observation: CurrentObservation,
        resolutions: Sequence[EvidenceResolution],
        *,
        confidence: float | None = None,
        source: str | None = None,
    ) -> ObservationHistoryEntry:
        """Record one observation and its one-to-one resolution records."""
        resolution_list = list(resolutions)
        if len(resolution_list) != len(observation.evidence):
            raise ValueError("each perception evidence needs one resolution")
        for evidence, resolution in zip(observation.evidence, resolution_list):
            if evidence.evidence_id != resolution.evidence_id:
                raise ValueError("resolution evidence ids must preserve ordering")
        aggregate = confidence
        if aggregate is None:
            values = [evidence.confidence for evidence in observation.evidence]
            aggregate = sum(values) / len(values) if values else 0.0
        entry = ObservationHistoryEntry(
            observation_id=observation.observation_id,
            timestamp=_as_utc(observation.timestamp),
            evidence=list(observation.evidence),
            resolutions=resolution_list,
            confidence=round(aggregate, 4),
            source=source if source is not None else observation.source,
            player_status=observation.player_status,
        )
        return self.append(entry)

    def ordered_entries(self) -> list[ObservationHistoryEntry]:
        """Return deterministic chronological ordering without mutating history."""
        return sorted(
            self.entries,
            key=lambda entry: (_as_utc(entry.timestamp), entry.observation_id),
        )

    @property
    def latest(self) -> ObservationHistoryEntry | None:
        ordered = self.ordered_entries()
        return ordered[-1] if ordered else None


class SemanticStateTransition(BaseModel):
    """Sanitized transition summary; it contains no raw evidence values."""

    transition_id: str
    previous_state_id: str = ""
    state_id: str
    from_observation_id: str = ""
    to_observation_id: str
    timestamp: datetime
    changed_entities: list[str] = Field(default_factory=list)
    lifecycle_changes: dict[str, str] = Field(default_factory=dict)
    confidence_before: float = Field(default=0.0, ge=0, le=1)
    confidence_after: float = Field(default=0.0, ge=0, le=1)
    unresolved_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    stale_count: int = Field(default=0, ge=0)
    reasoning: list[str] = Field(default_factory=list)


SelectedEvent = tuple[
    ObservationHistoryEntry,
    PerceptionEvidence,
    EvidenceResolution,
]


class StateReducer:
    """Reduce multiple observations into one read-only semantic state."""

    _LOCATION_TYPES = {"map", "map_label", "location"}
    _QUEST_TYPES = {"quest", "quest_context"}
    _INVENTORY_TYPES = {"item", "equipment", "inventory", "inventory_item"}

    def __init__(
        self,
        graph: MapleKnowledgeGraph,
        *,
        evidence_resolver: EvidenceResolver | None = None,
        stale_after_seconds: float = 30.0,
        expiry_after_seconds: float = 120.0,
        now: datetime | None = None,
    ) -> None:
        if stale_after_seconds < 0 or expiry_after_seconds <= stale_after_seconds:
            raise ValueError("expiry must be greater than stale threshold")
        self.graph = graph
        self.evidence_resolver = evidence_resolver or EvidenceResolver()
        self.stale_after_seconds = stale_after_seconds
        self.expiry_after_seconds = expiry_after_seconds
        self.now = now
        self.last_state: SemanticGameState | None = None
        self.last_transition: SemanticStateTransition | None = None

    def reduce(
        self,
        observations: ObservationHistory | Sequence[CurrentObservation],
    ) -> SemanticGameState:
        history = self._materialize_history(observations)
        entries = history.ordered_entries()
        if not entries:
            raise ValueError("cannot reduce empty observation history")
        latest = entries[-1]
        now = _as_utc(self.now or datetime.now(UTC))
        selected_events: dict[str, list[SelectedEvent]] = defaultdict(list)
        unresolved_ids: list[str] = []
        stale_ids: list[str] = []
        conflict_ids: list[str] = []
        confidence_values: list[float] = []

        for entry in entries:
            for evidence, resolution in zip(entry.evidence, entry.resolutions):
                age = self._age_seconds(now, entry.timestamp)
                if age > self.stale_after_seconds:
                    stale_ids.append(evidence.evidence_id)
                if resolution.conflict:
                    conflict_ids.append(evidence.evidence_id)
                if not resolution.resolved or resolution.selected is None:
                    unresolved_ids.append(evidence.evidence_id)
                    confidence_values.append(resolution.evidence_confidence)
                    continue
                selected_events[resolution.selected.canonical_id].append(
                    (entry, evidence, resolution)
                )
                confidence_values.append(resolution.selected.resolution_confidence)

        latest_type_events: dict[str, list[tuple[str, str]]] = defaultdict(list)
        for evidence, resolution in zip(latest.evidence, latest.resolutions):
            if resolution.resolved and resolution.selected is not None:
                latest_type_events[evidence.evidence_type.strip().lower()].append(
                    (evidence.evidence_id, resolution.selected.canonical_id)
                )
        for evidence_type, values in latest_type_events.items():
            canonical_ids = {canonical_id for _, canonical_id in values}
            if evidence_type in self._LOCATION_TYPES and len(canonical_ids) > 1:
                conflict_ids.extend(evidence_id for evidence_id, _ in values)

        references: dict[str, SemanticEntityReference] = {}
        reference_types: dict[str, str] = {}
        for canonical_id, events in selected_events.items():
            event = max(
                events,
                key=lambda item: (
                    _as_utc(item[0].timestamp),
                    item[0].observation_id,
                    item[1].evidence_id,
                ),
            )
            entry, evidence, resolution = event
            last_seen = _as_utc(entry.timestamp)
            age = self._age_seconds(now, last_seen)
            is_latest = entry.observation_id == latest.observation_id
            if age >= self.expiry_after_seconds:
                lifecycle = EntityLifecycle.EXPIRED
                reason = "last selected evidence exceeded expiry threshold"
            elif is_latest and age <= self.stale_after_seconds:
                lifecycle = EntityLifecycle.VISIBLE
                reason = "selected by latest fresh observation"
            else:
                lifecycle = EntityLifecycle.LOST
                reason = "not selected by latest fresh observation"
            weights = [
                max(
                    0.1,
                    1.0
                    - self._age_seconds(now, item[0].timestamp)
                    / self.expiry_after_seconds,
                )
                for item in events
            ]
            values = [
                item[2].selected.resolution_confidence
                for item in events
                if item[2].selected is not None
            ]
            aggregate = (
                sum(value * weight for value, weight in zip(values, weights))
                / sum(weights)
                if values
                else 0.0
            )
            reference = SemanticEntityReference(
                canonical_id=canonical_id,
                entity_type=resolution.selected.entity_type,
                display_name=resolution.selected.display_name,
                confidence=round(aggregate, 4),
                evidence_ids=[item[1].evidence_id for item in events],
                source=resolution.selected.source,
                version=resolution.selected.version,
                lifecycle=lifecycle,
                last_observed_at=last_seen,
                reason=reason,
            )
            references[canonical_id] = reference
            reference_types[canonical_id] = evidence.evidence_type.strip().lower()

        unknown_references = self._unknown_references(latest, conflict_ids)
        conflict_ids = list(dict.fromkeys(conflict_ids))
        unresolved_ids = list(dict.fromkeys(unresolved_ids))
        stale_ids = list(dict.fromkeys(stale_ids))

        location_refs = [
            reference
            for canonical_id, reference in references.items()
            if reference_types[canonical_id] in self._LOCATION_TYPES
        ]
        location_conflict = self._has_latest_category_conflict(
            latest, self._LOCATION_TYPES
        )
        location = (
            self._unknown_reference("location", "conflicting location candidates")
            if location_conflict
            else self._latest_reference(location_refs)
        )
        nearby = [
            reference
            for canonical_id, reference in references.items()
            if reference_types[canonical_id] not in self._LOCATION_TYPES
            | self._QUEST_TYPES
            | self._INVENTORY_TYPES
        ]
        quests = [
            reference
            for canonical_id, reference in references.items()
            if reference_types[canonical_id] in self._QUEST_TYPES
        ]
        inventory = [
            reference
            for canonical_id, reference in references.items()
            if reference_types[canonical_id] in self._INVENTORY_TYPES
        ]
        if location_conflict:
            unknown_references.append(location)
        player_status = self._latest_player_status(entries, now)
        aggregate_confidence = (
            round(sum(confidence_values) / len(confidence_values), 4)
            if confidence_values
            else 0.0
        )
        state = SemanticGameState(
            state_id=new_id(),
            observation_id=latest.observation_id,
            timestamp=_as_utc(latest.timestamp),
            location=location,
            player_status=player_status,
            nearby_entities=nearby,
            quest_context=quests,
            inventory_references=inventory,
            resolution_candidates=[
                candidate
                for entry in entries
                for resolution in entry.resolutions
                for candidate in resolution.candidates
            ],
            unresolved_evidence_ids=unresolved_ids,
            evidence=[
                evidence for entry in entries for evidence in entry.evidence
            ],
            confidence=aggregate_confidence,
            history_size=len(entries),
            stale_evidence_ids=stale_ids,
            conflict_evidence_ids=conflict_ids,
            unknown_references=unknown_references,
            reasoning=[
                f"history_entries={len(entries)}",
                f"resolved_entities={len(references)}",
                f"unresolved_evidence={len(unresolved_ids)}",
                f"conflicts={len(conflict_ids)}",
                f"stale_evidence={len(stale_ids)}",
                "temporal reduction is read-only; no action planning performed",
            ],
        )
        self.last_transition = self._transition(self.last_state, state)
        self.last_state = state
        return state

    def _materialize_history(
        self,
        observations: ObservationHistory | Sequence[CurrentObservation],
    ) -> ObservationHistory:
        if isinstance(observations, ObservationHistory):
            return observations
        history = ObservationHistory()
        for observation in observations:
            resolutions = [
                self.evidence_resolver.resolve(evidence, self.graph)
                for evidence in observation.evidence
            ]
            history.add_observation(observation, resolutions)
        return history

    @staticmethod
    def _age_seconds(now: datetime, timestamp: datetime) -> float:
        return max(0.0, (now - _as_utc(timestamp)).total_seconds())

    @staticmethod
    def _latest_reference(
        references: list[SemanticEntityReference],
    ) -> SemanticEntityReference | None:
        return max(
            references,
            key=lambda reference: reference.last_observed_at or datetime.min.replace(tzinfo=UTC),
            default=None,
        )

    def _unknown_references(
        self,
        entry: ObservationHistoryEntry,
        conflict_ids: list[str],
    ) -> list[SemanticEntityReference]:
        unknown: list[SemanticEntityReference] = []
        for evidence, resolution in zip(entry.evidence, entry.resolutions):
            if resolution.resolved and not resolution.conflict:
                continue
            reason = (
                "multiple canonical candidates"
                if resolution.conflict
                else (resolution.reasoning[0] if resolution.reasoning else "unresolved")
            )
            unknown.append(
                self._unknown_reference(
                    evidence.evidence_type.strip().lower(),
                    reason,
                    evidence_id=evidence.evidence_id,
                    confidence=resolution.evidence_confidence,
                    timestamp=entry.timestamp,
                )
            )
        return unknown

    @staticmethod
    def _unknown_reference(
        entity_type: str,
        reason: str,
        *,
        evidence_id: str = "",
        confidence: float = 0.0,
        timestamp: datetime | None = None,
    ) -> SemanticEntityReference:
        return SemanticEntityReference(
            canonical_id="",
            entity_type=entity_type,
            display_name="UNKNOWN",
            confidence=confidence,
            evidence_ids=[evidence_id] if evidence_id else [],
            lifecycle=EntityLifecycle.UNKNOWN,
            last_observed_at=_as_utc(timestamp) if timestamp else None,
            reason=reason,
        )

    @staticmethod
    def _has_latest_category_conflict(
        entry: ObservationHistoryEntry,
        categories: set[str],
    ) -> bool:
        values = {
            resolution.selected.canonical_id
            for evidence, resolution in zip(entry.evidence, entry.resolutions)
            if evidence.evidence_type.strip().lower() in categories
            and resolution.resolved
            and resolution.selected is not None
        }
        return len(values) > 1

    def _latest_player_status(
        self,
        entries: list[ObservationHistoryEntry],
        now: datetime,
    ) -> PlayerStateReference | None:
        for entry in reversed(entries):
            if entry.player_status is not None:
                if self._age_seconds(now, entry.timestamp) < self.expiry_after_seconds:
                    return entry.player_status
                return None
        return None

    @staticmethod
    def _state_references(
        state: SemanticGameState | None,
    ) -> dict[str, EntityLifecycle]:
        if state is None:
            return {}
        references = [
            reference
            for reference in [
                state.location,
                *state.nearby_entities,
                *state.quest_context,
                *state.inventory_references,
            ]
            if reference is not None and reference.canonical_id
        ]
        return {reference.canonical_id: reference.lifecycle for reference in references}

    @classmethod
    def _transition(
        cls,
        previous: SemanticGameState | None,
        current: SemanticGameState,
    ) -> SemanticStateTransition:
        previous_refs = cls._state_references(previous)
        current_refs = cls._state_references(current)
        all_ids = sorted(set(previous_refs) | set(current_refs))
        lifecycle_changes = {
            canonical_id: (
                f"{previous_refs.get(canonical_id, 'ABSENT')}"
                f"->{current_refs.get(canonical_id, 'ABSENT')}"
            )
            for canonical_id in all_ids
            if previous_refs.get(canonical_id) != current_refs.get(canonical_id)
        }
        return SemanticStateTransition(
            transition_id=new_id(),
            previous_state_id=previous.state_id if previous else "",
            state_id=current.state_id,
            from_observation_id=previous.observation_id if previous else "",
            to_observation_id=current.observation_id,
            timestamp=current.timestamp,
            changed_entities=sorted(lifecycle_changes),
            lifecycle_changes=lifecycle_changes,
            confidence_before=previous.confidence if previous else 0.0,
            confidence_after=current.confidence,
            unresolved_count=len(current.unresolved_evidence_ids),
            conflict_count=len(current.conflict_evidence_ids),
            stale_count=len(current.stale_evidence_ids),
            reasoning=["transition summary contains no raw evidence values"],
        )


def save_semantic_memory_trace(
    sessions_dir: str | Path,
    trace_id: str,
    transitions: Sequence[SemanticStateTransition],
    *,
    history_size: int = 0,
) -> None:
    """Write sanitized state transitions without screenshots or raw sessions."""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "trace_type": "semantic_memory_trace",
        "history_size": history_size,
        "state_transitions": [
            transition.model_dump(mode="json") for transition in transitions
        ],
    }
    (directory / "semantic_memory_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
