# Phase 13-J Knowledge Graph & Semantic State Foundation

## Scope

Phase 13-J extends the existing read-only knowledge path:

```text
PerceptionEvidence
    ↓
KnowledgeGuidedResolver / EvidenceResolver
    ↓
SemanticGameState
```

The phase does not add input providers, execution, automation, keyboard or
mouse control, memory reading, hooks, injection, or action planning.

## 1. Canonical entities

The existing `MapleKnowledgeGraph` remains the canonical graph store. Its
`MapleKnowledgeEntity` identity is `knowledge_id`; names and aliases are
lookup material, never identity. The supported Phase 13-J entity types are:

- `MAP`
- `NPC`
- `MONSTER`
- `ITEM`
- `EQUIPMENT`
- `QUEST`
- `STORY_LORE`

Every canonical entity carries `knowledge_id`, `name`, `aliases`, typed
provenance, confidence, and data version. Provenance records the source id,
source type/reference, game/server profile, snapshot/data version, and content
hash where available. Existing `source` and `timestamp` fields remain for
backward compatibility.

The importer rejects duplicate canonical ids and records naming/alias
conflicts instead of silently overwriting an entity.

## 2. Knowledge graph relationships

Existing relation storage is reused and extended with deterministic semantic
relations, including `LOCATED_IN`, `CONTAINS`, `SPAWNS`, `DROPS`, `REQUIRES`,
`REWARDS`, `CONNECTED_TO`, `USES`, `EQUIPPED_BY`, `PART_OF`, `ADVANCES`, and
`REVEALS`. Relations reference canonical ids and remain read-only references.

The generic Phase 4-E importer is extended with the new entity collections and
relation vocabulary. No second importer or parallel graph database is added.

## 3. Evidence vs Resolution separation

`PerceptionEvidence` remains the immutable observation-side contract. It keeps
the original evidence id, observed value, confidence, source, frame id, ROI,
and method. The resolver produces `ResolutionCandidate` records containing a
canonical id, entity type, match type, match score, and resolution confidence.

Resolver output references evidence by id and never overwrites or promotes
observed text into canonical truth. Exact id/name and exact alias matching are
deterministic. Unknown or ambiguous evidence remains unresolved and is
reported as such.

## 4. Semantic Game State model

The existing `GameStateReference` remains compatible. Phase 13-J adds a
read-only `CurrentObservation` input and `SemanticGameState` output in the
existing `game_state` package.

`CurrentObservation` contains the observation id, timestamp, original
`PerceptionEvidence`, and optional player-status reference. `SemanticGameState`
contains:

- resolved location;
- player status reference;
- nearby resolved entities;
- quest context references;
- inventory/equipment references;
- all resolution candidates and unresolved evidence ids;
- an aggregate confidence and source observation id.

No field is an action, command, target coordinate, or execution permission.

## 5. Import pipeline reuse

Sources continue to flow through:

```text
KnowledgeSourceAdapter
    → KnowledgeImportOrchestrator
    → Phase 4-E run_import/build_dataset/validate
    → CanonicalMapper / quality benchmark
    → MapleKnowledgeGraph
```

Phase 13-G `KnowledgeSourceReference`, manifest, mapping records, and
automatic readiness policy remain the provenance and quality boundary. The
new fixture is sanitized and local to tests; it is not a production database.

## 6. Readiness impact

The fixture and resolver add measurable canonical coverage, provenance
coverage, unresolved rate, and conflict rate. Readiness remains automatic via
`build_knowledge_readiness`; a small fixture without a production coverage
denominator must remain `FOUNDATION_ONLY`. No readiness value is hand-written
as `READY`.

## Compatibility and safety decision

Existing public models and queries keep their defaults and behavior. New
fields are optional with defaults. The only permitted Phase 13-J consumers are
read-only semantic understanding and quality evaluation. `SAFETY_MODE` remains
`MOCK_ONLY`.
