# Execution Transition Review

> Phase 13-D Controlled Execution Architecture Review(vNext Proposal)
> 本文件是 **vNext 提案**,不修改 Phase 7-A frozen baseline。

## 1. 现状链路(Phase 0 - 13-C,全部只读 / Mock)

```text
Observation
→ Planning(Quest / Navigation / Behavior)
→ Action Proposal
→ Safety Gate
→ Action Verification
→ Recovery
→ Mock Execution Only
```

当前 `SAFETY_MODE = "MOCK_ONLY"`(见 `src/maple_agent/architecture.py`),
`SAFETY_BOUNDARY.forbidden` 包含 `physical_input / automation_control / client_modification`。
Extension Guideline 明确:**真实输入层属于未授权方向,任何此类开发必须先经架构评审**。

## 2. 未来链路(受控执行 vNext Proposal)

```text
Observation
→ Planning
→ Action Proposal
→ Safety Gate
→ Human / Policy Gate
→ Controlled Input Adapter(未来)
→ Observation
→ Outcome Verification
→ Recovery
```

## 3. 模块处置矩阵

| 模块 | 处置 | 说明 |
| --- | --- | --- |
| Observation / Vision Runtime | 保留 | 继续作为唯一状态来源 |
| Quest / Navigation / Behavior / Action Proposal | 保留 | 上游只读规划链 |
| Safety Gate(13-A) | 保留 | 继续作为动作级安全审核 |
| Action Verification(13-C) | 保留 + 强制接入 | 未来每步执行后必须验证 |
| Recovery(13-B) | 保留 | RecoveryReference 仍不是 command,必须重新走 Planning→Proposal→Safety→Permission |
| Confirmation / PermissionToken | 复用 + 兼容扩展 | 见 `04_permission_and_confirmation_v2.md` |
| Executor Sandbox | 保留(MOCK_ONLY) | 作为受控执行契约的参考边界 |
| Controlled Input Adapter | 禁止修改/禁止实现 | 本阶段仅设计,不落地 |
| DecisionEngine / Runtime Core / AgentLoop stages | 禁止修改 | 冻结 |

## 4. 架构冲突声明

Phase 7-A 冻结 `MOCK_ONLY` 与「真实输入」存在**直接冲突**。
因此:

- 不能直接创建 `RealExecutor / VirtualKeyboardProvider / SendInputProvider / HIDProvider`;
- 任何真实输入实现都属于 Architecture Regression;
- 只能通过 **Versioned Safety Architecture**(vNext)在明确评审批准后分阶段演进。

## 5. Versioned Safety 概念

```text
MOCK_ONLY           当前生产默认(唯一可用模式)
CONTROLLED_TEST     未来实验模式(必须显式启动 + 全套门控)
HUMAN_SUPERVISED    未来连续受控操作(必须 session 级同意 + 边界权限)
```

本阶段只定义,不启用。默认保持 `MOCK_ONLY`;没有配置就绝不能进入后续模式。
禁止设计 `UNRESTRICTED` 或 `FULL_AUTO_NO_GUARD`。
