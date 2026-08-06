# Phase 0 开发计划

## 1. 目标

交付可运行、可测试、可审核的基础架构骨架,不包含任何游戏自动化行为。

## 2. 范围

### 允许

- 项目结构、配置系统、日志系统、数据库、事件总线;
- Runtime 状态机、Agent 状态机框架与 Agent Loop 骨架;
- 知识库框架(加载/版本检测/更新报告);
- Session Replay 骨架;
- WebUI 骨架(FastAPI + Jinja2 + Bootstrap + WebSocket);
- 输入/视觉/LLM 抽象接口与 Mock Provider(LLM 不绑定 DeepSeek,OCR 不锁死引擎);
- Event Bus 基础模块(Reflex / Runtime / Error 事件);
- 只读游戏窗口检测(存在检测 + Rect 获取)。

### 禁止

- 自动移动、自动攻击、自动任务、自动购买;
- 真实键鼠控制(Input 只允许 Mock);
- 任何未确认的外部副作用(LLM 真实调用不在 Phase 0 范围);
- 解析 WZ 等客户端专有资源;
- 任何内存读取;
- 任何真实键鼠执行。

## 3. 里程碑

| 里程碑 | 内容 | 交付物 / 验收标准 |
| --- | --- | --- |
| M0 仓库骨架 | README / LICENSE / .gitignore / .env.example / requirements / pyproject | 按文档可完成 `git clone` 与依赖安装 |
| M1 配置系统 | settings.py + defaults.yaml + .env 加载 | 单测:默认值、环境变量覆盖、非法值报错 |
| M2 日志系统 | logging_setup.py:7 个分模块文件(startup/runtime/agent/vision/input/task/error)+ trace_id/correlation_id + 轮转 | 启动即生成 startup.log/error.log;同一 trace_id 可跨文件关联;轮转生效 |
| M3 事件总线 | events/:强类型 Event + EventType/Priority 枚举 + 异步优先级队列 + trace 集成 | 单测:强类型校验、优先级排序、同优先级 FIFO、trace 跨订阅者关联 |
| M4 Runtime + 状态机 | OFFLINE/STARTING/READY/RUNNING/PAUSED/STOPPING/ERROR 严格迁移表;状态变化发布事件 + runtime.log + trace_id | 单测覆盖合法/非法迁移、Bus 命令消费、事件发布;READY 下禁止输入 |
| M4.5 只读窗口检测 | game/window.py:GameWindowDetector 接口 + Mock(存在检测 / Title / Process / Rect) | 单测用 Mock 窗口对象;READY 状态展示检测结果 |
| M5 Provider 接口层 | providers/:LLM / OCR / Vision / Storage 抽象 + Mock,统一生命周期 / trace / 日志 / Event Bus | 单测:Mock 生命周期、异常处理、接口契约、事件发布 |
| M5b Agent 框架 | Controller + Agent Loop + Reflex/Planner/Executor 接口 + Mock | Mock 环境跑通完整 Loop;Reflex 紧急事件可打断 |
| M6 知识库框架 | loader / versioning / update 报告骨架 + schema/(JSON Schema),不导入具体数据 | 加载 schema、档案不匹配提示、生成更新报告 |
| M7 Session 骨架 | session_xxx 目录,state/actions/decision/errors 落盘 | 一次运行生成完整会话文件 |
| M8 WebUI 控制台 | FastAPI + Jinja2 + Bootstrap + WS;Dashboard 显示 Runtime / Provider / 窗口 / Event / 日志;START/PAUSE/STOP 仅调 Runtime API | 浏览器可访问;按钮驱动状态机且不产生输入;WS 推送事件与日志 |
| M9 测试与文档 | 全部单测通过 + docs 齐备 | pytest 0 失败;README 快速开始可复现 |

## 4. 测试策略

- 全部测试离线可跑,不依赖游戏进程、不调用真实 API;
- 使用 Mock:Vision Provider(固定 GameState)、Input Provider(记录动作)、LLM Provider(固定 Plan)、窗口对象(固定 Rect);
- 日志:分模块落盘、等级过滤、trace_id 跨文件关联、文件轮转;
- 覆盖范围:配置、日志、状态机、事件总线、知识库加载/版本检测、Agent Loop(正常 + 紧急打断 + 异常路径)。

## 5. 每次开发提交要求(对齐 V1.2 第 23 节)

每次代码提交必须附:

1. 修改文件列表;
2. Git Commit 建议;
3. 测试结果;
4. 完整运行日志;
5. 错误日志(如无则说明);
6. 下一步优化建议。

## 6. Phase 0 完成验收清单

- [ ] `pip install -r requirements.txt` 成功;
- [ ] `python -m maple_agent` 启动,WebUI 可访问;
- [ ] READY / RUNNING / PAUSED / STOP 状态切换符合状态机定义;
- [ ] 程序运行中允许:READY 状态、WebUI、日志、只读窗口检测;
- [ ] 全程无任何真实键鼠执行(Input 仅 Mock);
- [ ] 无任何内存读取代码;
- [ ] pytest 全部通过;
- [ ] logs/ 与 sessions/ 正常生成且 .gitignore 生效;
- [ ] 提交记录含上述 6 项信息。

## 7. Phase 1 入口(后续)

- Vision:窗口截图、OpenCV 模板/颜色检测、OCR 真实实现(Windows OCR / PaddleOCR / Tesseract 实测选型);
- Input:Provider 选型与实现(先后台模拟,按测试结果再定);
- Agent:游戏状态与状态机对齐,联调 L1/L2。
