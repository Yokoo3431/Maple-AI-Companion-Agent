# Execution Session Contract(vNext)

## ExecutionSessionReference

```text
session_id
architecture_version
execution_mode
window_binding_id
policy_id
permission_token_ids
started_at
expires_at
kill_switch_state
action_count
failure_count
retry_count
status
```

## 规则

- session 必须 ACTIVE 才能通过 gate;
- 关联 policy / binding / permission;
- 记录 action/failure/retry 预算消耗;
- Kill Switch ACTIVE 时终止活动 session。

仅为 Reference,不构成执行许可。
