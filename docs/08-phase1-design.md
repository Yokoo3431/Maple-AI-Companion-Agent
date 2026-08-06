# Maple AI Companion Agent — Phase 1 Vision Foundation 设计文档(Review Patch v0.2)

| 项 | 内容 |
| --- | --- |
| 文档版本 | v0.2(设计审核修订) |
| 关联阶段 | Phase 0 Freeze(v0.1.0-phase0)之后的首个子阶段 |
| 日期 | 2026-08-06 |
| 状态 | 待审核 |

## 1. Phase 1 目标

建立可观测的游戏画面感知基础:窗口截图(DPI-Aware)、Observation Layer、Vision 数据模型、OCR Provider 真实实现与选型、Knowledge Provider、WebUI 只读扩展,并接入现有 Runtime / EventBus / Provider 体系。

本阶段交付:

- Screenshot Provider(Capture 抽象 + 真实 win32 实现 + Mock)+ ScreenshotPolicy 容量控制;
- Observation Layer:截图 → 原始识别(Observation)→ 聚合摘要(VisionState);
- Vision Worker 生命周期(STOPPED / IDLE / CAPTURING / ERROR),与 Runtime 总体生命周期分工;
- OCR 引擎实测对比(Windows OCR baseline / Tesseract fallback / PaddleOCR optional)并确定默认引擎;
- Knowledge Provider:地图名字典 / NPC / 怪物查询接口,Vision Pipeline 不直接读 JSON;
- WebUI 只读扩展:Vision 状态卡片、识别结果面板、截图缩略图;
- Session Replay:`sessions/<trace_id>/` 落盘,便于未来 Vision 调试;
- 全链路 trace 贯通:一次"截图 → 识别 → 事件"共用一个 trace_id。

原则:**只"看"不"动"**——本阶段不涉及任何输入执行、攻击、任务或游戏控制(见"安全边界")。

## 2. Screenshot Provider 架构

位置:`src/maple_agent/vision/`,沿用 Phase 0 的 BaseProvider 生命周期契约(initialize / shutdown / trace / 日志 / 事件)。

```text
GameWindowDetector(只读,Phase 0 已有)
        ↓ 窗口 Rect / 存在性
Screenshot Provider
  ├─ CaptureProvider(抽象)
  │   ├─ Win32CaptureProvider:窗口截图(DPI-Aware、BitBlt/PrintWindow、多显示器坐标换算)
  │   └─ MockCaptureProvider:固定测试图 / 帧序列(离线测试)
        ↓
ScreenFrame(强类型:frame_id / captured_at / window / image_size / dpi_scale / image_path)
        ↓
Observation Layer(原始识别结果,见第 3 节)
        ↓
VisionState(聚合摘要)
```

关键设计:

- **DPI / 分辨率适配**:所有坐标以窗口逻辑坐标系保存,`dpi_scale = 截图尺寸 ÷ 窗口 Rect 尺寸`,禁止绝对坐标(延续 Phase 0 原则);
- **帧率控制**:采样节流(默认 1–5 FPS,由 `VISION_CAPTURE_FPS` 配置),过载时丢帧而非排队;
- **窗口绑定**:截图前必须经 GameWindowDetector 确认窗口存在并取得 Rect,窗口丢失立即停止采样并发布事件。

### 2.1 ScreenshotPolicy(新增)

避免长期运行积累大量截图,策略字段:

| 字段 | 默认 | 说明 |
| --- | --- | --- |
| `save_enabled` | false | 是否落盘原始帧;生产默认关闭,调试时开启 |
| `max_images` | 50 | 单个 trace / 会话最多保留的帧数,超出按 FIFO 清理 |
| `ttl` | 3600(秒) | 截图文件最长保留时间,过期清理 |
| `compression` | "png" | png(无损)/ jpeg(体积小,质量可配) |

清理由 Vision Worker 定期执行;截图目录统一为 `sessions/`(与 Session Replay 共用)。

### 2.2 Vision Worker 生命周期(新增)

分工:**Runtime 负责总体生命周期**(状态机决定 Worker 何时启动/停止),**Vision Worker 负责内部采集状态**。

```text
VisionWorkerState:
  STOPPED   未启动(与 Runtime OFFLINE/READY 对应)
  IDLE      已启动,等待下一个采样 tick
  CAPTURING 正在截图/识别(单帧处理中)
  ERROR     采集异常(可自动恢复或等待 Runtime 介入)
```

状态迁移:

- STOPPED → IDLE:Runtime 进入 RUNNING 时启动采样;
- IDLE → CAPTURING:到达采样 tick;
- CAPTURING → IDLE:单帧完成(或丢帧);
- CAPTURING / IDLE → ERROR:异常(窗口丢失、捕获失败);
- ERROR → IDLE:自动重试 / 恢复;ERROR → STOPPED:Runtime 停止;
- 任何状态 → STOPPED:Runtime 进入 PAUSED / STOPPING / OFFLINE 时停止采样。

状态变化写 vision.log;异常统一发布 `ERROR_OCCURRED`;正常帧发布 `SCREEN_UPDATED`。

## 3. Vision 数据模型

新增 `src/maple_agent/vision/models.py`,全部为 Pydantic 强类型模型,禁止裸 dict(与 Phase 0 Event 风格一致)。

数据流:`ScreenFrame → Observation → VisionState`

### 3.1 ScreenFrame(截图元信息)

| 字段 | 说明 |
| --- | --- |
| frame_id | 帧唯一 ID |
| captured_at | 捕获时间 |
| window | WindowInfo(窗口标题 / 进程 / Rect) |
| image_size / dpi_scale | 尺寸与 DPI 换算 |
| image_path | 原始帧落盘路径(受 ScreenshotPolicy 控制,可为空) |

### 3.2 Observation(原始识别结果,新增)

每个可识别元素一条,承载原始识别输出:

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `element` | str | 元素标识,如 "hp_bar" / "mp_bar" / "map_name" / "ui_text" |
| `type` | str | 识别类型:"number" / "text" / "bar_ratio" / "boolean" |
| `raw_value` | str | 引擎 / 检测器原始输出(未清洗) |
| `normalized_value` | str \| int \| float \| bool | 归一化后的值(数字、文本、比例) |
| `confidence` | float | 0..1 置信度 |
| `source` | str | 来源,如 "ocr.windows" / "color.hp_bar" |

### 3.3 VisionState(聚合摘要)

**VisionState 不直接承载所有原始识别结果**,只携带聚合摘要:

| 字段 | 说明 |
| --- | --- |
| frame_id / trace_id | 关联帧与行为链 |
| hp / mp / map_name | 聚合后的关键数值(来自对应 Observation 的 normalized_value) |
| summary | 摘要文本(如 "HP 850/1000,地图 射手村") |
| observation_refs | Observation 摘要引用(element / normalized_value / confidence 精简列表) |
| overall_confidence | 整体置信度(各 Observation 加权) |

规则:

- 原始明细进 Observation;VisionState 只携带摘要与引用;
- 需要原始明细时,按 frame_id 查内存缓存或 Session Replay(`vision.json`);
- 所有识别项带 confidence,低于阈值标记 `low_confidence`,不静默丢弃;
- 模型版本化:字段只增不删,新增走可选字段。

## 4. OCR Provider 接入方案

延续 Phase 0 的 `OCRProvider` 接口(`providers/ocr.py`),本阶段只新增真实引擎适配器,不改接口契约:

```text
OCRProvider(接口,Phase 0 已定义)
├─ providers/windows_ocr.py   # Phase 1 baseline:WinRT Windows.Media.Ocr(zh-Hans 语言包)
├─ providers/tesseract.py     # Fallback:pytesseract + Tesseract 安装检测
└─ providers/paddleocr.py     # Optional:体积大、延迟高
由配置 VISION_OCR_PROVIDER 选择(windows / tesseract / paddle)
```

默认策略:

- **baseline:Windows OCR**(系统自带、中文支持好、无额外依赖);
- **fallback:Tesseract**(Windows OCR 不可用或语言包缺失时自动降级);
- **optional:PaddleOCR**(准确率要求高的场景,按需安装)。

实测选型比较指标:

| 指标 | 说明 |
| --- | --- |
| 中文准确率 | 地图名 / UI 文案识别正确率 |
| 数字准确率 | HP / MP / 数量数字识别正确率 |
| 延迟 | 单张图识别耗时(ms) |
| 安装复杂度 | 依赖、语言包、环境配置难度 |

同一批测试图跑三个引擎,输出对比表后确定最终默认引擎。

其他要点:

- 词典后处理:地图名字典纠错经 KnowledgeProvider.resolve_alias,数字区域用白名单字符集,小规模 OCR_FIXES 修正字典;
- OCR 作为 Vision Pipeline 的识别子步骤,对外只暴露 `VisionProvider.capture_state()`,上层不感知引擎差异;
- 引擎原始置信度归一化后进入 `Observation.confidence`。

## 5. Knowledge Provider(新增)

**Vision Pipeline 不直接读取 JSON 文件**,统一经 KnowledgeProvider 接口访问知识:

```text
KnowledgeProvider(接口,遵循 BaseProvider 生命周期 / trace / 日志 / 事件)
├─ load_map_dictionary() -> MapDictionary      # 加载地图名字典(OCR 纠错用)
├─ resolve_alias(name: str) -> str | None      # 地图名 / 别名归一化
├─ get_npc(ref) -> Npc | None                  # NPC 查询(后续任务/补给使用)
└─ get_monster(ref) -> Monster | None          # 怪物查询(后续任务/补给使用)
```

实现:

- `JsonKnowledgeProvider`:读取 `knowledge/versions/<game_profile>/` 下 JSON,经 schema + Pydantic 校验后缓存;
- `MockKnowledgeProvider`:固定字典,离线测试;
- 配置 `MAPLE_KB_GAME_PROFILE`;档案缺失时 provider 报告"未配置",Vision 只读模式不阻塞。

Phase 1 内先落地 `load_map_dictionary()` 与 `resolve_alias()`(OCR 纠错);`get_npc()` / `get_monster()` 先定义接口与 Mock,供 Phase 1.5 / Phase 2 使用。

## 6. WebUI 扩展方案

只读扩展,沿用 FastAPI + Jinja2 + Bootstrap + WebSocket,不新增任何控制/输入按钮:

| 新增 | 说明 |
| --- | --- |
| Vision 卡片 | 最近 ScreenFrame:窗口标题、分辨率、dpi_scale、FPS、捕获耗时 |
| 识别结果面板 | VisionState 摘要 + Observation 精简列表(元素 / 归一化值 / 置信度) |
| 截图缩略图 | 最近一帧图片(仅本机读取,受 ScreenshotPolicy 约束) |
| `GET /api/vision/state` | 最近 VisionState JSON(只读) |
| WS 渲染分支 | 前端处理 `vision.screen_updated` 事件,增量刷新面板 |
| Session Replay 入口 | 可选:按 trace_id 查看历史帧与识别记录(本地) |

## 7. 与现有 Runtime / EventBus / Provider 的连接方式

- **Runtime ↔ Vision Worker 分工**:Runtime 状态机(OFFLINE / READY / RUNNING / PAUSED / STOPPING / ERROR)决定 Vision Worker 启停;Vision Worker 内部状态(STOPPED / IDLE / CAPTURING / ERROR)只描述采集循环,不越过 Runtime 门控;
- **EventBus**:Vision Pipeline 发布 `SCREEN_UPDATED`(payload 为 VisionState);失败发布 `ERROR_OCCURRED`;窗口丢失沿用 `GAME_WINDOW_LOST`(Runtime 已有自动暂停逻辑);
- **Provider 组合**:`VisionProvider` 组合 CaptureProvider + OCRProvider + KnowledgeProvider,均遵循 BaseProvider 生命周期与 trace / 日志 / 事件;配置经 `settings.vision` / `settings.knowledge` 读取;
- **trace**:一次截图识别链共用 trace_id,贯穿 vision.log / agent.log(后续 L2 决策复用同一链),并作为 Session Replay 目录名;
- 本阶段不接入 Agent Controller 的自动循环(那是 Phase 1 后续子阶段),避免越过"只读感知"边界。

## 8. 安全边界

- **只读边界**:仅读取窗口画面;禁止输入注入、内存读取、Hook、窗口句柄写入、窗口内容操作(延续 Phase 0 约束);
- **执行门控**:Vision 采样仅在"窗口存在 + RUNNING"时运行;READY 允许单次手动截图(只读);PAUSED / STOPPING / OFFLINE 停止采样;
- **隐私与留存**:截图默认不落盘(ScreenshotPolicy.save_enabled=false);开启调试时受 max_images / ttl 限制,避免敏感画面长期留存;WebUI 仅绑定 127.0.0.1、无鉴权,文档声明禁止暴露公网;
- **性能**:采样节流 + 丢帧,避免抢占游戏性能;
- **合规**:本阶段不实现自动输入 / 攻击 / 任务 / 游戏控制;第三方辅助风险已在 README 免责声明提示,由使用者自担。

## 9. 测试策略

- **离线优先**:MockCaptureProvider + 固定测试图驱动 Pipeline,不依赖真实窗口/游戏;
- **单元测试**:
  - Observation 模型校验与归一化(number / text / bar_ratio);
  - VisionState 聚合逻辑(Observation → 摘要,原始明细不泄漏);
  - DPI / 坐标换算、丢帧策略;
  - ScreenshotPolicy 轮换(max_images / ttl,用假时间);
  - VisionWorker 状态机(STOPPED / IDLE / CAPTURING / ERROR 迁移);
  - KnowledgeProvider:Mock + Json schema 校验 + resolve_alias 纠错;
  - OCR 词典后处理与引擎选择逻辑;
  - Session Replay 写入结构与容量约束;
- **集成测试(Windows-only)**:真实窗口(记事本/示例窗口)截图,验证 Capture → Observation → VisionState → Event 全链路;OCR 引擎实测表(中文 / 数字准确率、延迟、安装复杂度)作为测试产物;
- **回归**:Phase 0 全部测试(71)保持通过,新增不破坏;
- **CI**:非 Windows 部分(模型、换算、事件、Mock 链路、Worker 状态机)可在 ubuntu 运行;截图与 OCR 实测标 Windows-only 跳过。

## 10. Session Replay 设计(新增)

用于未来 Vision 调试与复盘,一次"截图 → 识别 → 事件"链按 trace_id 落盘:

```text
sessions/
└── <trace_id>/
    ├── frame.png      # 原始帧(受 ScreenshotPolicy 约束)
    ├── vision.json    # ScreenFrame + Observations + VisionState(结构化)
    └── events.json    # 该 trace 相关事件(SCREEN_UPDATED / ERROR_OCCURRED 等)
```

规则:

- 目录名 = trace_id,天然与日志、事件关联;
- `vision.json` 为强类型模型序列化(禁止裸 dict),供复盘工具 / 外部 AI 审核读取;
- `events.json` 记录该链发布/接收的事件(时间、类型、优先级、来源);
- 容量受 ScreenshotPolicy 约束(frame.png 可关闭,vision.json / events.json 始终保留文本记录);
- 该目录由 setup.ps1 预创建的 `sessions/` 承载,已 gitignore。

## 11. 限制(本设计明确禁止)

- 不设计自动输入、自动攻击、自动任务、游戏控制;
- 不设计键鼠注入、内存读取、Hook;
- 不解析 WZ 等客户端专有资源。

## 12. 待确认项

1. OCR 默认策略:baseline Windows OCR(需 zh-Hans 语言包)、fallback Tesseract、optional PaddleOCR——是否接受;
2. 截图保存策略:生产默认 `save_enabled=false`,调试开启并受 max_images / ttl 限制——是否接受;
3. 采样 FPS 默认值:建议 2 FPS;
4. WebUI 继续无鉴权(仅 127.0.0.1)是否接受;
5. Observation 明细保留:内存缓存(按容量淘汰)+ Session Replay 落盘——是否接受。
