# Architecture Overview

> Phase 7-A Architecture Freeze(冻结版本: 1.0)

本文档记录 Phase 0 - 6-E 完整系统结构、模块职责与依赖方向。

## 系统链路

```
Observation
    ↓
Vision Evaluation
    ↓
Knowledge
    ↓
Decision
    ↓
Action Planning
    ↓
Human Confirmation
    ↓
Permission Sandbox(MOCK_ONLY)
    ↓
Reflection
    ↓
Evaluation Benchmark
```

统一编排入口:`AgentLoopOrchestrator`(`src/maple_agent/agent_loop/`)。

## 模块职责

| 模块 | 目录 | 核心职责 |
| --- | --- | --- |
| Observation | `observation/` | 输入观察标准化(截图 + OCR → ObservationFrame/State) |
| Vision Evaluation | `vision_eval/` | 视觉识别质量评估(OCR/Entity/Consistency/Risk) |
| Knowledge | `knowledge/` `knowledge_graph/` | 结构化知识库、检索、评估、导入 |
| Decision | `decision/` | 候选评分与选择(含 Experience bonus) |
| Action Planning | `action_plan/` | 决策展开为可执行规格契约 |
| Human Confirmation | `confirmation/` | 人工授权门控与 PermissionToken |
| Permission Sandbox | `executor_sandbox/` | 受限 Mock 执行沙箱(仅 MOCK_ONLY) |
| Reflection | `reflection/` | 执行后反思与重规划触发 |
| Experience Memory | `experience/` | 结构化经验库(非训练) |
| Evaluation | `evaluation/` | Agent 质量评估与 Benchmark |
| Agent Loop | `agent_loop/` | 统一闭环编排与 Trace |

## 依赖方向

单向分层,禁止反向依赖:

```
observation → vision_eval → decision → action_plan
                                     ↓
                              confirmation
                                     ↓
                              executor_sandbox
                                     ↓
                                reflection
                                     ↓
                                evaluation
                                     ↓
                               agent_loop(顶层)
```

## 禁止依赖关系

- `confirmation` 禁止依赖 `executor_sandbox`(门控层不知道执行沙箱)
- `executor_sandbox` 禁止依赖 `reflection`(沙箱不反思)
- `observation` / `decision` 禁止依赖执行与反思层
- 任何核心模块禁止反向依赖 `agent_loop`
- 全系统禁止循环依赖(已由 `test_architecture_contract.py` 校验)

## 禁止事项(全阶段)

禁止真实输入、自动控制、客户端修改、内存读取、Hook、DLL 注入。
详见 `safety_boundary.md`。
