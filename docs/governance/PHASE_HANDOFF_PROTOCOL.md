# Phase Handoff Protocol

## 切换设备前的检查

```text
Handoff Status = READY 的前置条件:
- 无未提交文件(GIT 模式)
- 全部测试通过
- 本地已 push 且 CI green(GIT 模式)
- .project/HANDOFF.md 已更新
```

若存在未提交文件 / 测试失败 / CI 失败 / 本地领先未推送:

```text
SYNC_REQUIRED 或 BLOCKED
```

## Handoff Status 定义

```text
READY
IN_PROGRESS
BLOCKED
SYNC_REQUIRED
REVIEW_REQUIRED
```

## 交接内容

新机器上的 Agent 通过以下文件理解项目(不依赖聊天记录):

```text
AGENTS.md
.project/CURRENT_STATE.yaml
.project/BASELINE.json
.project/HANDOFF.md
README.md
docs/architecture/*
docs/governance/*
```

## Phase Prompt 契约

未来的 Phase Prompt 不需要重复全部通用规则。Phase Prompt 应主要包含:

```text
phase objective
scope
architecture-specific constraints
implementation requirements
acceptance criteria
```

通用项(preflight / testing / Git / CI / reporting / role / review)
一律引用 Repository Governance,避免规则漂移。
