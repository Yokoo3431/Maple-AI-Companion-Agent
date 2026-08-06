# Maple AI Companion Agent — 架构图

> 全部为 Mermaid 源码,可直接在 GitHub、Typora 或支持 Mermaid 的编辑器中渲染。

## 1. 系统上下文

```mermaid
flowchart LR
    P["玩家"] -->|浏览器访问| UI["Web UI<br/>(FastAPI + Jinja2 + WebSocket)"]
    UI -->|START / PAUSE / STOP| RM["Runtime Manager"]
    RM -->|生命周期控制| AC["Agent Controller"]
    AC -->|OBSERVE| V["Vision 视觉"]
    AC -->|REASON / PLAN| PL["L2 Planner<br/>DeepSeek V4 Flash"]
    AC -->|EXECUTE| IN["Input Provider"]
    AC -->|查询| KB["Knowledge Base<br/>(versions / game_profile)"]
    AC -->|读写| DB[("SQLite + Sessions")]
    V -->|窗口截图| G["游戏客户端窗口"]
    IN -.->|Phase 1+ 真实输入| G
    RM -->|状态 / 日志| UI
```

## 2. 分层架构(容器图)

```mermaid
flowchart TB
    subgraph DEL["交付层 Delivery"]
        UI["Web UI"]
        RM["Runtime Manager"]
    end
    subgraph CORE["核心层 Core"]
        AC["Agent Controller"]
        RX["L1 Reflex 反射层"]
        PL["L2 Planner 规划层"]
        MEM["Memory 记忆"]
    end
    subgraph AD["适配层 Adapter"]
        VIS["Vision 视觉<br/>(Capture / OpenCV / OCR)"]
        INP["Input 输入<br/>(Interface → Provider)"]
        GW["Game Window 窗口绑定"]
    end
    subgraph DAT["数据层 Data"]
        KB["Knowledge Base"]
        SQ[("SQLite")]
        SESS["Sessions / Replay"]
        LOGS["Logs 日志"]
    end
    subgraph CROSS["横切基础设施"]
        EB["Event Bus 事件总线"]
    end

    UI --> RM
    RM --> AC
    AC --> RX
    AC --> PL
    AC --> MEM
    RX -.紧急事件.-> EB
    RM -.状态事件.-> EB
    EB --> AC
    EB --> RM
    AC --> VIS
    AC --> INP
    VIS --> GW
    INP --> GW
    AC --> KB
    MEM --> SQ
    SESS --> LOGS
```

## 3. Agent Loop 时序

```mermaid
sequenceDiagram
    participant AC as Agent Controller
    participant RX as L1 Reflex
    participant VIS as Vision
    participant PL as L2 Planner(DeepSeek)
    participant EX as Executor / Input
    participant MEM as Memory

    loop 每轮 Tick
        AC->>VIS: capture_and_recognize(窗口截图)
        VIS-->>AC: GameState(HP / MP / 地图 / UI)
        AC->>RX: reflex_check(GameState)
        alt 紧急事件(HP 低 / 死亡 / 紧急暂停)
            RX-->>AC: EMERGENCY 事件(打断当前计划)
            AC->>EX: execute(紧急动作)
        else 正常
            AC->>PL: reason(GameState, 目标, 记忆)
            PL-->>AC: Plan(任务 / 路线 / 补给决策)
            AC->>EX: execute(Plan)
            EX-->>AC: 执行结果
        end
        AC->>MEM: reflect + update(决策与结果)
    end
```

## 4. Runtime 状态机

```mermaid
stateDiagram-v2
    [*] --> OFFLINE
    OFFLINE --> STARTING: start()
    STARTING --> READY: 启动完成
    STARTING --> STOPPING: 取消启动
    STARTING --> ERROR: 启动失败
    READY --> RUNNING: 窗口存在 + 用户确认 + start_agent()
    READY --> STOPPING: stop()
    READY --> ERROR: 未处理异常
    RUNNING --> PAUSED: PAUSE / 窗口丢失 / 紧急暂停
    PAUSED --> RUNNING: 恢复(重新校验门控)
    RUNNING --> STOPPING: STOP / Emergency Stop
    PAUSED --> STOPPING: STOP / Emergency Stop
    RUNNING --> ERROR: 未处理异常
    PAUSED --> ERROR: 未处理异常
    STOPPING --> OFFLINE: 停止完成(保存会话)
    STOPPING --> ERROR: 停止异常
    ERROR --> OFFLINE: 用户确认 / 恢复
```

## 5. 知识库版本与更新流程

```mermaid
flowchart TD
    A["启动"] --> B{"检测 knowledge/versions/<br/>与配置的 game_profile"}
    B -- 匹配 --> C["加载知识包(JSON / CSV)"]
    B -- 不匹配 --> D["提示更新(WebUI + 日志)"]
    D --> E{"手动导入 / 增量更新"}
    E --> F["比对数据差异"]
    F --> G["生成 knowledge_update_report.md"]
    G --> C
```

## 6. 模块依赖图

```mermaid
flowchart LR
    UI["WebUI"] --> RM["Runtime Manager"]
    RM --> AC["Agent Controller"]
    AC --> RX["Reflex"]
    AC --> PL["Planner"]
    AC --> VIS["Vision"]
    AC --> IN["Input Interface"]
    VIS --> GW["Game Window"]
    IN --> GW
    AC --> KB["Knowledge Base"]
    AC --> MEM["Memory"]
    MEM --> DB[("SQLite")]
    RM --> LOG["Logging"]
    AC --> LOG
    RX -.紧急事件.-> EB["Event Bus"]
    RM -.状态事件.-> EB
    EB --> AC
    EB --> RM
```

## 7. 图例说明

- 实线:正式调用/数据流;
- 虚线(`-.->`):事件/异步通知(Reflex 紧急事件、Runtime 状态事件等,经 Event Bus 路由);
- 各模块职责与依赖表详见 [01-system-design.md](01-system-design.md)。
