# Maple AI Companion Agent — 设计文档

本目录包含 Maple AI Companion Agent 的设计与发布文档。

| 文档 | 内容 |
| --- | --- |
| [01-system-design.md](01-system-design.md) | 系统设计说明:目标、边界、架构、模块设计、依赖关系、技术决策 |
| [02-architecture.md](02-architecture.md) | 架构图:系统上下文、分层、Agent Loop 时序、状态机、知识库流程 |
| [03-repo-structure.md](03-repo-structure.md) | GitHub 目录结构、文件职责、配置模板、忽略规则 |
| [04-phase0-plan.md](04-phase0-plan.md) | Phase 0 开发计划:里程碑、测试策略、验收标准 |
| [05-risks.md](05-risks.md) | 风险列表与缓解措施 |
| [06-phase0-release.md](06-phase0-release.md) | Phase 0 Release:已完成模块、测试结果、限制、Phase 1 计划 |

状态:✅ Phase 0 开发完成,Release Candidate 待审核(2026-08-06)

## 变更记录

- 2026-08-06:设计通过并进入 Phase 0。按审核意见微调:知识库改为 `knowledge/versions/game_profile` 目录方式(Phase 0 仅建 schema);Emergency Stop 默认热键改为 Ctrl + Alt + Pause;OCR 设计 Provider 接口(Windows OCR / PaddleOCR / Tesseract 可切换);Phase 0 增加只读窗口检测(禁止内存读取);增加 Event Bus 基础模块;LLM 改为 Provider 抽象(不绑定 DeepSeek)。
