# Maple AI Companion Agent — AI Agent 统一入口

> 本文件是仓库的 **Single Source of Truth** 入口。所有 AI Agent(Codex / Antigravity / 审核器)
> 开工前必须按顺序阅读下列内容,不得依赖历史聊天记录。

## 1. Project Identity

- **项目**:MapleStory 怀旧服 / 私服 AI Companion Agent(非通用 Computer-use Agent)
- **长期目标**:感知 → 知识 → 规划 → 记忆 → 反思 → 导航 → 任务推理 →
  未来隔离式受控输入(当前 **MOCK_ONLY**,未授权真实输入)
- **仓库**:https://github.com/Yokoo3431/Maple-AI-Companion-Agent

## 2. Mandatory Reading Order

开工(实现 / 审核 / 交接)前必须按顺序读取:

1. `AGENTS.md`(本文件)
2. `.project/CURRENT_STATE.yaml`(机器可读项目状态)
3. `README.md`(阶段表与路线)
4. `docs/01-system-design.md`(系统设计)
5. `docs/architecture/*` 与 `docs/architecture/safety_vnext/*`(冻结契约)
6. 与当前 Phase 相关的 `src/maple_agent/*` 模块
7. 与当前 Phase 相关的 `tests/unit/*`
8. 治理规范:`docs/governance/*`

## 3. Roles

- **IMPLEMENTER(Codex)**:可修改文件、运行测试、commit/push。
- **REVIEWER(Antigravity / 其他审核器)**:默认只读、检查、测试、对比、报告;
  不直接修改 production implementation;如需修复必须显式切换为 IMPLEMENTER 并记录。

## 4. Architecture Priority(冲突时)

```text
Frozen Architecture Contract(Phase 7-A)
> Safety Contract
> Repository Governance
> Current Phase Prompt
> Agent assumption
```

Current Phase Prompt 可按正式 Architecture Migration 流程扩展**非冻结区域**。

## 5. Safety(当前)

```text
SAFETY_MODE = MOCK_ONLY
READ ONLY
NO INPUT
NO EXECUTION
NO AUTOMATION
```

## 6. Git / Snapshot 判断

开工第一步:判断当前目录是否为 Git clone。

- `.git/` 存在 → **GIT 模式**:可 pull / commit / push / 校验 HEAD。
- `.git/` 不存在(GitHub Download ZIP)→ **SNAPSHOT 模式**:
  可读取 / 开发 / 本地测试,但**禁止伪报 commit / push / CI**;交付报告必须标注
  `GIT_SYNC_REQUIRED`,并读取 `.project/BASELINE.json` 识别来源 commit。

## 7. 工作完成后的 GitHub 同步(必须执行)

- 每次完成任务 / 里程碑、提交代码后,**必须**同步推送到 `origin/main`;
- 提交信息附修改文件列表、测试结果、日志、下一步建议;
- 敏感信息(API Key、`.env`、日志、本地绝对路径)禁止进入仓库;
- 完成后验证:`git ls-remote origin main` 与本地 HEAD 一致。
