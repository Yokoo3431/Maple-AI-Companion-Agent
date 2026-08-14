"""Phase 13-K temporal memory and semantic state evolution tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from maple_agent.game_state import (
    CurrentObservation,
    EntityLifecycle,
    ObservationHistory,
    StateReducer,
    save_semantic_memory_trace,
)
from maple_agent.hybrid_vision import EvidenceResolver, PerceptionEvidence
from maple_agent.maple_knowledge import (
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
    load_phase13j_fixture,
)


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_phase13j_fixture()
    base = MapleKnowledgeBase()
    for entity in entities:
        base.add_entity(entity)
    for relation in relations:
        base.add_relation(relation)
    return MapleKnowledgeGraph(base)


def _observation(
    observation_id: str,
    timestamp: datetime,
    *evidence: PerceptionEvidence,
) -> CurrentObservation:
    return CurrentObservation(
        observation_id=observation_id,
        timestamp=timestamp,
        evidence=list(evidence),
        source="fixture",
    )


def _evidence(
    evidence_id: str,
    evidence_type: str,
    value: str,
    confidence: float = 0.8,
) -> PerceptionEvidence:
    return PerceptionEvidence(
        evidence_id=evidence_id,
        evidence_type=evidence_type,
        value=value,
        confidence=confidence,
        source="fixture",
    )


def test_observation_history_is_ordered_and_append_only():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    graph = _graph()
    resolver = EvidenceResolver()
    history = ObservationHistory()
    late = _observation("obs-late", now, _evidence("e-late", "npc", "赫丽娜"))
    early = _observation(
        "obs-early",
        now - timedelta(seconds=10),
        _evidence("e-early", "npc", "玛雅"),
    )
    for observation in (late, early):
        history.add_observation(
            observation,
            [resolver.resolve(item, graph) for item in observation.evidence],
        )

    assert [entry.observation_id for entry in history.ordered_entries()] == [
        "obs-early",
        "obs-late",
    ]
    assert len(history.entries) == 2
    history.add_observation(
        _observation("obs-new", now + timedelta(seconds=1)),
        [],
    )
    assert len(history.entries) == 3


def test_state_reducer_merges_confidence_and_marks_lost_entity():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    reducer = StateReducer(
        _graph(),
        stale_after_seconds=30,
        expiry_after_seconds=120,
        now=now,
    )
    state = reducer.reduce(
        [
            _observation(
                "obs-old",
                now - timedelta(seconds=20),
                _evidence("e-npc-0", "npc", "赫丽娜", 0.6),
            ),
            _observation(
                "obs-visible",
                now - timedelta(seconds=10),
                _evidence("e-npc-1", "npc", "赫丽娜", 0.8),
            ),
            _observation(
                "obs-latest",
                now,
                _evidence("e-map", "location", "射手村", 0.9),
            ),
        ]
    )

    npc = next(item for item in state.nearby_entities if item.canonical_id == "npc_heena")
    assert state.history_size == 3
    assert npc.lifecycle is EntityLifecycle.LOST
    assert npc.confidence == 0.7048
    assert state.location is not None
    assert state.location.lifecycle is EntityLifecycle.VISIBLE
    assert state.unresolved_evidence_ids == []


def test_state_reducer_detects_same_observation_conflict():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = StateReducer(_graph(), now=now).reduce(
        [
            _observation(
                "obs-conflict",
                now,
                _evidence("e-map-a", "location", "射手村"),
                _evidence("e-map-b", "location", "魔法密林"),
            )
        ]
    )

    assert state.location is not None
    assert state.location.lifecycle is EntityLifecycle.UNKNOWN
    assert state.location.canonical_id == ""
    assert set(state.conflict_evidence_ids) == {"e-map-a", "e-map-b"}


def test_multiple_nearby_entities_are_not_a_location_conflict():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = StateReducer(_graph(), now=now).reduce(
        [
            _observation(
                "obs-nearby",
                now,
                _evidence("e-npc-a", "npc", "赫丽娜"),
                _evidence("e-npc-b", "npc", "玛雅"),
            )
        ]
    )

    assert state.conflict_evidence_ids == []
    assert {item.canonical_id for item in state.nearby_entities} == {
        "npc_heena",
        "npc_maya",
    }


def test_state_reducer_marks_old_entity_expired_and_keeps_stale_evidence():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = StateReducer(
        _graph(),
        stale_after_seconds=30,
        expiry_after_seconds=120,
        now=now,
    ).reduce(
        [
            _observation(
                "obs-old",
                now - timedelta(seconds=180),
                _evidence("e-old", "npc", "赫丽娜"),
            ),
            _observation("obs-now", now),
        ]
    )

    npc = next(item for item in state.nearby_entities if item.canonical_id == "npc_heena")
    assert npc.lifecycle is EntityLifecycle.EXPIRED
    assert "e-old" in state.stale_evidence_ids
    assert "e-old" in npc.evidence_ids


def test_unknown_evidence_is_preserved_as_unknown_not_absent():
    now = datetime(2026, 1, 1, tzinfo=UTC)
    state = StateReducer(_graph(), now=now).reduce(
        [
            _observation(
                "obs-unknown",
                now,
                _evidence("e-unknown", "npc", "未登记对象", 0.7),
            )
        ]
    )

    assert state.unresolved_evidence_ids == ["e-unknown"]
    assert len(state.unknown_references) == 1
    assert state.unknown_references[0].lifecycle is EntityLifecycle.UNKNOWN
    assert state.unknown_references[0].reason
    assert state.nearby_entities == []


def test_sanitized_semantic_memory_trace_contains_transitions_only(tmp_path):
    now = datetime(2026, 1, 1, tzinfo=UTC)
    reducer = StateReducer(_graph(), now=now)
    reducer.reduce(
        [
            _observation(
                "obs-a",
                now,
                _evidence("e-a", "npc", "赫丽娜"),
            ),
            _observation(
                "obs-b",
                now + timedelta(seconds=1),
                _evidence("e-b", "location", "射手村"),
            ),
        ]
    )
    assert reducer.last_transition is not None
    save_semantic_memory_trace(
        tmp_path,
        "trace-13k",
        [reducer.last_transition],
        history_size=2,
    )

    payload = json.loads(
        (tmp_path / "trace-13k" / "semantic_memory_trace.json").read_text(
            encoding="utf-8"
        )
    )
    serialized = json.dumps(payload, ensure_ascii=False)
    assert payload["trace_type"] == "semantic_memory_trace"
    assert payload["history_size"] == 2
    assert payload["state_transitions"][0]["to_observation_id"] == "obs-b"
    assert "e-a" not in serialized
    assert "赫丽娜" not in serialized
    assert "screenshot" not in serialized.lower()
    assert "raw_value" not in serialized
