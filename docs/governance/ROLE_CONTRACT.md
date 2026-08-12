# Role Contract

## IMPLEMENTER(Codex)

允许:

```text
modify files
run tests
commit / push
```

负责:按 DEVELOPMENT_WORKFLOW.md 完成阶段开发与交付。

## REVIEWER(Antigravity / 其他审核器)

默认只允许:

```text
read
inspect
test
compare
report
```

不修改 production implementation。

如用户明确要求 reviewer 修复:

```text
必须显式切换角色为 IMPLEMENTER 并记录。
```

## 角色分离原则

```text
IMPLEMENTER 不兼任自我审核结论;
REVIEWER 不兼任代码修改。
```
