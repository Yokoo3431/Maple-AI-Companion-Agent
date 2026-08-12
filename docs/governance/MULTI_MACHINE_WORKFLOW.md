# Multi-machine Workflow(Office → Home → Office)

> 默认 **ONE ACTIVE MACHINE AT A TIME**:切换设备前,前一台必须 finish/stop cleanly、
> 通过测试、commit/push(GIT 模式)、更新 handoff。

## A. GitHub Desktop 模式(推荐)

首次:
1. 安装 GitHub Desktop;
2. Clone repository,选择本地文件夹;
3. 打开 Codex 并指向该文件夹。

每次从另一台电脑回来:
1. 打开 GitHub Desktop;
2. 选择 Maple repository;
3. 点击 **Fetch origin**;
4. 如显示 **Pull**,点击 **Pull origin**;
5. 确认无未提交修改;
6. 再打开 Codex。

开发结束:
1. Codex 完成 tests;
2. GitHub Desktop 查看 **Changes**;
3. **Commit to main**;
4. **Push origin**;
5. 检查 GitHub Actions。

> 用户不需要手敲 git pull。

## B. ZIP Snapshot 模式(兼容)

1. GitHub 打开 repository → Code → Download ZIP;
2. 解压到新的版本文件夹;
3. Codex 打开该文件夹并读取:
   - `AGENTS.md`
   - `.project/BASELINE.json`
   - `.project/CURRENT_STATE.yaml`

ZIP 适合:read / develop / local test / review。
ZIP 不适合:merge / commit history / push / conflict handling。

检测到 `.git` 缺失时必须提示 **SNAPSHOT MODE**,
不执行假的 `git status / git commit / git push`。
