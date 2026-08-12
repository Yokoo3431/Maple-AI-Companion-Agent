# Delivery Report Standard(固定格式)

所有 Codex 交付报告至少包含:

## 1. GitHub / Snapshot

Git clone 模式:

```text
branch
old commit
new commit
full hash
origin/main 同步状态
working tree 状态
```

ZIP 模式:

```text
snapshot baseline(source commit)
.git = unavailable
Git sync status = REQUIRED
```

## 2. Files Changed

新增 / 修改文件完整列表。

## 3. Architecture

本阶段架构说明与复用/扩展/禁止修改矩阵。

## 4. Implementation

关键实现说明与示例。

## 5. Tests(分别报告)

```text
targeted tests
full pytest
architecture contract
ruff
GitHub Actions(Python 3.11 / 3.12)
```

Local PASS ≠ CI PASS。若已 push,必须报告实际 CI 结果。

## 6. Readiness

```text
Real Vision
Knowledge
Overall Controlled Execution
```

不虚报。

## 7. Safety

```text
SAFETY_MODE = MOCK_ONLY
READ ONLY
NO INPUT
NO EXECUTION
```

## 8. Known Limitations

诚实列出未完成项 / 预留项 / 未验证项。

## 9. Next Phase Recommendation

基于真实 readiness 独立判断,禁止自动推荐 Input Provider。
