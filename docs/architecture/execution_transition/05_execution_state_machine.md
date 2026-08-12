# Execution State Machine(vNext Draft)

## 1. 状态

```text
IDLE
AWAITING_CONFIRMATION
AUTHORIZED
READY
EXECUTING
WAITING_OBSERVATION
VERIFYING
RECOVERING
PAUSED
BLOCKED
ABORTED
COMPLETED
```

## 2. 合法 Transition(草案)

| From | To | 条件 |
| --- | --- | --- |
| IDLE | AWAITING_CONFIRMATION | 新请求进入 |
| AWAITING_CONFIRMATION | AUTHORIZED | 人工/策略批准 + token 有效 |
| AWAITING_CONFIRMATION | BLOCKED | 拒绝 / 过期 / 门控失败 |
| AUTHORIZED | READY | window binding + session + rate limit 通过 |
| READY | EXECUTING | 所有 gate 通过 |
| EXECUTING | WAITING_OBSERVATION | 动作发出,等待观察 |
| WAITING_OBSERVATION | VERIFYING | 获取 After 状态 |
| VERIFYING | COMPLETED | SUCCESS |
| VERIFYING | RECOVERING | FAILED / TIMEOUT / PARTIAL(policy) |
| VERIFYING | PAUSED | INCONCLUSIVE / 用户冲突 |
| VERIFYING | ABORTED | DEATH / Kill Switch |
| RECOVERING | AWAITING_CONFIRMATION | 恢复建议重新进入规划与门控 |
| PAUSED | READY | 恢复条件满足 |
| PAUSED | ABORTED | 用户终止 |
| BLOCKED | ABORTED | 门控失败终止 |
| ABORTED | IDLE | 会话清理 |
| COMPLETED | IDLE | 会话清理 |

## 3. 禁止 Transition

```text
BLOCKED → EXECUTING
UNAUTHORIZED → EXECUTING
RECOVERING → EXECUTING(必须重新经过规划 + Safety Gate + Permission)
```

## 4. Outcome Verification 强制循环

```text
Execute → Observe → Verify Outcome
SUCCESS      → next
PARTIAL      → policy
FAILED       → Recovery(重新门控)
TIMEOUT      → Recovery(重新门控)
INCONCLUSIVE → wait / observe
DEATH        → hard stop
```
