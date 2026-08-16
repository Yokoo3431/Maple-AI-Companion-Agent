# Phase 13-O Context Reasoning Layer

## Boundary

Phase 13-O adds a deterministic, read-only interpretation layer after the
existing Phase 13-J resolver, Phase 13-K temporal reducer, and Phase 13-N
relationship graph:

```text
Perception Evidence
        ↓
Knowledge Resolution
        ↓
Semantic Game State
        ↓
Temporal Memory / lifecycle projection
        ↓
Validated KnowledgeGraph relations
        ↓
ContextUnderstanding
        ↓
existing PlanningContext reference
```

This layer is context understanding, not planning. It does not create
commands, actions, input, execution permissions, or a second planner.

## Context contract

`ContextUnderstanding` contains a state id reference, related canonical
entities, validated relation references, a descriptive `ContextType`, a
bounded confidence, a reasoning trace, and explicit uncertainties. Context
types are descriptive only: `QUEST_RELATED_CONTEXT`,
`ITEM_QUEST_CONTEXT`, `LOCATION_CONTEXT`, `NPC_RELATED_CONTEXT`,
`ITEM_RELATED_CONTEXT`, `EXPLORATION_CONTEXT`, and `UNKNOWN_CONTEXT`.

Unknown, conflicted, lost, and expired references are never converted into a
positive current fact. A lost entity may be retained as a historical
reference; an expired entity is excluded from active context candidates.

## Deterministic rules

The first rule set is intentionally small:

1. A visible current location, visible NPC, `CONTAINS` relation, and `GIVES`
   relation produce `QUEST_RELATED_CONTEXT`.
2. A visible quest, visible inventory item, and `REQUIRES` relation produce
   `ITEM_QUEST_CONTEXT`.
3. Any lifecycle other than `VISIBLE` is not an active input. `LOST` is kept
   as historical-only uncertainty; `UNKNOWN` and `EXPIRED` do not promote a
   context.
4. Relation confidence below the configured threshold remains uncertainty and
   is not included as an active related relation.
5. Multiple candidates are retained and reported as uncertainty; the reasoner
   never silently selects one.

## Confidence formula

For a promoted context:

```text
context_confidence = min(
    semantic_state.confidence,
    every participating entity confidence,
    every participating relation confidence,
)
```

The value is rounded to four decimal places. The minimum is conservative: a
context cannot be more certain than its weakest input. Entity confidence is
the existing semantic resolution aggregate, while relation confidence and
provenance are copied from the validated graph edge. No confidence is
fabricated when a component is unavailable.

## Temporal integration

`TemporalState` is a lightweight read-only projection of the existing
`SemanticGameState`: state id, timestamp, history size, lifecycle map, and
stale/conflict counts. It is not a second memory store and does not persist
raw evidence. The reasoner uses it together with the current semantic state;
the Phase 13-K history and reducer remain the source of temporal truth.

## Graph and provenance

The reasoner reads the existing `KnowledgeGraph.all_relations()` and node
lookup methods. It does not repair or rewrite graph data. Every active
`ContextRelationReference` preserves relation type, confidence, and
provenance. Low-confidence and conflicting edges are represented in the
uncertainty trace instead of being promoted.

## Dataset and readiness

The Phase 13-M bounded community snapshot remains the only real dataset. No
crawler, scraper, reverse engineering, client extraction, or external API is
introduced. Context reasoning changes no readiness gate:
Real Vision remains `FOUNDATION_ONLY`, Knowledge remains `FOUNDATION_ONLY`,
and overall controlled execution remains `NOT_READY` with `MOCK_ONLY` safety.
