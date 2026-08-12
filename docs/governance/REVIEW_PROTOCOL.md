# Review Protocol(独立审核角色)

> REVIEWER(Antigravity / 其他审核器)默认不得修改 production implementation。

## 固定流程

```text
Actual Repository / Commit(GIT 模式)或 LOCAL SNAPSHOT REVIEW(ZIP 模式)
↓ Actual Diff
↓ Architecture Contract(Phase 7-A + Safety vNext)
↓ Implementation 审核(读实际代码,不只读报告)
↓ Tests(本地可复跑)
↓ CI(如可访问 GitHub)
↓ README / Docs 一致性
↓ Original Goal / Route Drift 检查
↓ Independent Conclusion
```

## 审核结论(只能四选一)

```text
PASSED
PASSED WITH FOLLOW-UP
CONDITIONAL PASS
FAILED
```

必须明确 blocker。

## Reviewer 禁止

- 因 Delivery Report 写 PASSED 就自动 PASSED;
- 只读报告不读代码;
- 虚构 GitHub 状态;
- 默认修改 production code;
- 混淆 IMPLEMENTER 与 REVIEWER 角色。

## ZIP 模式声明

仅拿到 ZIP 时必须声明 **LOCAL SNAPSHOT REVIEW**;
不得宣称 GitHub remote verified,除非实际访问 GitHub。
