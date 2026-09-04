# Phase 13-U.1i — Existing Antigravity Route Recovery

## Boundary

This phase recovers an existing read-only visual route and validates one-image
transport. It does not add a second vision pipeline, resolver, semantic-state
model, planner, executor, input provider, or automation path. The safety state
remains `SAFETY_MODE=MOCK_ONLY`.

## Route findings

The machine exposes an existing `agy` CLI (version 1.1.24) and its model listing
includes `gemini-3.7-flash-low`. The CLI does not expose a direct image argument;
its supported local-image shape is a bounded working directory (`--add-dir`), a
prompt referring to the image file, and `--json-schema` for structured output.
The project U.1h provider expects a command containing `{image_path}` and reads a
`VisualSemanticResponse` directly, so the shape requires a launcher rather than
a second provider contract.

## Thin compatibility launcher

`scripts/antigravity_visual_bridge.py` receives the existing provider's image
path and request metadata, invokes the existing `agy` route with `--sandbox`,
`--mode plan`, and `--disable-slash-commands`, and passes the existing
`VisualSemanticResponse.model_json_schema()` to `--json-schema`. It consumes only
agy's `structured_output`; the human-facing response and any tool metadata are
discarded. The validated result is returned to
`AntigravityVisualSemanticProvider`, which remains the only project provider
boundary.

An operator may configure the existing adapter for this route in the current
process only, for example:

```text
MAPLE_ANTIGRAVITY_COMMAND=.venv\\Scripts\\python.exe scripts\\antigravity_visual_bridge.py {image_path} {model}
MAPLE_ANTIGRAVITY_MODEL=gemini-3.7-flash-low
```

No global configuration, credential, OpenClaw/Hermes setting, or repository
secret is required or changed by this phase.

## Capability evidence

The route successfully inspected a synthetic local PNG and returned structured
MAP/HP/MP values. A strict JSON Schema probe also returned a schema-constrained
object. The synthetic result is capability evidence only; it is not Maple
semantic evidence. WSL did not expose an `agy` command, and no separate
`antigravity` or `gemini` command was found in the Windows PATH.

## Real Maple boundary

The existing `WindowsWindowDiscovery` did not find a visible matching Maple
window during this run. Consequently no real Maple image was captured or sent,
and no real semantic closure is claimed. The next bounded operation is a
single-image smoke after the user manually makes the Maple client visible in
the same accessible desktop/session.
