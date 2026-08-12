# ADR-001: Controlled Execution Transition

| 项 | 内容 |
| --- | --- |
| 状态 | **ACCEPTED**(仅批准架构方向;不等于 LIVE EXECUTION APPROVED) |
| 日期 | 2026-08-12 |
| 关联 | Phase 13-D Controlled Execution Architecture Review |

## Context

当前系统 `SAFETY_MODE = MOCK_ONLY`,已具备完整的只读认知链
(Observation → Planning → Action Proposal → Safety Gate → Verification → Recovery)。
长期目标需要受控输入,但 Phase 7-A 冻结边界明确禁止 Physical Input /
Automation Control,Extension Guideline 要求真实输入必须先经架构评审。
因此需要一条**不破坏现有安全模型**的演进路径。

## Decision

采用 **Versioned Safety Architecture + 分阶段迁移**:

```text
MOCK_ONLY(现状)
→ CONTROLLED_TEST(显式启动 + 全套门控 + 最小原型)
→ HUMAN_SUPERVISED(session 级同意 + 边界权限)
```

本阶段只产出架构文档与 Contract Draft,**不实现任何输入**;
只有在未来 Architecture Review 明确批准新 Safety Contract Version 后才可进入原型。

## Alternatives

| 方案 | 结论 |
| --- | --- |
| 永久 MOCK_ONLY | 不满足长期目标,保留为安全基线 |
| SendInput 直接前台模拟 | 破坏隔离目标、高误发风险,否决为首选 |
| Virtual HID | 隔离性好但驱动/权限成本高,列为候选(需实测客户端兼容) |
| VM / isolated desktop | 隔离性最高但性能/反作弊/复杂度风险高,列为最后选项 |
| Controlled Provider(本 ADR) | 采用:Contract First + 门控 + 分阶段 |

## Consequences

- 安全:MOCK_ONLY 边界保持不变,任何演进必须先评审;
- 工程:先契约后实现,可测试、可审计、可回退;
- 用户体验:以 Human Input Priority > Agent Input 为原则,冲突即 PAUSE/YIELD;
- 风险:Windows 无官方完全隔离输入通道,「第二套隔离通道」只能尽量接近,必须实测。

## Status

**ACCEPTED(architecture direction)**。经 Phase 13-E Safety Contract vNext Formalization
完成契约一致性审查后,批准本 ADR 的演进架构方向。

> **ACCEPTED architecture direction ≠ LIVE EXECUTION APPROVED**
>
> 仅批准受控执行演进架构;不批准任何真实输入 / 执行实现。
> Runtime 仍为 `SAFETY_MODE = MOCK_ONLY`,整体 readiness 仍为 `NOT_READY`。
