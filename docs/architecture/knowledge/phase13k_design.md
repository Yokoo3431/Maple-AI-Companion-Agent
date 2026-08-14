# Phase 13-K Temporal Memory & Semantic State Evolution

## Scope

Phase 13-K extends the Phase 13-J read-only semantic path:

```text
PerceptionEvidence
    ↓
EvidenceResolver
    ↓
ObservationHistory
    ↓
StateReducer
    ↓
Stable SemanticGameState
```

The phase adds temporal memory only. It does not add input providers,
execution, automation, keyboard or mouse control, hooks, injection, memory
reading, screenshots, or raw session storage.

## 1. Observation history

`ObservationHistoryEntry` stores one sanitized semantic observation boundary:

- observation timestamp and id;
- original `PerceptionEvidence` records;
- corresponding `EvidenceResolution` records;
- aggregate evidence confidence;
- a non-path source label;
- optional player status reference.

`ObservationHistory` is append-only. Ordering is deterministic by timestamp and
observation id. History is never pruned by the reducer. The history model is a
structured in-memory record; replay output intentionally excludes raw evidence
values and is not a screenshot/session archive.

## 2. Temporal reducer

`StateReducer` consumes an `ObservationHistory` or a sequence of
`CurrentObservation` values. When given observations, it uses the existing
Phase 13-J `EvidenceResolver` and materializes the corresponding history
entries; it does not introduce a second resolver or importer.

For each canonical entity the reducer performs deterministic recency-weighted
confidence aggregation. The reducer accepts an explicit `now` value in tests
and uses UTC in normal operation. Evidence ages are classified using two
thresholds:

- `stale_after_seconds`: evidence is no longer fresh;
- `expiry_after_seconds`: evidence is too old to support an active reference.

The resulting `SemanticGameState` keeps unresolved ids, conflict ids, stale
evidence ids, and lifecycle-bearing references. Unknown is never converted to
absent.

## 3. Entity lifecycle

`SemanticEntityReference.lifecycle` uses four explicit values:

- `VISIBLE`: selected in the latest fresh observation;
- `LOST`: previously selected, absent from the latest observation, but not yet
  expired;
- `UNKNOWN`: an observation exists but has no safe canonical resolution;
- `EXPIRED`: the last selected evidence is older than the expiry threshold.

History remains available for every lifecycle. Lifecycle is a state projection,
not deletion or mutation of past evidence.

## 4. Conflict and uncertainty

Resolver conflicts remain explicit. Same-category competing selections in the
latest observation are reported as conflicts and are not silently merged.
Unresolved evidence produces an `UNKNOWN` reference with its evidence id,
confidence, and reason. The reducer never infers that an unknown or absent
observation means the entity is absent.

## 5. Sanitized replay

`save_semantic_memory_trace` writes a `semantic_memory_trace.json` containing
state-transition summaries: state ids, observation ids, timestamps, lifecycle
changes, unresolved/conflict/stale counts, and confidence. It does not write
screenshots, private paths, raw session payloads, or raw observed game text.

## 6. Readiness and safety impact

Temporal aggregation improves semantic stability measurement but does not create
a production knowledge denominator or real-vision validation evidence.
Readiness therefore remains automatic and stays `FOUNDATION_ONLY`.
`SAFETY_MODE` remains `MOCK_ONLY`; no state produced by this phase is an
execution permission or action plan.
