# Maple AI Companion Agent — 系统设计说明

| 项 | 内容 |
| --- | --- |
| 文档版本 | v0.1(设计草案) |
| 对应需求 | Maple AI Companion Agent V1.2 |
| 日期 | 2026-08-06 |
| 状态 | 待审核 |

## 1. 项目定位与边界

### 1.1 定位

Maple AI Companion Agent 是一个针对《冒险岛怀旧服》的桌面 AI 辅助程序,目标是辅助玩家管理日常任务、怪物击杀、补给、路线与游戏状态。核心思想:**Agent 负责理解和规划,本地模块负责稳定执行**。

### 1.2 边界(重要)

- 只做冒险岛领域,不构建通用 Computer-use Agent 平台;
- 不过度抽象,但底层保持工程化(接口隔离、分层、可测试);
- 若后续稳定,再考虑将通用模块抽离为"框架 + Maple 插件"。

### 1.3 阶段约束

- 当前仅执行 **Phase 0(基础架构阶段)**:项目结构、Runtime、配置、日志、WebUI、Agent 状态机框架、知识库框架;
- **禁止**:自动移动、自动攻击、自动任务、自动购买、任何真实键鼠控制;
- Phase 0 完成后停止,等待审核。

## 2. 设计原则

1. **分阶段交付**:Phase 0→3,每阶段有明确范围与验收,完成后等待审核;
2. **依赖倒置**:核心层只依赖抽象接口(Input Interface、Vision Provider、LLM Provider),适配层实现细节可替换;
3. **双层决策**:L1 Reflex 本地低延迟(不调用 AI),L2 Planner 由 DeepSeek V4 Flash 负责秒级规划;
4. **AI 不直接控制键鼠**:所有执行必须经过 Input Interface 与运行门控;
5. **配置外部化**:禁止硬编码;密钥与本地隐私只放 `.env`(不进 Git);
6. **知识库外部化**:不解析 WZ 等专有资源,使用 JSON/CSV 外部知识包,并绑定游戏版本;
7. **安全优先**:Emergency Stop 全局热键 + 游戏窗口绑定 + 用户确认 + RUNNING 状态门控;
8. **可观测性**:全链路分模块日志 + 每次运行 Session Replay;
9. **可测试性**:核心逻辑与真实窗口/输入/视觉完全解耦,可用 Mock 跑通 Agent Loop;
10. **事件驱动**:Event Bus 统一承载 L1 Reflex 紧急事件、Runtime 状态事件与 Error 事件,模块间解耦。

## 3. 总体架构

四层结构,自顶向下:

| 层 | 模块 | 职责 |
| --- | --- | --- |
| 交付层 | Web UI、Runtime Manager | 用户交互、生命周期控制 |
| 核心层 | Agent Controller、L1 Reflex、L2 Planner、Memory | 决策、规划、状态机、记忆 |
| 适配层 | Vision、Input Provider、Game Window | 感知与执行的具体实现 |
| 数据层 | Knowledge Base、SQLite、Sessions、Logs | 知识、持久化、复盘、审计 |
| 横切基础设施 | Config、Logging、Event Bus | 配置、审计日志、模块间解耦通信 |

关键交互:

- Web UI 只与 Runtime Manager 通信(命令与状态),不直接触达 Agent;
- Agent Controller 是唯一编排者,驱动 Observe → Reason → Plan → Execute → Reflect → Memory Update;
- L1 Reflex 独立于 AI 运行,可随时打断 Planner 并插入紧急动作(HP 低、死亡、紧急暂停);
- Event Bus 承载 L1 Reflex 紧急事件、Runtime 状态事件与 Error 事件,支持优先级;
- 所有坐标基于游戏窗口 Rect 换算,不写固定绝对坐标。

## 4. 模块详细设计

### 4.1 Runtime Manager

- 完整状态:OFFLINE → STARTING → READY → RUNNING ⇄ PAUSED → STOPPING → OFFLINE,另含 ERROR 兜底;
- 严格状态迁移表:非法跳转直接拒绝(IllegalTransitionError),状态保持不变;
- Runtime 作为 Event Bus 消费者:订阅 START / PAUSE / STOP 命令与 GAME_WINDOW_LOST(窗口丢失自动暂停),忽略自身发布的事件避免自循环;
- 每次状态变化:发布对应 Event + 写入 runtime.log + 携带 trace_id;
- READY 允许:检测游戏窗口、展示状态;禁止:输入控制;
- RUNNING 需要同时满足:目标窗口存在 + 用户确认 + 状态门控;
- 提供 START / PAUSE / STOP 命令(WebUI 与全局热键均可触发)。

### 4.2 Agent Controller

- 运行 Agent Loop:Observe(采集状态)→ Reason(分析)→ Plan(生成计划)→ Execute(派发到 Executor)→ Reflect(复盘)→ Memory Update(更新记忆);
- 每轮循环可被 L1 Reflex 的紧急事件打断(高优先级);
- 包含:心跳、看门狗、循环超时、执行门控校验。

### 4.3 L1 Reflex Layer(实时反射层)

- 本地执行,不调用 AI;目标响应延迟 < 100ms;
- 职责:HP/MP 检测、死亡检测、紧急暂停、药水使用、输入恢复;
- 通过 Event Bus 发布紧急事件,Agent Controller 订阅后暂停/接管。

### 4.4 L2 Planning Layer(规划层)

- 通过 **LLM Provider 抽象接口**调用模型,不直接绑定 DeepSeek;默认适配 DeepSeek V4 Flash,支持 OpenAI 兼容接口,后续可按配置切换厂商;
- 职责:是否回城、是否补给、任务选择、路线规划、长期策略、异常分析;
- Phase 0 只实现 LLM Provider 接口与 Mock,不发起真实 API 调用;
- 允许秒级响应;调用带超时、重试、熔断;AI 不可用时不阻塞 L1。

### 4.5 Vision 视觉系统

- Screenshot Capture:窗口截图,DPI-Aware;
- OpenCV:模板匹配、颜色/条带检测(HP/MP 条、UI 元素);
- OCR Provider 抽象接口,支持未来切换 Windows OCR / PaddleOCR / Tesseract,不锁死引擎(Phase 0 仅接口);
- 识别对象:HP、MP、弹药、地图名、NPC、怪物、UI 状态;
- DPI/分辨率适配:统一以窗口逻辑坐标系 + scale_factor 换算,禁止固定绝对坐标。

### 4.6 Input 输入层

- 调用链:Agent → Input Interface → Input Provider → Windows Implementation;
- Phase 0 只定义接口 + Mock Provider(记录动作、不产生真实输入);
- 具体实现(后台模拟/驱动级)在 Phase 1 后按测试结果选择,不在 V1 架构上锁定。

### 4.7 Game Window 绑定

- **GameWindowDetector 抽象接口(Phase 0:接口 + Mock,不接真实 win32)**;
- WindowInfo 字段:handle(仅标识)/ title / process_name / WindowRect(left/top/width/height);
- 允许:窗口存在检测、窗口标题、进程名、窗口 Rect;
- **禁止**:任何内存读取、注入、Hook、句柄写入、窗口内容操作;
- 运行前校验:窗口存在 + 用户确认 + RUNNING;
- 窗口丢失/最小化 → 自动暂停并记录日志。

### 4.8 知识库系统

- 外部知识包,JSON/CSV 导入;结构:maps / npc / monster / items / quests / routes;
- 目录方式:`knowledge/versions/<game_profile>/`,不固定具体版本号;游戏档案名由配置指定(`MAPLE_KB_GAME_PROFILE`),启动时检测档案是否匹配,不匹配则提示更新;
- **Phase 0 只建立 schema(JSON Schema + 加载器框架),不导入具体游戏数据**;
- 支持手动导入、增量更新(比对差异)、生成 `knowledge_update_report.md`(新增/删除/修改)。

### 4.9 任务系统

- 任务数据库:记录 NPC、地图、条件、奖励、路线;
- 初期:固定任务模板 + 模板状态机;
- Phase 3:增加 AI 任务规划。

### 4.10 补给系统

- 检测:HP/MP/箭矢/飞镖不足;
- 流程:检测 → 规划 → 返回城镇 → 购买 → 返回地图;
- 依赖 L1(状态检测)、L2(决策)、任务/路线知识。

### 4.11 Human Teaching 模式(Phase 3)

- 用户手动完成一次流程,系统录制路线/操作/时间/状态;
- 生成任务模板,进入知识库。

### 4.12 Memory 与 Session

- 短期记忆:当前会话状态、最近决策(内存);
- 长期记忆:SQLite 持久化(任务模板、路线、统计数据);
- Session Replay:每次运行生成 `sessions/session_xxx/`,含 screenshots/、state.json、actions.json、decision.json、errors.log,用于复盘。

### 4.13 Web UI(Phase 0 可观测性控制台)

- 技术锁定:FastAPI + Jinja2 + Bootstrap + WebSocket(禁止 Node / npm);
- 展示:Runtime State、Provider 状态、Game Window 检测状态、Event 流、实时日志;
- WebSocket 实时推送:runtime 事件、error 事件、log 事件;
- START / PAUSE / STOP 按钮只调用 Runtime 状态接口(`/api/runtime/*`),禁止触发真实输入;
- Phase 0 禁止:游戏 UI 解析、HP 显示、OCR、任务页面。

### 4.14 配置系统

- pydantic-settings:默认值 → 用户配置 → 环境变量(.env)覆盖;
- `.env.example` 进 Git,`.env` 不进;
- 所有模块配置集中管理,禁止散落硬编码。

### 4.15 日志系统

- 分模块日志文件:startup.log / runtime.log / agent.log / vision.log / input.log / task.log / error.log;
- 固定等级:DEBUG / INFO / WARNING / ERROR / CRITICAL;
- 统一 trace_id / correlation_id:一次 Agent 行为链内的记录携带相同 trace_id,可跨 runtime.log / agent.log / vision.log / task.log 关联;
- runtime.log 专门记录 OFFLINE / READY / RUNNING / PAUSE / STOP 状态变化;
- 结构化字段:时间、级别、模块、trace_id、correlation_id、上下文;
- Agent 记录状态/输入/决策/原因;Vision 记录截图路径/OCR 结果/置信度;Input 记录动作/时间/来源;Error 记录堆栈/当前状态/最近动作;
- 文件轮转 + 保留策略。

### 4.16 数据库(SQLite)

- 本地单文件,零运维;
- 核心表:runtime_state、sessions、decisions、tasks、task_templates、knowledge_versions、stats。

### 4.17 Event Bus 事件总线(基础设施,被多模块依赖)

- 进程内异步优先级队列,负责模块间解耦通信;
- **强类型事件模型**:Event 含 event_id / event_type / timestamp / priority / trace_id / source / payload,payload 必须是 Pydantic 模型,禁止裸 dict;
- EventType 枚举:Runtime(START/STARTING/READY/RUNNING/PAUSE/STOP/STOPPING/STOPPED)、Vision(SCREEN_UPDATED/HP_LOW/GAME_WINDOW_LOST)、Agent(PLAN_CREATED/PLAN_FAILED)、Error(ERROR_OCCURRED);
- Priority:CRITICAL / HIGH / NORMAL / LOW,紧急事件优先处理,同优先级 FIFO;
- 与日志 trace 机制集成:Event 创建时自动取当前 trace_id,发布/分发时恢复该 trace 上下文;
- 发布/订阅模型,核心层与适配层均可使用;Phase 0 仅 Mock 测试,不连接真实模块。

### 4.18 Provider 抽象层(未来能力接入契约)

- 统一契约:所有 Provider 继承 BaseProvider,统一生命周期 CREATED → INITIALIZED → SHUTDOWN 与调用门控(未初始化即调用报错);
- 四类 Provider:LLMProvider(规划)、OCRProvider(文字识别)、VisionProvider(画面状态)、StorageProvider(持久化);
- Phase 0 只实现 Interface / Protocol / Mock,禁止真实 API 调用、真实 OCR、截图分析、游戏逻辑;
- 所有调用统一:解析/生成 trace_id → 写模块日志(LLM→agent.log、OCR/Vision→vision.log、Storage→startup.log)→ 发布 Event Bus 事件(成功/失败),失败统一 ERROR_OCCURRED 且抛 ProviderError;
- 接口与 Mock 分离:未来接入真实实现只替换 Mock,不影响上层调用方。

## 5. 模块依赖关系

### 5.1 分层依赖规则

- 交付层 → 核心层 → 适配层/数据层(单向);
- 核心层只依赖抽象接口,不 import 具体实现(如 `input.providers.win32`、`vision.providers.opencv`);
- 适配层实现接口并向核心层注册;禁止反向依赖;
- 各模块可依赖 `events`(事件总线)与 `models`(领域模型)。

### 5.2 依赖矩阵

| 模块 | 依赖 | 被依赖 |
| --- | --- | --- |
| webui | runtime(命令/状态)、events | — |
| runtime | agent、config、logging、events | webui、main |
| agent.controller | reflex、planner、vision.interface、input.interface、memory、knowledge、task、events | runtime |
| agent.reflex | vision.interface、input.interface、events | agent.controller |
| agent.planner | llm.provider、memory、knowledge、events | agent.controller |
| vision.* | config、logging | agent、reflex |
| input.* | config、logging、game.window | agent、reflex |
| knowledge | config、logging、database | agent、planner、task |
| database | config | knowledge、memory、task、sessions |
| sessions | logging、events | runtime、agent |
| events | models | 全部模块(横切) |
| game.window | config、logging | runtime(READY 检测)、input.* |
| providers | events、logging_setup | agent.planner、vision、task、sessions(后续接入) |

详细调用图见 [02-architecture.md](02-architecture.md)。

## 6. 关键技术决策

| 决策点 | 选择 | 理由 |
| --- | --- | --- |
| 语言/运行时 | Python 3.11+ | 生态成熟(OpenCV/FastAPI),开发效率高 |
| 进程模型 | 单进程 + asyncio 主循环 + 工作线程(视觉/输入) | 降低复杂度,事件循环统一调度 |
| 模块通信 | 进程内 Event Bus(异步队列) | Reflex 打断、状态广播解耦 |
| Web 后端 | FastAPI + WebSocket | 与需求锁定一致,轻量 |
| 前端 | Jinja2 + Bootstrap(静态资源) | 无 Node 构建链 |
| 知识库版本 | `knowledge/versions/<game_profile>` + `MAPLE_KB_GAME_PROFILE` | 不绑定固定版本号,档案可配置 |
| 持久化 | SQLite | 单机零运维,足够 |
| LLM 接入 | LLM Provider 抽象 + httpx 异步客户端(DeepSeek 为默认适配) | 不绑定厂商,超时/重试/熔断可控 |
| 坐标体系 | 窗口 Rect 相对坐标 + scale_factor | 支持 DPI/多显示器/不同分辨率 |
| OCR | OCR Provider 抽象(Windows OCR / PaddleOCR / Tesseract 可选) | 按实测结果切换,不锁死 |
| 输入 | Interface + Mock(Phase 0) | 先定契约,后选实现 |

## 7. 非功能需求

- **性能**:Reflex < 100ms;Vision 采样 1–5 FPS(可配置);Planner 秒级;
- **安全**:Emergency Stop 全局热键(默认 Ctrl + Alt + Pause,可配置);执行三重门控(窗口存在 + 用户确认 + RUNNING);
- **可用性**:任何异常不静默,进 ERROR 状态并落日志;
- **可维护性**:模块单一职责,接口稳定,文档随代码更新;
- **可部署性**:`git clone → pip install -r requirements.txt → cp .env.example .env → python -m maple_agent`。

## 8. 术语表

| 术语 | 含义 |
| --- | --- |
| Agent Loop | 观察→推理→规划→执行→反思→记忆更新 的循环 |
| L1 Reflex | 本地实时反射层(毫秒级,不调用 AI) |
| L2 Planner | DeepSeek 规划层(秒级) |
| Provider | 可替换实现(视觉/输入/LLM) |
| Session Replay | 会话回放数据,用于问题复盘 |
| WZ | 冒险岛客户端专有资源格式(本项目不解析) |

## 9. 已确认决策与待确认项

已按审核意见确认:

1. 知识库:采用 `knowledge/versions/<game_profile>` 目录方式,不绑定固定版本;Phase 0 仅建 schema,不导入具体游戏数据;
2. Emergency Stop 默认热键:Ctrl + Alt + Pause;
3. OCR:设计 Provider 接口,支持 Windows OCR / PaddleOCR / Tesseract 切换;
4. Phase 0 包含只读窗口检测(存在检测 + Rect 获取),禁止任何内存读取;
5. 增加 Event Bus(Reflex / Runtime / Error 事件)与 LLM Provider 抽象(不绑定 DeepSeek)。

待确认:

1. `MAPLE_KB_GAME_PROFILE` 默认留空(未配置档案时程序正常启动并提示),是否接受;
2. Phase 0 窗口检测用 win32 只读 API 实现,依赖环境实测确认。
