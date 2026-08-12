# Controlled Execution Contract(vNext Draft)

> 本文件是 Future Contract Draft,不包含任何 executor / provider / input 调用。

## 1. 设计原则

- Contract 只定义「执行层上游」的语义请求与结果,不含 raw keyboard command;
- 所有输入必须是结构化动作意图,由未来 Controlled Input Adapter 翻译;
- 任何 gate 失败一律 `BLOCK`,禁止 fallback 绕过。

## 2. ControlledActionRequest

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| request_id | str | 请求唯一 ID |
| source_action_id | str | 关联 ActionProposalReference.action_id |
| action_type | str | OBSERVE/NAVIGATE/INTERACT/COMBAT/COLLECT/USE_ITEM 等 |
| target_reference | str | 目标参考(不生成点击坐标) |
| window_binding_id | str | 关联 GameWindowBindingReference |
| permission_token_id | str | 关联 v2 PermissionToken |
| safety_evaluation_id | str | 关联 SafetyEvaluationReference |
| expected_outcome_id | str | 关联 ExpectedOutcomeReference |
| created_at / expires_at | datetime | 请求生命周期 |

## 3. ControlledExecutionPolicy

全部 Policy 驱动,禁止 hard-code 分散实现:

```text
max_actions_per_second
max_actions_per_minute
max_continuous_execution_time
max_retry_count
max_failure_count
max_navigation_timeout
max_combat_duration
allowed_action_types
target_restriction
window_restriction
session_duration
```

## 4. ControlledExecutionResult

```text
execution_id
request_id
status(见 05_execution_state_machine.md)
window_binding_id
permission_token_id
observation_reference
outcome_reference(强制 ActionOutcomeReference)
audit
mode
```

## 5. ExecutionSessionReference

```text
session_id
window_binding_id
permission_token_ids[]
policy_id
started_at
expires_at
kill_switch_status
status
```

## 6. Mandatory Gates(未来执行必须全过)

```text
Action Proposal VALID
→ Safety Gate ALLOW
→ Human Confirmation / Policy Approval
→ PermissionToken VALID
→ Window Binding VALID
→ Execution Session ACTIVE
→ Rate Limit VALID
→ Kill Switch NOT ACTIVE
→ Controlled Executor
```

## 7. Kill Switch(三层)

```text
Software Kill Switch    全局配置级
Session Kill Switch     当前 session 级
User Emergency Stop     用户热键/UI 级(最高优先)
```

Kill Switch active 时:BLOCK ALL NEW ACTIONS,并终止活动 execution session。

## 8. Outcome Verification 强制循环

```text
Execute → Observe → Verify Outcome
SUCCESS      → next
PARTIAL      → policy
FAILED       → Recovery
TIMEOUT      → Recovery
INCONCLUSIVE → wait / observe
DEATH        → hard stop
```

禁止 `execute → immediately execute next action`。
