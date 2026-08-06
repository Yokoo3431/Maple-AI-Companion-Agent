# Maple AI Companion Agent — Phase 0 Release

| 项 | 内容 |
| --- | --- |
| 版本 | 0.1.0(Phase 0 Release Candidate) |
| 日期 | 2026-08-06 |
| 状态 | 待最终审核 |

## 1. 已完成模块

| 里程碑 | 模块 | 提交 | 说明 |
| --- | --- | --- | --- |
| M0 | 仓库骨架 | 85e6a9b | README / LICENSE / gitignore / .env.example / 依赖 / pyproject / CI |
| M1 | 配置系统 | 487915e | defaults.yaml + .env + 环境变量,应用/LLM/游戏/知识库/视觉五节 |
| M2 | 日志系统 | b8b7066 | 7 个分模块文件 + trace_id/correlation_id + 固定等级 + 轮转 |
| M3 | Event Bus | 05195f7 | 强类型 Event / EventType / Priority,异步优先级队列 |
| M4 | Runtime 状态机 | 92fbd4c | 7 状态严格迁移表,Event Bus 消费者,runtime.log + trace |
| M4.5 | 只读窗口检测 | 92fbd4c | GameWindowDetector 接口 + Mock(禁止内存读取/注入/Hook) |
| M5 | Provider 接口层 | 7dfec02 | LLM / OCR / Vision / Storage + Mock,统一生命周期/trace/日志/Event |
| M6 | WebUI 控制台 | 49c4247 | FastAPI + Jinja2 + Bootstrap + WebSocket,只读 Dashboard + Runtime API |
| M7 | Integration + RC | 本里程碑 | python -m maple_agent、/api/health、CLI(start/doctor/test) |
| M7.1 | Desktop Launcher | 本里程碑 | 双击启动:环境检查 / venv / 依赖 / 自动打开 WebUI / launcher.log |
| M7.1.1 | Launcher 可用性 + 审核包 | 本里程碑 | 阶段日志 / Debug 模式 / ExecutionPolicy 检查 / External Review Package 生成器 |

## 2. 测试结果

- pytest:全量通过(含配置、日志、事件、状态机、窗口、Provider、WebUI、CLI、装配);
- ruff:`All checks passed!`;
- CI:GitHub Actions 在 Python 3.11 / 3.12 上运行 lint + pytest。

## 3. 架构说明

四层结构 + 横切基础设施:

```text
交付层:Web UI(FastAPI + Jinja2 + WebSocket)、Runtime Manager
核心层:Agent Controller、L1 Reflex、L2 Planner(LLM Provider)、Memory
适配层:Vision、Input(Interface)、Game Window(只读)
数据层:Knowledge Base(schema)、SQLite、Sessions、Logs
横切:Config、Logging、Event Bus
```

关键机制:

- 启动流程:Config → Logging → EventBus → Providers → Runtime → WebUI;
- Agent 行为链:一次操作通过 trace_id / correlation_id 贯穿 runtime / agent / vision / task 日志与事件;
- Runtime 每次状态变化:发布 Event + 写 runtime.log + 携带 trace_id,非法跳转被严格迁移表拒绝;
- Provider 调用统一:生命周期门控 + trace + 日志 + 成功/失败事件。

## 4. 当前限制(Phase 0)

- 所有 Provider 均为 Mock:无真实 DeepSeek API、无 Tesseract / Windows OCR / PaddleOCR、无截图分析;
- 窗口检测为 Mock,未接入真实 win32;
- 无输入执行、无游戏逻辑、无任务/补给/Human Teaching;
- WebUI 仅绑定 127.0.0.1,无鉴权,定位为本地控制台;
- 知识库仅 schema 框架,未导入具体游戏数据;
- Session Replay 落盘骨架顺延至 Phase 1;
- 尚未配置 `MAPLE_KB_GAME_PROFILE`,知识库默认不加载。

## 5. Phase 1 计划

- Vision:窗口截图(DPI-Aware)、OpenCV 模板/颜色检测、OCR Provider 实测选型(Windows OCR / PaddleOCR / Tesseract);
- Input:Provider 选型与实现(先后台模拟,再按测试结果定);
- Game Window:win32 只读实现(存在检测 / Title / Process / Rect);
- Agent:Controller + Agent Loop,接入 L1 Reflex 与 L2 Planner;
- Session Replay:session_xxx 落盘骨架;
- 知识库:加载器 + schema 校验 + 版本档案检测落地。
