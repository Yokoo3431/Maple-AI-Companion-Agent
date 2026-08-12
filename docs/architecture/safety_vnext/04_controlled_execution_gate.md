# Controlled Execution Gate(vNext)

## 1. Gate Mandatory Order(正式冻结)

```text
Action Proposal VALID
↓
Safety Gate ALLOW
↓
Confirmation APPROVED
↓
Permission VALID
↓
Window Binding VALID
↓
Execution Session VALID
↓
Policy VALID
↓
Rate / Budget VALID
↓
Kill Switch CLEAR
↓
Expected Outcome PRESENT
↓
ELIGIBLE_REFERENCE
```

任何一个失败 → `BLOCKED_REFERENCE`;禁止 fallback 绕过。

## 2. ControlledExecutionGateReference

```text
gate_id
verdict(ELIGIBLE_REFERENCE / WARNING_REFERENCE / BLOCKED_REFERENCE)
blocked_reasons
warnings
action_reference / policy_id / session_id / window_binding_id / expected_outcome_id
```

## 3. 语义澄清

```text
ELIGIBLE_REFERENCE ≠ 真实执行
只表示 future execution prerequisites satisfied
```

Recovery 重新进入门控时必须重走完整 gate order。
