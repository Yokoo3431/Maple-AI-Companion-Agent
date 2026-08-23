# Phase 13-R — End-to-End Read-Only Companion Loop Integration

## Boundary

Phase 13-R is an integration and audit phase. It composes the existing
perception-evidence, resolver, semantic-state, temporal-memory, knowledge
graph, context-reasoning, and planning-reference layers. It does not add a
new intelligence layer, planner, executor, input provider, automation path,
or real-client dependency.

The safety contract remains `SAFETY_MODE=MOCK_ONLY`, read-only, and no
execution. Real Vision and Knowledge readiness remain `FOUNDATION_ONLY`.

## Composition

```text
Observation
  -> existing Phase 13-J EvidenceResolver
  -> existing Phase 13-J SemanticGameState / Phase 13-K StateReducer
  -> existing Phase 13-K ObservationHistory and TemporalState projection
  -> existing Phase 13-N KnowledgeGraph
  -> existing Phase 13-O ContextReasoner
  -> existing Phase 13-Q PlanningReferenceEngine
  -> CompanionSnapshot
```

`CompanionRuntimeCoordinator` is deliberately composition-only. It injects
the two existing graph interfaces where the repository currently requires
them: the legacy resolution graph for the Phase 13-J resolver and the
Phase 13-N graph for context/reference queries. It does not duplicate any of
those rules.

## Input modes and temporal session

Structured sanitized replay is the deterministic CI mode. The coordinator
also accepts the existing `CurrentObservation`, so a future real-vision
adapter can provide observations without changing the coordinator or
reimplementing Vision. A `CompanionSession` stores only snapshot and history
reference identifiers; raw evidence remains in the existing in-memory
Phase 13-K history and is not persisted by this layer.

One coordinator owns one append-only `ObservationHistory`. Therefore a
session can project `VISIBLE -> LOST -> EXPIRED` without treating each
snapshot as an independent session. Unknown and conflicting evidence remain
explicit throughout the chain.

## Snapshot and privacy boundary

`CompanionSnapshot` contains a human-readable semantic projection,
`TemporalSummary`, context understanding, planning references, information
gaps, uncertainties, confidence, readiness notes, and configured dataset
provenance. The public semantic projection removes raw evidence values,
evidence IDs, source paths, process/window identifiers, and raw OCR fields.
Nested provenance is replaced with the configured path-free dataset summary.

`CompanionSnapshotRenderer` is formatting-only. A structural schema guard
rejects action-shaped fields such as `command`, `executor`, `input`,
`movement_plan`, and `execution_request`; replay tests also scan rendered
output for action leakage.

## Evaluation and benchmark

The sanitized A-J scenario set covers normal task context, unknown NPC,
unconfirmed item ownership, conflicting locations, low-confidence relation,
temporal lifecycle, missing relation, community provenance warning, multiple
NPCs, and empty evidence. The benchmark reports explicit denominators for
scenario pass rate, unknown/conflict preservation, temporal continuity,
planning-reference consistency, provenance preservation, confidence-bound
violations, action leakage, and snapshot generation.

The long-run smoke uses 101 structured observations to record history growth,
exceptions, determinism, and latency. These are baselines, not production
performance gates. Empty denominators are reported as
`INSUFFICIENT_DATA`, never as fabricated 100% readiness.

## Known limitations

The scenarios validate deterministic composition and safety boundaries; they
do not establish real-client OCR accuracy, complete Maple knowledge coverage,
or production readiness. The dataset remains a small sanitized community
fixture. This phase does not add context rules, planning rules, or execution
semantics.
