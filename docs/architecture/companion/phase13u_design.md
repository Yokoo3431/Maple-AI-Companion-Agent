# Phase 13-U — Real Session Evidence Validation

## Boundary

Phase 13-U validates whether an already supported Maple client can drive the
existing read-only path:

```text
Existing Vision Observation
        ↓
CurrentObservation
        ↓
CompanionRuntimeCoordinator
        ↓
CompanionSnapshot
```

This is an evidence-validation phase, not a new cognition phase. It does not
add resolver rules, temporal rules, graph facts, context rules, planning, input
handling, automation, or execution. The existing Vision pipeline remains the
only capture/OCR/CV boundary, and replay and real observations continue to use
the same `CompanionRuntimeCoordinator`.

## Session gates

Level A is a user-started, read-only 10-minute session. It records whether
capture, observation creation, snapshot creation, timestamp progression,
append-only history and latency summaries remain stable. Level B is an optional
30–60 minute extension for continuity and memory-growth evidence. Neither
duration is a readiness claim by itself.

The Notebook has no detected Maple client at this checkpoint. Therefore the
checked-in report is explicitly `REAL_SESSION_PENDING`; zero real observations
are not interpreted as successful capture. The existing 101-event structured
replay is retained only as a runtime-hardening baseline.

## Aggregate evidence

The report records only duration, counts, failure categories, latency,
history/lifecycle counters, confidence-related counts, provenance status,
privacy status and safety status. Screenshots, OCR text, ROI data, account or
character data, chat, PID/HWND, absolute paths and raw observations are outside
the report schema and remain local-only if a future HOME session is run.

## Safety and readiness

The session boundary is `SAFETY_MODE=MOCK_ONLY`, `READ ONLY`, `NO INPUT` and
`NO EXECUTION`. A real session may only validate the observation-to-snapshot
contract; it cannot raise Real Vision, Knowledge or Overall readiness. Until a
user-started HOME session supplies evidence, `Companion Session` remains
`FOUNDATION_ONLY / NOT_VALIDATED` and Overall remains `NOT_READY`.

## Known limitations

No Maple client was available on the Notebook, so window states, capture
failures, real OCR/CV output, real lifecycle changes and real memory growth are
not measured here. Replay hardening is useful for deterministic runtime
regression but is not Vision accuracy and cannot substitute for HOME evidence.
