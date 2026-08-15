# Phase 13-N Knowledge Graph Relationship & Planning Reference Foundation

## Boundary

Phase 13-N extends the existing Phase 4-A `KnowledgeGraph` and Phase 13-M
dataset package with explicit, provenance-bearing relationships. It does not
create a second graph, importer, resolver, planner, command model or input
path.

```text
Perception Evidence
        ↓
Phase 13-J Knowledge Resolution
        ↓
Semantic Game State / Phase 13-K Temporal Memory
        ↓
existing KnowledgeGraph + validated relations
        ↓
read-only related knowledge / PlanningContext
```

## Canonical relation contract

Relations use source and target entity types plus source and target IDs. The
supported semantic types are `CONTAINS`, `GIVES`, `REQUIRES`, `DROPS` and
`REWARDS`; legacy Phase 4-A relation values remain accepted for compatibility.
Every Phase 13-N relation carries `provenance` and bounded `confidence`.

The validator rejects duplicate edges, dangling endpoints, unknown entity
types, unknown relation types, missing required provenance and invalid
confidence. Invalid records are reported; they are never repaired or silently
discarded by the graph query layer.

## Import compatibility

`KnowledgeDatasetPackageAdapter` still feeds the existing Phase 4-E Generic
Import Pipeline. The relation records are converted by the existing dataset
builder into the same `KnowledgeDataset.relations` collection and then passed
to the existing `KnowledgeGraph` builder/query surface.

## Read-only query layer

`KnowledgeGraph.related_*` methods return deterministic neighboring entities for
an entity reference. `query_related` exposes grouped `npcs`, `items`, `maps`
and `quests` without proposing actions. Query results preserve the relation
type, confidence and provenance through `RelationReference` records.

## Planning reference context

`PlanningContext` contains only:

- the current `SemanticGameState`;
- relevant entity/relation references;
- grouped possible references and reasoning.

It has no command, action, key, mouse, input, executor or execution field. It
is a read-only context object for later planning review, not a planner.

## Dataset and readiness impact

The Phase 13-M snapshot remains a bounded community snapshot. Phase 13-N adds
only relations whose endpoints can be validated in the package; the package
validator reports relation counts and integrity metrics. Missing knowledge,
missing denominators, community provenance and profile limitations continue to
keep Knowledge at `FOUNDATION_ONLY`; no readiness status is promoted by this
phase.
