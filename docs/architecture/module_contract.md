# Module Contract

> Phase 7-A Architecture Freeze(冻结版本: 1.0)

定义所有核心模块职责边界。每个模块:负责什么、禁止什么。

## Observation(`observation/`)

- 负责: 输入观察标准化(截图/图像 → ObservationFrame)、状态识别(地图/实体)、观察校验
- 禁止: 决策、执行、输入控制

## Vision Evaluation(`vision_eval/`)

- 负责: 视觉识别质量评估(OCR/Entity/Consistency/Confidence)、风险等级、评测集
- 禁止: 提升模型能力、修改观察结果、执行

## Knowledge(`knowledge/`, `knowledge_graph/`, `knowledge/retrieval/` 等)

- 负责: 结构化知识加载、图谱、检索排序、评估、导入
- 禁止: 解析游戏客户端文件(WZ)、内存读取、自动任务

## Decision(`decision/`)

- 负责: 候选评分(目标对齐 + 知识置信 + 经验加成 - 风险)、选择最优
- 禁止: 执行、计划生成、输入

## Action Planning(`action_plan/`)

- 负责: 决策展开为结构化步骤、前置条件、成功标准、校验
- 禁止: 执行、物理动作语义

## Human Confirmation(`confirmation/`)

- 负责: 人工确认请求、批准/拒绝/过期、PermissionToken 签发
- 禁止: 调用 Executor、自动批准(除非显式模拟)、真实执行

## Permission Sandbox(`executor_sandbox/`)

- 负责: PermissionToken 验证、策略校验、Mock 执行契约、审计 Replay
- 禁止: 真实输入、调用 Executor / Input Layer、非 MOCK_ONLY 模式

## Reflection(`reflection/`)

- 负责: 执行结果反思、失败类型分析、重规划触发、反思记忆
- 禁止: 执行、自动纠错动作

## Experience Memory(`experience/`)

- 负责: 结构化经验记录、相似性检索、经验评估、决策加分
- 禁止: 训练模型、真实执行

## Evaluation(`evaluation/`)

- 负责: Trace 分析、质量评分、Benchmark、评估报告
- 禁止: 改变 Agent 行为、执行

## Agent Loop(`agent_loop/`)

- 负责: 统一闭环编排(观察→评估→决策→计划→确认→沙箱→反思→评估)、统一 Trace
- 禁止: 重实现已有模块、跳过确认门控、非 MOCK_ONLY

## 通用约束

- 所有模块输入输出必须为强类型模型(禁止裸 dict 作为核心契约)
- 所有模块必须支持 Replay
- 所有模块不得破坏既有安全边界
