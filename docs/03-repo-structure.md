# Maple AI Companion Agent — GitHub 目录结构

## 1. 目录总览

```text
Maple-Agent/
├── README.md                    # 项目说明、快速开始、免责声明
├── LICENSE
├── .gitignore                   # 排除 .env、日志、会话、数据库、缓存
├── .env.example                 # 配置模板(不含密钥)
├── requirements.txt             # Phase 0 核心依赖
├── requirements-vision.txt      # 视觉依赖(Phase 1 按需安装)
├── requirements-dev.txt         # 开发/测试依赖
├── pyproject.toml               # 打包与工具配置(pytest / ruff 等)
├── Makefile                     # 常用命令: install / test / run / lint
│
├── src/
│   └── maple_agent/             # 主包,核心代码全部在此
│       ├── __init__.py
│       ├── __main__.py          #   python -m maple_agent 入口
│       ├── main.py              #   入口:CLI 委托
│       ├── bootstrap.py         #   装配:Config→Logging→EventBus→Providers→Runtime→WebUI
│       ├── cli.py               #   CLI:start / doctor / test
│       ├── config/              # 配置系统(pydantic-settings)
│       │   ├── settings.py      #   Settings 模型与加载
│       │   └── defaults.yaml    #   默认值
│       ├── logging_setup.py     # 日志基础设施:分模块文件 + trace_id/correlation_id + 轮转
│       ├── models/              # 领域模型(Pydantic): GameState、Action、Plan、Event
│       ├── providers/           # Provider 抽象层(Phase 0 仅接口 + Mock)
│       │   ├── base.py          #   BaseProvider:生命周期 + trace + 日志 + Event
│       │   ├── llm.py           #   LLMProvider + MockLLMProvider
│       │   ├── ocr.py           #   OCRProvider + MockOCRProvider
│       │   ├── vision.py        #   VisionProvider + MockVisionProvider
│       │   └── storage.py       #   StorageProvider + MockStorageProvider
│       ├── events/              # 进程内事件总线
│       │   ├── bus.py           #   异步优先级队列 + 发布/订阅
│       │   └── types.py         #   强类型 Event / EventType / Priority
│       ├── runtime/             # Runtime 状态机 + 生命周期管理
│       │   ├── states.py        #   RuntimeState 枚举 + 严格迁移表
│       │   └── manager.py       #   RuntimeManager(Event Bus 消费者)
│       ├── agent/
│       │   ├── controller.py    #   Agent Controller(Agent Loop)
│       │   ├── states.py        #   Agent 状态定义
│       │   ├── reflex/          #   L1 反射层(HP/MP/死亡/紧急暂停)
│       │   ├── planner/         #   L2 规划层
│       │   │   └── llm/         #     LLM Provider 抽象 + 适配器(不绑定 DeepSeek)
│       │   └── memory/          #   短期/长期记忆,Session 上下文
│       ├── vision/              # 视觉适配层
│       │   ├── interface.py     #   Vision Provider 抽象契约
│       │   ├── capture.py       #   窗口截图(DPI-Aware)
│       │   ├── coord.py         #   窗口 Rect 相对坐标换算
│       │   ├── matchers/        #   模板匹配 / 颜色检测(Phase 1)
│       │   └── ocr/             #   OCR Provider 抽象(不锁死引擎)
│       │       ├── base.py      #     OCR Provider 接口
│       │       └── providers/   #     tesseract / windows_ocr / paddleocr(Phase 1)
│       ├── input/               # 输入适配层
│       │   ├── interface.py     #   Input Interface(抽象契约)
│       │   ├── actions.py       #   动作模型(移动/技能/购买/药水)
│       │   └── providers/       #   mock.py(Phase 0);后续 win32 等
│       ├── game/                # 游戏客户端
│       │   ├── window.py        #   只读 GameWindowDetector 接口 + Mock
│       │   └── state.py         #   游戏状态聚合
│       ├── task/                # 任务系统 + 补给 + Human Teaching(骨架)
│       ├── knowledge/           # 知识库框架
│       │   ├── loader.py        #   JSON/CSV 加载与校验
│       │   ├── versioning.py    #   档案目录检测(game_profile)
│       │   └── update.py        #   手动/增量更新 + 更新报告
│       ├── database/            # SQLite:sessions、decisions、tasks、knowledge_versions
│       ├── sessions/            # Session Replay 骨架
│       └── webui/               # FastAPI 应用
│           ├── app.py           #   FastAPI 实例与路由(Dashboard + Runtime API + /api/health)
│           ├── ws.py            #   WebSocket 推送(runtime / error / log 事件)
│           ├── templates/       #   Jinja2 模板(index.html)
│           └── static/          #   Bootstrap 本地 vendor(无 Node 构建)
│
├── knowledge/                   # 外部知识库框架
│   ├── README.md                # 知识包格式与导入说明
│   ├── schema/                  # JSON Schema(Phase 0 只建 schema,不导入数据)
│   │   ├── maps.schema.json
│   │   ├── npc.schema.json
│   │   ├── monster.schema.json
│   │   ├── items.schema.json
│   │   ├── quests.schema.json
│   │   └── routes.schema.json
│   └── versions/                # game_profile 目录(运行时导入,不入库)
│       └── README.md            #   目录约定说明
│
├── data/
│   └── database/                # maple.db(运行时生成,gitignore)
│
├── logs/                        # startup/runtime/agent/vision/input/task/error(gitignore)
│
├── sessions/                    # 会话回放(gitignore)
│   └── session_xxx/
│       ├── screenshots/
│       ├── state.json
│       ├── actions.json
│       ├── decision.json
│       └── errors.log
│
├── tests/                       # pytest,全部离线可跑(Mock 环境)
│   ├── unit/
│   ├── integration/
│   └── conftest.py
│
├── docs/                        # 本目录(设计文档)
├── scripts/                     # setup.ps1 / run.ps1 / test.ps1 / update_knowledge.py
└── .github/
    └── workflows/ci.yml         # lint + pytest(不触碰游戏与网络)
```

## 2. 关键文件职责

| 文件/目录 | 职责 |
| --- | --- |
| `src/maple_agent/main.py` | 程序入口:加载配置 → 初始化日志/DB → 启动 Runtime → 拉起 WebUI |
| `src/maple_agent/logging_setup.py` | 日志基础设施:分模块文件 + error.log + trace_id/correlation_id + 轮转 |
| `src/maple_agent/runtime/` | Runtime 状态机(含 STARTING)与严格迁移表,状态变化发布事件 + runtime.log + trace_id |
| `src/maple_agent/game/window.py` | 只读窗口检测接口(存在检测 / Title / Process / Rect),禁止内存读取 / 注入 / Hook |
| `src/maple_agent/agent/controller.py` | Agent Loop 编排与执行门控 |
| `src/maple_agent/agent/planner/llm/` | LLM Provider 抽象,不绑定 DeepSeek |
| `src/maple_agent/providers/` | Provider 抽象层:LLM / OCR / Vision / Storage 接口 + Mock,统一生命周期 / trace / 日志 / Event |
| `src/maple_agent/events/` | Event Bus:Reflex / Runtime / Error 事件,支持优先级 |
| `src/maple_agent/input/interface.py` | 输入抽象契约(Phase 0 仅接口 + Mock) |
| `src/maple_agent/vision/interface.py` | 视觉抽象契约(截图/识别/OCR) |
| `src/maple_agent/vision/ocr/` | OCR Provider 接口(Windows OCR / PaddleOCR / Tesseract 可切换) |
| `src/maple_agent/game/window.py` | 只读窗口检测(存在检测 + Rect),禁止内存读取 |
| `src/maple_agent/knowledge/` | 知识包加载、档案检测、增量更新与报告(Phase 0:schema + 框架) |
| `src/maple_agent/sessions/` | 每次运行生成 Session Replay 数据 |
| `src/maple_agent/webui/` | FastAPI + Jinja2 + Bootstrap + WebSocket;Dashboard 展示 Runtime / Provider / 窗口 / Event / 日志,按钮仅调 Runtime API |
| `src/maple_agent/cli.py` | CLI:start / doctor / test |
| `src/maple_agent/bootstrap.py` | 启动装配:Config→Logging→EventBus→Providers→Runtime→WebUI |
| `knowledge/schema/` | JSON Schema,Phase 0 不导入具体游戏数据 |
| `knowledge/versions/<game_profile>/` | 运行时导入的游戏档案数据,不入库 |

## 3. 配置模板(.env.example 草案)

```dotenv
# ===== 应用 =====
MAPLE_LOG_LEVEL=INFO
MAPLE_WEBUI_HOST=127.0.0.1
MAPLE_WEBUI_PORT=8080
MAPLE_EMERGENCY_HOTKEY=ctrl+alt+pause

# ===== LLM(L2 Planner,Phase 0 仅接口) =====
LLM_PROVIDER=deepseek            # 可选: deepseek / openai_compatible
LLM_API_KEY=
LLM_BASE_URL=https://api.deepseek.com
LLM_MODEL=deepseek-v4-flash
LLM_TIMEOUT_SEC=30

# ===== 游戏 =====
MAPLE_GAME_PROCESS=MapleStory.exe
MAPLE_GAME_TITLE=MapleStory

# ===== 知识库 =====
# game_profile 目录名,对应 knowledge/versions/<game_profile>/
# 留空表示未配置档案,程序正常启动并提示
MAPLE_KB_GAME_PROFILE=

# ===== 视觉(Phase 1 生效) =====
VISION_CAPTURE_FPS=5
VISION_OCR_PROVIDER=tesseract    # 可选: tesseract / windows / paddle
VISION_SCALE_MODE=auto
```

## 4. .gitignore 要点

```gitignore
.env
logs/
sessions/
data/database/
__pycache__/
*.pyc
.venv/
.pytest_cache/
knowledge/versions/*/       # game_profile 数据(运行时导入,不入库)
# knowledge/schema/ 下的 JSON Schema 正常入库
```

> 说明:仓库内置 `knowledge/schema/`(JSON Schema)与导入工具,保证 `git clone` 后程序可启动;具体游戏数据通过 `knowledge/versions/<game_profile>/` 运行时导入,不入库。

## 5. 依赖清单分组

```text
# requirements.txt(Phase 0 核心,可离线安装)
fastapi
uvicorn[standard]
jinja2
python-multipart
websockets
pydantic
pydantic-settings
python-dotenv
structlog

# requirements-vision.txt(Phase 1 按需安装)
opencv-python
numpy
pillow
pytesseract
# paddleocr        # 可选,体积大

# requirements-dev.txt
pytest
pytest-asyncio
ruff
```

## 6. 模块依赖对应关系

完整依赖矩阵与分层规则见 [01-system-design.md](01-system-design.md) 第 5 节;依赖图见 [02-architecture.md](02-architecture.md) 第 6 节。
