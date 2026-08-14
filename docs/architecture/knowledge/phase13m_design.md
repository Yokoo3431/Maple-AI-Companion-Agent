# Phase 13-M Real Knowledge Dataset Acquisition & Validation

## Boundary

Phase 13-M adds a local, versioned, sanitized snapshot package. It does not
add a network runtime, crawler, reverse engineering path, client extraction,
or a second knowledge graph/importer/resolver.

```text
Public static snapshot
        ↓
knowledge_dataset/manifest.json + entities/*.json
        ↓
KnowledgeDatasetPackageAdapter
        ↓
Existing Phase 4-E Generic Import Pipeline
        ↓
Existing canonical mapper and Phase 13-G quality gate
        ↓
Phase 13-J EvidenceResolver
        ↓
Phase 13-K ObservationHistory / StateReducer
```

## Package contract

Each package declares dataset version, source ID/name/reference, source type,
game profile, server profile, snapshot version, deterministic content hash,
entity counts, expected denominators, provenance fields and sanitization
status. Entity files contain only structured records; screenshots, sessions,
private paths, client files and personal data are excluded.

The initial acquisition profile is an explicit snapshot from the public
Chinese nostalgic-server database site `mxdc.dvg.cn` ("冒险岛怀旧服小册子").
It is classified as `COMMUNITY_DATABASE`, not as an official Tencent/Nexon
data feed. The package therefore uses a community Chinese nostalgic profile
and does not claim that it is an exact official server build. The snapshot is
not treated as the project's existing `maple-v113` profile and cannot
independently make Knowledge READY. The package records the public source,
snapshot date/version and terms reference for reviewer traceability.

The first package intentionally imports only a bounded slice of the public
catalog: 50 maps, 100 NPCs, 50 quests and 200 items. It keeps Chinese IDs and
names plus the minimum semantic references needed by the existing importer;
resource/icon URLs, descriptions that are not needed for resolution, runtime
sessions and local paths are excluded.

## Validation

The package validator checks manifest/file count agreement, content hash,
duplicate IDs, per-type name/alias conflicts, provenance completeness, missing
relation references and invalid relation types. Coverage is calculated against
manifest denominators; missing denominators remain unavailable. The existing
`KnowledgeQualityBenchmark` remains the readiness metric producer.

## Canonical and semantic compatibility

The snapshot's source IDs are mapped through an explicit canonical entity
index. This is deterministic source-identity canonicalization, not a claim
that the snapshot covers every Maple profile. The package adapter feeds the
same `KnowledgeImportOrchestrator`; Phase 13-J resolution and Phase 13-K
temporal reduction consume the existing canonical graph/evidence contracts.

## Readiness and safety

The expected real snapshot denominator is useful for measuring coverage, but
profile mismatch, source limitations, canonical scope and missing production
coverage keep Knowledge at `FOUNDATION_ONLY`. Runtime remains
`SAFETY_MODE=MOCK_ONLY`, read-only, with no input or execution path.
