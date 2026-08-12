# Rate Limit / Action Budget Contract(vNext)

全部 Policy 驱动,禁止 hard-code 分散实现:

```text
max_actions_per_second
max_actions_per_minute
max_continuous_execution_time
max_retry_count
max_failure_count
max_navigation_timeout
max_combat_duration
```

## 规则

- 预算超限 → BLOCK / PAUSE;
- retry/failure 超限 → ABORT + 人工介入;
- 预算状态记录于 ExecutionSessionReference(action_count / failure_count / retry_count)。
