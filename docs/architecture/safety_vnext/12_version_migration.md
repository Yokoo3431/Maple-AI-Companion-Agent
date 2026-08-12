# Version Migration(v1 → vNext)

## 原则

- Phase 7-A v1 文档保持 frozen baseline,禁止重写历史语义;
- vNext 全部内容位于独立目录 `docs/architecture/safety_vnext/` 与 `src/maple_agent/safety_vnext/`;
- 只有后续 Architecture Review 明确批准新 Safety Contract Version,才能进入原型阶段。

## 迁移前置(Gate)

```text
Safety vNext(架构批准)
Real Vision Validation Gate
Knowledge Quality Gate
Permission v2
Window Binding
Session
Kill Switch
Rate Limit
Outcome Verification
Threat Mitigation
Explicit Enable(配置显式开启,禁止默认)
```

## 当前状态

```text
default mode = MOCK_ONLY
overall Controlled Execution readiness = NOT_READY
ADR-001 = ACCEPTED(仅批准架构方向,不授权 live input)
```
