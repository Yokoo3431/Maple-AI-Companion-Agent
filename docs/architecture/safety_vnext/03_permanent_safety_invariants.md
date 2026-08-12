# Permanent Safety Invariants

> 跨版本永久安全红线。与「Current Mode Restriction」区分:
> Current Restriction 是当前 v1 的绝对约束;Permanent Invariant 是未来任何版本都不可突破。

## Current v1 Restriction(Phase 7-A / 当前 main)

```text
MOCK_ONLY
NO REAL INPUT
NO AUTOMATION
NO VIRTUAL HID
NO SENDINPUT
```

## Permanent Safety Invariants(未来任何 Safety 版本)

```text
UNAUTHORIZED_EXECUTION                → 永久禁止
SAFETY_GATE_BYPASS                    → 永久禁止
PERMISSION_BYPASS                     → 永久禁止
CONFIRMATION_BYPASS                   → 永久禁止
WRONG_WINDOW_EXECUTION                → 永久禁止
RECOVERY_DIRECT_EXECUTION             → 永久禁止
EXECUTION_WITHOUT_OUTCOME_VERIFICATION → 永久禁止
EXECUTION_WITHOUT_KILL_SWITCH         → 永久禁止
UNBOUNDED_ACTION_RATE                 → 永久禁止
UNBOUNDED_RETRY                       → 永久禁止
STALE_PERMISSION_EXECUTION            → 永久禁止
DEFAULT_LIVE_EXECUTION                → 永久禁止
UNRESTRICTED_MODE                     → 永久禁止
FULL_AUTO_NO_GUARD                    → 永久禁止
```

## Human Input Priority(永久)

```text
Human Input Priority > Agent Input
检测用户冲突 → PAUSE / YIELD,禁止抢占
```
