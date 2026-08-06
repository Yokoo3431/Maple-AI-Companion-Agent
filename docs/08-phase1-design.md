# Maple AI Companion Agent — Phase 1 Vision Foundation 设计文档

| 项 | 内容 |
| --- | --- |
| 文档版本 | v0.1(设计草案) |
| 关联阶段 | Phase 0 Freeze(v0.1.0-phase0)之后的首个子阶段 |
| 日期 | 2026-08-06 |
| 状态 | 待审核 |

## 1. Phase 1 目标

建立可观测的游戏画面感知基础:窗口截图(DPI-Aware)、Vision 数据模型、OCR Provider 真实实现与选型、知识库 schema 校验、WebUI 只读扩展,并接入现有 Runtime / EventBus / Provider 体系。

本阶段交付:

- Screenshot Provider(Capture 抽象 + 真实 win32 实现 + Mock);
- Vision Pipeline:截图 → 识别 → 结构化 `VisionState`;
- OCR 引擎实测对比(Windows OCR / PaddleOCR / Tesseract)并确定默认引擎;
- Knowledge Base:地图名字典 + schema 校验落地(game_profile 检测);
- WebUI 只读扩展:Vision 状态卡片、识别结果面板、截图缩略图;
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
Vision Pipeline(OpenCV 颜色/条带检测 + OCR Provider)
        ↓
VisionState(结构化识别结果)
```

关键设计:

- **DPI / 分辨率适配**:所有坐标以窗口逻辑坐标系保存,`dpi_scale = 截图尺寸 ÷ 窗口 Rect 尺寸`,禁止绝对坐标(延续 Phase 0 原则);
- **帧率控制**:采样节流(默认 1–5 FPS,由 `VISION_CAPTURE_FPS` 配置),过载时丢帧而非排队;
- **生命周期**:CaptureProvider 复用 BaseProvider 的 CREATED → INITIALIZED → SHUTDOWN 门控;
- **窗口绑定**:截图前必须经 GameWindowDetector 确认窗口存在并取得 Rect,窗口丢失立即停止采样并发布事件。

## 3. Vision 数据模型

新增 `src/maple_agent/vision/models.py`,全部为 Pydantic 强类型模型,禁止裸 dict(与 Phase 0 Event 风格一致):

| 模型 | 字段 | 说明 |
| --- | --- | --- |
| `ScreenFrame` | frame_id / captured_at / window(WindowInfo)/ image_size / dpi_scale / image_path | 一次截图元信息,不含像素(像素文件落盘,路径入模型) |
| `VisionState` | frame_id / hp / mp / map_name / ui_flags / ocr_text / confidence / trace_id | 识别结果聚合,供上层消费 |
| `UiRegion` | kind / rect / confidence / raw_text | 可选:UI 区域级识别结果(HP 条、地图名框等) |

规则:

- 所有识别项携带 `confidence`;低于阈值标记 `low_confidence`,不静默丢弃;
- `VisionState` 输出时:写 vision.log + 发布 `SCREEN_UPDATED` 事件 + 供 WebUI 只读展示;
- 模型版本化(字段只增不删,新增走可选字段),避免后续阶段破坏性变更。

## 4. OCR Provider 接入方案

延续 Phase 0 的 `OCRProvider` 接口(`providers/ocr.py`),本阶段只新增真实引擎适配器,不改接口契约:

```text
OCRProvider(接口,Phase 0 已定义)
├─ providers/tesseract.py     # pytesseract + Tesseract 安装检测
├─ providers/windows_ocr.py   # WinRT Windows.Media.Ocr(zh-Hans 语言包)
└─ providers/paddleocr.py     # 可选,体积大、延迟高
由配置 VISION_OCR_PROVIDER 选择(tesseract / windows / paddle)
```

接入要点:

- **实测选型**:同一批测试图(地图名、HP/MP 数字、UI 文案)跑三个引擎,输出准确率 / 延迟 / 依赖对比表,据此定默认引擎(建议先以 Tesseract 验证链路);
- **词典后处理**:地图名字典纠错 + 数字区域白名单字符集;小规模 `OCR_FIXES` 修正字典(沿用全局指令中 DXF 流程的经验);
- **组合关系**:OCR 作为 Vision Pipeline 的识别子步骤,对外只暴露 `VisionProvider.capture_state()`,上层不感知引擎差异;
- **置信度传递**:引擎原始置信度归一化后进入 `VisionState.confidence`。

## 5. Knowledge Base 准备

延续 Phase 0 框架(`knowledge/schema/` + `knowledge/versions/<game_profile>/`),Phase 1 只做"准备",不导入海量数据:

- **schema 校验落地**:maps / npc / monster / items / quests / routes 的 JSON Schema + Pydantic 校验器,加载即校验;
- **地图名字典**:`maps` 知识项提供 地图名 → 别名/英文,用于 OCR 结果纠错(供 Vision Pipeline 查询);
- **game_profile 检测**:启动时检测 `knowledge/versions/<game_profile>/` 是否存在;缺失则 WebUI 提示"未配置知识档案",只读模式不阻塞;
- 数据来源仍为用户整理 / 社区公开资料,禁止解析 WZ 等客户端专有资源。

## 6. WebUI 扩展方案

只读扩展,沿用 FastAPI + Jinja2 + Bootstrap + WebSocket,不新增任何控制/输入按钮:

| 新增 | 说明 |
| --- | --- |
| Vision 卡片 | 最近 ScreenFrame:窗口标题、分辨率、dpi_scale、FPS、捕获耗时 |
| 识别结果面板 | HP / MP / 地图名 / 置信度 / 最近 OCR 文本 |
| 截图缩略图 | 最近一帧图片(仅本机读取,存 sessions/ 或 logs/,不上传) |
| `GET /api/vision/state` | 最近 VisionState JSON(只读) |
| WS 渲染分支 | 前端处理 `vision.screen_updated` 事件,增量刷新面板 |

## 7. 与现有 Runtime / EventBus / Provider 的连接方式

- **EventBus**:Vision Pipeline 发布 `SCREEN_UPDATED`(payload 为 VisionState);失败发布 `ERROR_OCCURRED`;窗口丢失沿用 `GAME_WINDOW_LOST`(Runtime 已有自动暂停逻辑);
- **Runtime**:Vision 采样循环仅在 `RUNNING` 状态运行;`READY` 允许单次手动截图(只读);`PAUSED` / `STOPPING` / `OFFLINE` 停止采样——由 Runtime 状态事件驱动 Vision 启停;
- **Provider**:`VisionProvider` 组合 `CaptureProvider` + `OCRProvider`,仍遵循 BaseProvider 生命周期与 trace / 日志 / 事件;配置经 `settings.vision` 读取;
- **trace**:一次截图识别链共用 trace_id,贯穿 vision.log / agent.log(后续 L2 决策复用同一链);
- 本阶段不接入 Agent Controller 的自动循环(那是 Phase 1 后续子阶段),避免越过"只读感知"边界。

## 8. 安全边界

- **只读边界**:仅读取窗口画面;禁止输入注入、内存读取、Hook、窗口句柄写入、窗口内容操作(延续 Phase 0 约束);
- **执行门控**:Vision 采样仅在"窗口存在 + RUNNING"时进行,窗口丢失立即暂停并发布事件;
- **隐私**:截图默认仅本地保留;WebUI 仅绑定 127.0.0.1、无鉴权,文档声明禁止暴露公网;
- **性能**:采样节流 + 丢帧,避免抢占游戏性能;
- **合规**:本阶段不实现自动输入 / 攻击 / 任务 / 游戏控制;第三方辅助风险已在 README 免责声明提示,由使用者自担。

## 9. 测试策略

- **离线优先**:MockCaptureProvider + 固定测试图驱动 Pipeline,不依赖真实窗口/游戏;
- **单元测试**:数据模型校验、DPI 换算、坐标换算、OCR 词典后处理、引擎选择逻辑、丢帧策略;
- **集成测试(Windows-only)**:真实窗口(记事本/示例窗口)截图,验证 Capture → Vision → Event 全链路;OCR 引擎实测表(准确率 / 延迟)作为测试产物;
- **回归**:Phase 0 全部测试(71)保持通过,新增不破坏;
- **CI**:非 Windows 部分(模型、换算、事件、Mock 链路)可在 ubuntu 运行;截图与 OCR 实测标 Windows-only 跳过。

## 限制(本设计明确禁止)

- 不设计自动输入、自动攻击、自动任务、游戏控制;
- 不设计键鼠注入、内存读取、Hook;
- 不解析 WZ 等客户端专有资源。

## 待确认项

1. OCR 默认引擎倾向:建议先 Tesseract 验证链路,后续按实测切换;
2. 截图保存策略:默认存会话目录,可配置关闭;
3. 采样 FPS 默认值:建议 2 FPS;
4. WebUI 继续无鉴权(仅 127.0.0.1)是否接受。
