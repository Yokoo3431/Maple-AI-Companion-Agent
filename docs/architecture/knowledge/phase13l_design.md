# Phase 13-L Knowledge Acquisition Pipeline & Dataset Foundation

## Scope

Phase 13-L strengthens the existing Phase 13-G acquisition path; it does not
create a second importer, graph, or resolver:

```text
External Knowledge Source
    ↓
Existing KnowledgeSourceAdapter contract
    ↓
Existing Phase 4-E run_import/build_dataset/validate
    ↓
Versioned KnowledgeDataset metadata
    ↓
Existing canonical mapper and MapleKnowledgeGraph boundary
    ↓
Extended KnowledgeQualityBenchmark
    ↓
Existing Phase 13-J EvidenceResolver
    ↓
Phase 13-K temporal semantic memory
```

No crawler, reverse engineering, client extraction, screenshots, private
sessions, personal paths, input, automation, or execution is introduced.

## 1. Versioned dataset foundation

`KnowledgeDataset` retains the Phase 4-E `version` field and adds optional
dataset metadata:

- game profile;
- server profile;
- source provenance identifiers;
- deterministic content hash.

`KnowledgeAcquisitionManifest` remains the Phase 13-G audit record. The
existing `KnowledgeImportOrchestrator` populates the dataset metadata and
writes a sanitized version record containing manifest, source metadata,
canonical mapping, and quality report. Raw source packets are not persisted.

## 2. Source adapter contract

The existing `KnowledgeSourceAdapter` protocol remains the only source
boundary. It returns a structured import packet and never writes a graph. The
existing adapters represent future source classes:

- `ManualCuratedAdapter`;
- `LocalStaticKnowledgeAdapter`;
- `WikiCommunityAdapter` for offline snapshots only;
- `StaticGameResourceAdapter` as an explicit non-parsing stub.

This phase formalizes adapter metadata and privacy-safe source serialization;
it does not add network access, crawler behavior, WZ/client extraction, or
reverse engineering.

## 3. Quality benchmark

The existing benchmark gains explicit metrics for:

- entity coverage against a declared denominator;
- canonical ID coverage;
- alias-bearing entity coverage;
- missing/dangling references and rate;
- conflict rate;
- provenance coverage.

Missing denominators remain `None`/reported as a reason. Metrics never produce
`READY` by hand; `build_knowledge_readiness` remains the only readiness gate.

## 4. Compatibility

Adapters still flow through `KnowledgeImportOrchestrator` and Phase 4-E. The
Phase 13-J resolver and Phase 13-K temporal reducer consume the same canonical
graph and evidence contracts. New entity collections are passed through the
existing generic packet path rather than a parallel importer.

## 5. Privacy and safety

Version records and acquisition traces contain metadata and summaries only.
Source references that could contain absolute/private paths are redacted at
serialization boundaries. Content hashes are deterministic identifiers, not
raw source content. Runtime remains `SAFETY_MODE=MOCK_ONLY` and all outputs are
read-only knowledge references.

## 6. Readiness impact

Version metadata, source adapters, and richer benchmark metrics improve audit
quality but do not provide production coverage denominators or real-vision
evidence. Real Vision remains `FOUNDATION_ONLY`, Knowledge remains
`FOUNDATION_ONLY`, and Overall remains `NOT_READY`.
