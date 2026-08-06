# Maple AI Companion Agent

《冒险岛怀旧服》AI Companion Agent —— 基于成熟 Agent 架构思想的桌面辅助程序。

> 免责声明:本项目仅供学习与技术研究使用。使用第三方辅助可能违反游戏运营规则,由此产生的账号风险由使用者自行承担。项目默认不包含任何真实键鼠自动化行为(Phase 0 仅基础架构)。

## 功能规划(分阶段)

| 阶段 | 内容 | 状态 |
| --- | --- | --- |
| Phase 0 | 基础架构:配置 / 日志 / Event Bus / Runtime / WebUI / Agent 状态机框架 / 知识库框架 / 只读窗口检测 | 开发中(M0 进行中) |
| Phase 1 | Vision + OCR + Input Provider + Agent 状态机 | 规划中 |
| Phase 2 | 知识库 + 路线 + 补给 | 规划中 |
| Phase 3 | 任务 Agent + Human Teaching | 规划中 |

## 快速开始(Phase 0)

需要 Python 3.11+。

```powershell
git clone <repo-url> Maple-Agent
cd Maple-Agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt      # 开发环境
Copy-Item .env.example .env
python -m pytest                          # 运行测试
python -m maple_agent doctor              # 环境自检
python -m maple_agent start               # 启动 WebUI 控制台(http://127.0.0.1:8080)
python -m maple_agent test                # 运行测试套件
```

也可以直接运行 `scripts/setup.ps1` 一键安装。

Phase 0 Release 说明见 [docs/06-phase0-release.md](docs/06-phase0-release.md)。

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
