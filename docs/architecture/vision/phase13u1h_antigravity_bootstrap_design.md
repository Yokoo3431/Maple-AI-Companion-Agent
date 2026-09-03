# Phase 13-U.1h — Antigravity Visual Bootstrap

## Scope and decision boundary

This phase evaluates a bounded, read-only visual bootstrap path. It does not make
Real Vision production-ready, add a planner, or add any input/execution capability.
The existing local CV/OCR path remains the preferred cheap path. A configured
Antigravity-compatible CLI is only a low-frequency fallback when local evidence is
unknown, stale, or gated by a scene/ROI change.

The safety contract remains `SAFETY_MODE=MOCK_ONLY`, `READ ONLY`, `NO INPUT`,
`NO EXECUTION`, and `NO AUTOMATION`.

## Reference study

The following public repositories were reviewed for architecture ideas only; no
third-party code, model weights, screenshots, or game data were copied:

- [Project Aegis](https://github.com/ninja-otaku/Project_Aegis): frame-diff gating,
  local preprocessing, provider isolation, and structured analysis are useful
  patterns. Its network intake, TTS, and unrestricted provider output are outside
  this project's boundary. The repository declares MIT.
- [4x-game-agent](https://github.com/sonpiaz/4x-game-agent): cheap local perception
  with low-frequency LLM fallback is a useful cost/latency pattern. Its ADB,
  tap/swipe, workflow, and bot execution layers are explicitly excluded. The
  repository declares MIT.
- [Cradle](https://github.com/BAAI-Agents/Cradle): screenshot-based observation and
  provider/process separation are relevant, but its stated computer-control output
  includes keyboard/mouse operations. Only the observation boundary is relevant
  here; the repository declares MIT.
- [AiGameCompanion](https://github.com/Wintersta7e/AiGameCompanion): isolated
  Windows.Graphics.Capture and bring-your-own-provider boundaries are useful. Its
  overlay focus/hotkey behavior and interactive UI are excluded. The repository
  declares MIT.

## Existing contract reuse

The adapter implements the existing `VisualSemanticProvider.observe()` protocol and
returns the existing `VisualSemanticResponse`. Valid candidates still enter
`ExistingVisionObservationAdapter`, then the existing entity-evidence or
`PlayerStateReference` path. No resolver, semantic-state model, or knowledge graph
is duplicated.

## Image transport and privacy

`EphemeralFrameStore` stores caller-supplied image bytes in a temporary local
directory and returns an opaque token. The provider resolves that token only for
the subprocess call, passes the temporary path through an explicit `{image_path}`
command placeholder, and deletes the image in `finally`. The request metadata and
transport metrics contain no pixel data, base64, absolute path, or raw provider
transcript. Callers should register the smallest safe ROI; full-frame transport is
not the default privacy policy.

The environment-based provider configuration is opt-in through
`MAPLE_ANTIGRAVITY_COMMAND` and `MAPLE_ANTIGRAVITY_MODEL`. Commands are executed
without a shell. A command is unavailable unless it is resolvable and explicitly
contains `{image_path}`; this prevents guessing an undocumented CLI interface.

## Strict output and HP/MP semantics

Provider stdout must be JSON accepted by the existing response schema. Extra fields,
invalid JSON, nonzero exit, timeout, frame-token mismatch, and unsupported image
transport fail closed. The prompt requests only visible facts (`MAP`, `HP`, `MP`,
and `UI_TEXT`) and forbids inference, recommendations, commands, or actions.

HP/MP candidates use the existing normalized-ratio player-state contract. When a
provider can read a current/max pair, the candidate may additionally carry
`observed_current`, `observed_max`, and `normalized_ratio`; these values must agree.
A current-only reading is rejected because no ratio may be guessed. HP/MP never
become knowledge entities.

## Multi-frame confirmation

`VisualSemanticAgreementGate` compares validated candidate signatures across
independent responses. It can report `CONSISTENT`, `CONFLICT`, or
`INSUFFICIENT_DATA`; it never raises confidence. A consistent result reports the
weakest input confidence as a bound, while conflicts remain conflicts.

## Local/VLM scheduling

The existing `FrameChangeDetector`, `VisionScheduler`, and `VisualSemanticGate`
remain responsible for deciding when perception work is worthwhile. No per-frame
VLM loop is introduced. A real provider call is impossible until a user-configured
CLI with documented image input is present. CI uses the deterministic subprocess
fixture only and never requires credentials, a client, or external network access.

## Current feasibility result

On this development machine, `antigravity` and `gemini` are not available on PATH.
Google Cloud CLI is present as a separate tool but is not a validated image-input
Antigravity/Gemini route; its version command could not read its own user config in
this environment. No authentication state or credentials were inspected or
changed. Therefore no real image was sent and no real VLM candidate was produced.

The phase result remains `INSUFFICIENT_EVIDENCE`,
`REAL_SEMANTIC_EVIDENCE=NOT_CLOSED`, and `Real Vision=FOUNDATION_ONLY`.
The existing Map `MAP_TEMPLATE_ASSET_GAP` and local HP/MP signal gap remain
unchanged.
