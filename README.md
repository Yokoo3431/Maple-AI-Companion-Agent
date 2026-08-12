# Maple AI Companion Agent

《冒险岛怀旧服》AI Companion Agent —— 基于成熟 Agent 架构思想的桌面辅助程序。

> 免责声明:本项目仅供学习与技术研究使用。使用第三方辅助可能违反游戏运营规则,由此产生的账号风险由使用者自行承担。项目默认不包含任何真实键鼠自动化行为(Phase 0 仅基础架构)。

## 功能规划(分阶段)

> 项目目标保持不变:**Maple Companion AI(理解与规划)+ 未来隔离虚拟输入(仅规划,不实现真实输入)**。

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Phase 0-7A | 基础架构 / 认知闭环(观察-决策-规划-确认-沙箱-反思-评估)/ 架构冻结 | ✅ 已完成 |
| Phase 7B-8F | 长期规划 / 环境理解 / 决策参考 / 人类对齐 | ✅ 已完成 |
| Phase 9A-9F | 记忆图谱 / 语义记忆 / Maple 上下文 / 领域知识 / 感知绑定 / 任务推理 | ✅ 已完成 |
| Phase 10A | Perception Fusion(多源感知融合,只读) | ✅ 已完成 |
| Phase 10B | L1 Reflex Foundation(HP/MP/UI 状态与危险事件快速感知) | 规划中 |
| Phase 10C | Virtual Keyboard Isolation Layer(未来隔离虚拟输入层) | 规划中 |

当前架构路线:

```text
Observation → Vision Evaluation → Knowledge → Decision → Planning
→ Human Confirmation → Permission Sandbox(MOCK_ONLY) → Reflection → Evaluation
→ Memory / Semantic Memory → Maple Context → Quest Reasoning → Perception Fusion
```

保持:`READ_ONLY_FIRST / DATA_DRIVEN / MOCK_EXECUTOR_ONLY`,禁止真实键鼠控制与输入注入。

## 快速开始(Phase 0)

需要 Python 3.11+。

**第一次使用(换电脑 / 新环境,一键恢复):**

```powershell
git clone <repo-url> Maple-Agent
cd Maple-Agent
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1
```

setup.ps1 会自动完成:检查 Python ≥ 3.11 → 创建/复用 .venv → 安装依赖 → 创建 logs/ sessions/ knowledge/ config/ 目录 → 从 .env.example 生成 .env → 运行 doctor 自检。然后双击 `launcher\Maple Agent 启动.bat` 即可启动。

**日常使用:**直接双击 `launcher\Maple Agent 启动.bat`。

**开发模式(可选):**

```powershell
python -m pytest                          # 运行测试
python -m maple_agent doctor              # 环境自检
python -m maple_agent start               # 启动 WebUI 控制台(http://127.0.0.1:8080)
python -m maple_agent test                # 运行测试套件
```

Phase 0 Release 说明见 [docs/06-phase0-release.md](docs/06-phase0-release.md)。

## 普通用户启动方式(Windows,无需命令行)

1. 双击 `launcher\Maple Agent 启动.bat`;
2. 启动器自动检查 Python 与项目 venv,缺失时弹出中文提示;
3. 服务就绪后自动打开浏览器 http://127.0.0.1:8080(默认 READY 状态,不会自动进入 RUNNING);
4. 启动记录保存在 `launcher\launcher.log`。

排查启动问题:双击 `launcher\Maple Agent 启动 Debug.bat`,窗口会保持打开(显示完整检查过程),便于查看错误。

## 外部审核包生成流程(External Review Package)

用于把当前项目打包,提交给其他 AI 模型做架构审核、安全审核与代码质量审核。

```powershell
# 方式一:命令行(在项目根目录执行)
powershell -ExecutionPolicy Bypass -File scripts\create_review_package.ps1

# 方式二:右键 scripts\create_review_package.ps1 -> 使用 PowerShell 运行
```

生成结果:

- `review_package/`:README_REVIEW.md、PROJECT_STATUS.md、ARCHITECTURE_SUMMARY.md、CHANGELOG.md、docs/、src/、tests/、requirements.txt、pyproject.toml;
- `Maple_AI_Companion_Agent_review_v0.1.0.zip`:可直接上传给外部 AI 审核。

排除内容(脚本自动校验,不进入包内):

- .venv、__pycache__、*.pyc、logs/、launcher.log、.env、review_package 自身、本地绝对路径;
- API Key 与用户配置不在包内(它们只存在于本机 .env)。

注意事项:每次运行会重新生成并覆盖 `review_package/` 与 zip;`PROJECT_STATUS.md` 会自动写入实测 pytest 数量。

## 架构

四层结构 + 横切基础设施:

```text
交付层:Web UI(FastAPI + Jinja2 + WebSocket)、Runtime Manager
核心层:Agent Controller、L1 Reflex、L2 Planner(LLM Provider)、Memory
适配层:Vision(截图/OpenCV/OCR Provider)、Input(Interface → Provider)、Game Window(只读)
数据层:Knowledge Base(versions/game_profile)、SQLite、Sessions/Replay、Logs
横切:Config、Logging、Event Bus(Reflex / Runtime / Error 事件)
```

详细设计见 [docs/README.md](docs/README.md)。

## 开发约定

- 每次提交附:修改文件列表 / Commit 建议 / 测试结果 / 运行日志 / 错误日志 / 下一步建议;
- 核心层只依赖抽象接口(Input / Vision / LLM Provider),禁止反向依赖;
- 禁止硬编码;API Key 与本地隐私只放 `.env`(不进 Git);
- Phase 0 禁止:自动移动/攻击/任务/购买、真实键鼠控制、内存读取。

## License

MIT
