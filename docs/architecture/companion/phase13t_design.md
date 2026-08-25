# Phase 13-T — Real Companion Session Validation & Runtime Hardening

## Scope

Phase 13-T validates the existing read-only runtime boundary. It does not
create a new cognitive layer and does not promote replay success to real
Vision readiness.

~~~text
Existing Vision Result
  -> CurrentObservation
  -> CompanionRuntimeCoordinator
  -> CompanionSnapshot
~~~

The same CompanionRuntimeCoordinator is used for structured replay and
existing observation input. ExistingVisionObservationAdapter only converts
already-produced observation/evidence objects; it does not capture a window,
run OCR, perform CV, or add a Vision backend.

## Hardening checks

The replay hardening baseline records:

- event, observation, and snapshot counts;
- append-only history and duplicate observation IDs;
- snapshot timestamp monotonicity;
- exception count;
- deterministic context type;
- average/max observation latency and snapshot latency;
- observation interval;
- unknown, unresolved, and stale counts;
- traced peak memory.

These values are diagnostic baselines without an artificial pass threshold.
The 101-event smoke is not a production endurance claim.

## Real-session levels

Level A is a minimum 10-minute read-only HOME session. Level B targets
30–60 minutes. A real session may only consume the existing Vision pipeline
and feed CurrentObservation into the shared coordinator. If the client is not
available, the report remains REAL_SESSION_PENDING and all real counters stay
zero or unknown.

The Notebook had no detected Maple client during this phase. Therefore no
real capture, OCR, window-state, or client stability result is claimed.

## Privacy and safety

The committed report is aggregate-only. Raw screenshots, ROI crops, OCR,
chat, account/character data, PID, HWND, absolute paths, and raw observations
remain local-only.

Safety remains:

~~~text
SAFETY_MODE=MOCK_ONLY
READ ONLY
NO INPUT
NO EXECUTION
NO AUTOMATION
~~~

No keyboard/mouse, Input Provider, executor, hooks, DLL injection, memory
reading, client modification, planner, or action system is introduced.

## Readiness

Replay hardening is validated, but a real HOME session is not available.
Therefore Companion Session remains FOUNDATION_ONLY / NOT_VALIDATED.
Real Vision, Knowledge, and Overall remain unchanged.
