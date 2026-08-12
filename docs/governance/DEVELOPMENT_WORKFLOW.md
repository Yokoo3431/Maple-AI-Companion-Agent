# Development Workflow(IMPLEMENTER 固定流程)

> Codex 默认角色为 IMPLEMENTER。每个 Phase 按以下固定流程执行。

```text
Repository Preflight(判断 GIT / SNAPSHOT)
↓ Read Governance(docs/governance/*)
↓ Read Architecture(AGENTS.md 阅读顺序)
↓ Verify Baseline(.project/CURRENT_STATE.yaml + BASELINE.json)
↓ Inspect Existing Implementation(相关模块与 tests)
↓ Implement
↓ Targeted Tests
↓ Full pytest
↓ Architecture Contract(pytest tests/unit/test_architecture_contract.py)
↓ ruff(check src tests scripts)
↓ Git Status
↓ Commit
↓ Push origin/main(GIT 模式)
↓ GitHub Actions(Python 3.11 / 3.12 green)
↓ Delivery Report(按 DELIVERY_REPORT_STANDARD.md)
```

## SNAPSHOT 模式(.git 缺失)

- 允许:读取 / 开发 / 本地测试;
- 禁止:伪报 commit、push、CI;
- 完成开发与本地 tests 后:
  - 更新 `.project/HANDOFF.md`;
  - 交付报告标注 `GIT_SYNC_REQUIRED`。

## 质量门禁

```text
pytest -q                    全部通过
pytest -q tests/unit/test_architecture_contract.py  通过
ruff check src tests scripts 通过
```

禁止 skip 失败用例掩盖问题;禁止放宽 Architecture Contract。
