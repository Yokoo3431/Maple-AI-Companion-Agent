# Recovery Re-entry Contract

## 正式定义

```text
RecoveryReference 永远不是 command
```

## Recovery 正确路径

```text
Recovery
↓
Planning
↓
Behavior
↓
Action Proposal
↓
Safety Gate
↓
Confirmation
↓
Permission
↓
Gate(ELIGIBLE_REFERENCE)
```

## 禁止

```text
Recovery → Executor
```

Recovery 任何情况下都不得绕过 Safety Gate / Confirmation / Permission 直接控制输入。
