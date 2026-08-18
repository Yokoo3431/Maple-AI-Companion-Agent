# Phase 13-P Evaluation / Simulation Layer

## Boundary

Phase 13-P is a read-only quality gate for the existing semantic chain:

`Perception Evidence -> Knowledge Resolution -> Semantic Game State -> Temporal Memory -> Knowledge Graph -> Context Understanding -> Evaluation`

The layer evaluates outputs from Phase 13-J, 13-K, 13-N and 13-O. It does not add a resolver, memory store, graph, planner, action model, execution path, crawler, client extraction, input provider, or LLM dependency. Vision, importing, resolution, temporal reduction, graph validation and safety contracts remain frozen.

## Evaluation architecture

`EvaluationCase` stores a sanitized semantic state reference, expected descriptive context, lifecycle expectations and confidence inputs. `ContextReasoner` is called as an existing read-only dependency. `ContextEvaluationResult` records expected/actual context, active status, uncertainty, confidence-bound violations and an explicit failure reason. `EvaluationReport` aggregates results and metrics.

The evaluator never overwrites evidence or changes upstream state. It only compares the observed semantic result with a fixture expectation. The existing Phase 5-F execution-oriented `evaluation` models remain compatible with Agent Loop; the Phase 13-P result is separately named `ContextEvaluationResult` to avoid a second execution pipeline or a breaking model collision.

## Benchmark philosophy

The committed fixture is structured semantic data only. It contains seven cases: normal map/NPC/quest context, quest-item context, unresolved entity, expired entity, lost entity, conflicting location candidates and a low-confidence relation. It is not a production Maple database and does not claim server completeness. Provenance identifies the sanitized fixture and carries profile/version/hash metadata.

## Metrics and denominators

The report calculates context accuracy, unknown preservation, conflict preservation, false promotion, expired exclusion, lost handling and confidence-bound violations. Every rate carries an explicit denominator. Empty categories return `null`, with `INSUFFICIENT_DATA`; no rate is fabricated from an absent denominator. The fixture report is `SUFFICIENT` only because the corresponding cases are present.

Context confidence is checked against the weakest confidence supplied for the evaluated semantic context. The existing reasoner uses the minimum of state, entity, relation and resolved graph confidence; the evaluator records any upward-bound violation rather than repairing it.

## Temporal replay

Replay reuses Phase 13-K's semantic state lifecycle outputs and Phase 13-O's `TemporalState` projection. The sanitized replay report records only lifecycle, context type, active/historical status and uncertainty count for `VISIBLE -> LOST -> EXPIRED`. It never serializes screenshots, raw OCR/evidence, sessions or private paths.

## Known limitations

- The fixture is intentionally small and synthetic/sanitized; it is not a complete Maple Island knowledge source.
- Evaluation validates deterministic rule behavior, not real-world recall or precision against live gameplay.
- A low-confidence relation can preserve a descriptive location context while remaining excluded from promoted relation context; this distinction is intentional.
- `INSUFFICIENT_DATA` prevents unsupported claims but is not a readiness upgrade.

Readiness remains `Knowledge = FOUNDATION_ONLY`, `Real Vision = FOUNDATION_ONLY`, `Overall = NOT_READY`, and `SAFETY_MODE = MOCK_ONLY`.
