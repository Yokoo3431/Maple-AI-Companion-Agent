# Phase 13-S — Runtime Contract Reconciliation & Real/Replay Session Validation

## Boundary

Phase 13-S is a contract-reconciliation and validation phase. It does not add
new context, planning, quest, map, combat, or decision rules. The safety
boundary remains:

~~~text
SAFETY_MODE=MOCK_ONLY
READ ONLY
NO INPUT
NO EXECUTION
~~~

The existing Phase 13-R chain remains the only cognitive runtime:

~~~text
CurrentObservation
  -> EvidenceResolver
  -> SemanticGameState / StateReducer
  -> TemporalState
  -> KnowledgeGraph
  -> ContextReasoner
  -> PlanningReferenceEngine
  -> CompanionSnapshot
~~~

## Contract reconciliation

The repository contains two historical graph interfaces with different
ownership boundaries:

| Interface | Owner | Runtime responsibility |
|---|---|---|
| MapleKnowledgeGraph | Phase 9-D / Phase 13-J | canonical evidence lookup and alias resolution |
| KnowledgeGraph | Phase 4-A / Phase 13-N | relationship truth and read-only graph queries |
| KnowledgeDatasetPackage | Phase 13-L/M | source snapshot metadata, content hash, package validation |
| RuntimeKnowledgeBundle | Phase 13-S | references existing views and verifies shared identity/metadata |

RuntimeKnowledgeBundle is not a third graph and stores no entity or relation
facts. For a source-backed package it reuses the existing Phase 4-E
build_dataset importer to materialize both historical views with the same
typed canonical IDs and provenance. The bundle then audits Map/NPC/Quest/Item
identity overlap, aliases, profile, provenance, version, and missing entities.
Invalid differences are reported, never repaired.

The current source-backed slice is consistent: 400 entities in each view,
400 canonical IDs overlapping, and zero mismatch counters. The historical
dual-graph shape remains documented debt because future loaders must continue
to prove that both views came from one package identity.

## Provenance and profile ownership

KnowledgeDatasetPackage.manifest is the source of truth for source identity,
source type, game profile, server profile, dataset version, public source
reference, and content hash. Production CompanionRuntime no longer falls back
to maple-v113. If a caller supplies graphs without trusted metadata, runtime
uses UNKNOWN/UNBOUND and records a quality issue. Fixture metadata such as
maple-v113-fixture exists only in benchmark factories.

## Replay and existing Vision input

Structured replay and existing Vision observations use the same
CompanionRuntimeCoordinator. ExistingVisionObservationAdapter only wraps an
existing CurrentObservation or converts already-produced PerceptionEvidence;
it does not capture windows, run OCR, perform template matching, or add a new
Vision backend. A future HOME session can therefore feed existing Vision
output into the same coordinator.

This Notebook has no detected Maple client. The committed real-session report
is consequently REAL_SESSION_PENDING with zero observations and zero
snapshots. It is not a real-client accuracy result and does not affect the
existing Vision readiness gate.

## Real-session evidence and privacy

Level A (10 minutes) and Level B (30–60 minutes) are operational targets for a
HOME machine with a Maple client. Session reports may contain only aggregate
duration, counts, latency, lifecycle, failure, provenance, and memory
summaries. Screenshots, ROI crops, raw OCR, account/character/chat content,
PID/HWND, absolute paths, and raw observations remain local-only.

## Baseline governance decision

BASELINE.json is treated as the long-lived Phase 13-I.4 reference snapshot,
not as the active phase pointer. This matches prior handoff semantics, where
later integration commits do not recursively rewrite baseline metadata. The
repository governance does not state this distinction as a single formal
sentence, so the policy is recorded as GOVERNANCE_AMBIGUITY for reviewer
confirmation; Phase 13-S does not modify the file.

## Readiness and limitations

The cross-graph contract is validated for the committed community package,
but this is not complete Maple knowledge validation. Replay is validated; the
real session remains pending on HOME. Therefore:

~~~text
Real Vision       = FOUNDATION_ONLY
Knowledge         = FOUNDATION_ONLY
Companion Loop    = FOUNDATION
Companion Session = FOUNDATION_ONLY / NOT_VALIDATED
Overall           = NOT_READY
~~~

No new Vision architecture, resolver, graph, planner, executor, input path,
or automation is introduced.
