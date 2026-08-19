# Phase 13-Q Planning Reference Foundation

## Boundary

Phase 13-Q consumes the existing `SemanticGameState`, Phase 13-K temporal
lifecycle projection, Phase 13-N `KnowledgeGraph` and Phase 13-O
`ContextUnderstanding`:

`Context Understanding -> Planning Reference -> Human-readable Information`

This layer does not decide or execute behavior. It has no planner, action
model, input provider, executor, movement/combat/quest path, crawler, client
control, memory reader, hook or DLL interface. The existing Vision, Resolver,
Temporal Reducer, Importer, KnowledgeGraph core and Safety contracts remain
unchanged.

## Reference model

`PlanningReference` is an information classification with a title,
description, supporting entities/relations, source state, bounded confidence,
uncertainties, limitations and a reasoning summary. Its types are
`QUEST_CONTEXT`, `MISSING_REQUIREMENT`, `KNOWN_LOCATION`, `RELATED_ENTITY`,
`INFORMATION_GAP` and `CONFLICT_NOTICE`. These are descriptive categories,
not commands or action categories.

The existing Phase 13-N `KnowledgeGraph.PlanningContext` remains intact. The
new `planning_reference/` package is a separate semantic-to-human-readable
reference layer and does not convert `PlanningContext` into a Planner.

## Deterministic rules

- Confirmed map/NPC/quest context produces `QUEST_CONTEXT`.
- A visible quest requirement whose inventory ownership is not confirmed
  produces `MISSING_REQUIREMENT`; the wording is explicitly “未确认拥有”,
  never a claim that the item is absent.
- Unknown, stale-only or otherwise insufficient state produces
  `INFORMATION_GAP` and asks for more observation.
- Conflict evidence produces `CONFLICT_NOTICE` and never selects a candidate.
- Expired entities are excluded from supporting entities and current facts.
- A descriptive location can produce `KNOWN_LOCATION`; low-confidence graph
  relations remain in uncertainty and are not promoted.

## Confidence and uncertainty

Reference confidence is the minimum of the semantic state confidence,
ContextUnderstanding confidence, and every supporting entity/relation
confidence. It is rounded only for serialization and never increases input
certainty. Every reference carries both `uncertainties` and `limitations`.

## Benchmark and privacy

The Phase 13-Q benchmark reuses the sanitized Phase 13-P semantic fixture and
adds a small manifest for six reference cases. It contains no screenshots,
OCR payloads, sessions, private paths or personal game data. Metrics include
reference accuracy, uncertainty preservation, confidence-bound violations and
action leakage. Empty denominators return `INSUFFICIENT_DATA`.

## Readiness impact

This phase improves the system's ability to state which information is worth
human attention. It does not promote Real Vision, Knowledge or Overall
readiness. The project remains `FOUNDATION_ONLY` for Real Vision and
Knowledge, `NOT_READY` overall, and `MOCK_ONLY` for safety.
