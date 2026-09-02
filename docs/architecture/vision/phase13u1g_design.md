# Phase 13-U.1g — HP/MP Live Signal Recalibration

## Boundary

Phase 13-U.1g is a bounded, read-only audit of the existing HP/MP visual path. It does not add a vision pipeline, a new OCR stack, a new player-state model, a resolver, a planner, or an execution capability. Map template acquisition and external VLM integration remain out of scope.

The safety boundary remains `SAFETY_MODE=MOCK_ONLY`, `READ ONLY`, `NO INPUT`, and `NO EXECUTION`.

## Existing contract

The Phase 13-I.4 numeric path reads current/max HP or MP from a dedicated HUD ROI, uses the existing Tesseract numeric extractor with bounded preprocessing and digit/ slash filtering, parses a current/max pair, and emits a normalized ratio. HP/MP are player-state evidence, not knowledge entities.

The formal candidate contract is now explicit: HP/MP visual candidates use `NORMALIZED_RATIO` and must parse to a value in `[0, 1]`. Ambiguous values such as `472/472` are not accepted as ratios. The existing `PlayerStateReference` and `CurrentObservation.player_status` path remains the sole consumer path.

## Bounded fixes

- Treat a directory-valued `TESSERACT_CMD` as invalid and fall back to a real executable discovered on PATH or at the standard Windows installation path.
- Resolve configured tessdata directories whether trained data is directly inside the directory or inside its `tessdata` child.
- Use the existing profile-aware pixel ROI transform and dedicated numeric HP/MP ROIs in the real-vision validation script.
- Expose aggregate candidate/parseable counters without recording OCR text or image data.
- Define HP/MP value semantics in the existing visual candidate model and add deterministic contract tests.

## Real diagnostic result

The 149.46-second Notebook diagnostic captured 30/30 frames and generated 30 snapshots without exceptions. The OCR backend was available, but HP and MP each had 30 invocations, zero digit candidates, zero parseable candidates, and zero player-state references. The bounded local ROI probe also produced zero candidates across the existing numeric ROI variants. No human-verifiable candidate was therefore available; ground truth remains `UNKNOWN_GT`.

This establishes a concrete signal/layout gap rather than an OCR executable startup failure. The evidence does not yet distinguish a client-layout/profile mismatch from a frame in which the numeric HUD was not visibly exposed. It is therefore recorded as `GAP_IDENTIFIED`, with `REAL_SEMANTIC_EVIDENCE=NOT_CLOSED`.

## Readiness and next investigation

Real Vision and Knowledge remain `FOUNDATION_ONLY`; Companion Session remains `REAL_SESSION_VALIDATED_LEVEL_A`; Overall remains `NOT_READY`. The separate `MAP_TEMPLATE_ASSET_GAP` is unchanged. The next bounded investigation should obtain user-confirmed visibility/layout information for the HP/MP HUD and then compare the existing profile ROI against that evidence. No fake normalization, knowledge-based observation, or VLM call is permitted.

The aggregate evidence is recorded in `phase13u1g_hpmp_signal_report.json`. Temporary real frames and ROI samples were local-only and were removed after analysis.
