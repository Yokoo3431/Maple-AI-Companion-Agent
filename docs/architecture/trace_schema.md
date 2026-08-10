# Trace Schema

> Phase 7-A Architecture Freeze(冻结版本: 1.0)

## 统一闭环 Trace

文件:`sessions/<trace_id>/agent_loop_trace.json`

Schema 版本:`1.0`

```json
{
  "schema_version": "1.0",
  "trace_id": "",
  "agent_version": "0.1.0",
  "stages": [
    {"stage": "observation", "status": "completed"},
    {"stage": "vision_evaluation", "status": "LOW"},
    {"stage": "decision", "status": "completed"},
    {"stage": "planning", "status": "completed"},
    {"stage": "confirmation", "status": "APPROVED"},
    {"stage": "sandbox", "status": "MOCK_ONLY"},
    {"stage": "reflection", "status": "completed"},
    {"stage": "evaluation", "status": "completed"}
  ],
  "final_status": "COMPLETED"
}
```

## 字段契约

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| schema_version | str | 是 | Trace Schema 版本,未来升级保持兼容 |
| trace_id | str | 是 | 一次认知循环唯一 ID |
| agent_version | str | 否 | Agent 版本,记录产生 Trace 的代码版本 |
| stages | list | 是 | 阶段记录(有序) |
| final_status | str | 是 | CREATED/OBSERVING/.../COMPLETED/FAILED/BLOCKED |

## 阶段顺序契约

```
observation → vision_evaluation → knowledge → decision → planning
→ confirmation → sandbox → reflection → evaluation
```

禁止跳过 Human Confirmation;禁止 Sandbox 无 PermissionToken。

## 版本升级规则

- 新增字段必须带默认值(向前兼容)
- 禁止删除既有字段
- 语义变化必须升 `schema_version`
- 旧版本 Trace 必须可被新版本读取

## 各阶段独立 Trace

同一 `trace_id` 目录下保留各阶段独立 Trace,便于逐段审计:

- `observation_trace.json`
- `vision_evaluation.json`
- `decision_trace.json`
- `action_plan_trace.json`
- `confirmation_trace.json`
- `sandbox_execution.json`
- `reflection_trace.json`
- `evaluation_report.json`
- `agent_loop_trace.json`(统一入口)
