# Safety Architecture vNext

> Phase 13-E Safety Contract vNext Formalization(vNext Contract,不是 Runtime enablement)

## 1. Versioned Safety

```text
Safety Architecture v1(Phase 7-A frozen baseline)
  SAFETY_MODE = MOCK_ONLY

Safety Architecture vNext(本目录,仅契约)
  ExecutionMode: MOCK_ONLY / CONTROLLED_TEST / HUMAN_SUPERVISED
  默认 = MOCK_ONLY
```

## 2. 版本 ≠ 执行许可

```text
SafetyArchitectureVersion.VNEXT 存在 ≠ 已启用
version != execution permission
```

## 3. Machine-readable Models

契约模型位于 `src/maple_agent/safety_vnext/`:

```text
ExecutionMode
SafetyArchitectureVersion
ControlledExecutionPolicyReference
PermissionScopeV2 / PermissionPolicyV2
GameWindowBindingReference
ExecutionSessionReference
KillSwitchReference
RealVisionReadinessReference
KnowledgeReadinessReference
ControlledExecutionGateReference
ControlledExecutionReadinessReference
```

## 4. 当前状态

```text
default = MOCK_ONLY
enabled = false
Controlled Execution overall readiness = NOT_READY
```

无真实执行路径;任何输入 Provider 均未实现。
