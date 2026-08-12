# Outcome Verification Requirement(永久)

## 强制循环

```text
Future Execute
↓
Observe
↓
Verify
```

禁止:

```text
Execute → Execute → Execute
```

必须:

```text
Execute → Observation → Action Outcome Verification
SUCCESS      → next candidate
PARTIAL_SUCCESS → policy/replan
FAILED       → Recovery(重新门控)
TIMEOUT      → Recovery(重新门控)
INCONCLUSIVE → WAIT / OBSERVE
DEATH        → HARD STOP
```

Gate 要求 `Expected Outcome PRESENT`;缺省即 BLOCKED。
