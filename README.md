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
| Phase 10B | L1 Reflex Foundation(HP/MP/UI 状态与危险事件快速感知,只读) | ✅ 已完成 |
| Phase 10C | Virtual Keyboard Isolation Layer(未来隔离虚拟输入层) | 规划中 |
| Phase 11A | Vision Runtime Foundation(窗口视觉读取 -> 结构化观察,只读) | ✅ 已完成 |
| Phase 11B | Game State Understanding(结构化 Maple 游戏状态,只读) | ✅ 已完成 |
| Phase 11C | World Knowledge Foundation(Maple 世界知识图谱,只读) | ✅ 已完成 |
| Phase 11D | Spatial World Model(地图内部空间认知,只读) | ✅ 已完成 |
| Phase 12A | Navigation Planning Foundation(只读导航规划参考) | ✅ 已完成 |
| Phase 12B | Behavior Planner Foundation(高层行为规划参考,只读) | ✅ 已完成 |
| Phase 12C | Action Proposal Foundation(动作建议参考,只读) | ✅ 已完成 |
| Phase 13A | Safety Gate Foundation(动作安全审核参考,只读) | ✅ 已完成 |
| Phase 13B | Failure Recovery Foundation(失败检测与恢复建议,只读) | ✅ 已完成 |
| Phase 13C | Action Outcome Verification(动作结果验证,只读) | ✅ 已完成 |
| Phase 13D | Controlled Execution Architecture Review(受控执行架构评审) | ✅ 已完成 |
| Phase 13E | Safety Contract vNext Formalization(安全契约 vNext 正式化) | ✅ 已完成 |
| Phase 13E.1 | Safety vNext Gate Enforcement Hardening(门执行加固) | ✅ 已完成 |
| Phase 13F | Real Vision Validation(真实视觉验证基础) | ✅ Foundation implemented |
| Phase 13G | Knowledge Acquisition & Quality Gate(知识获取与质量门) | ✅ Foundation implemented |
| Phase 13H | Repository Governance & Multi-Machine Handoff(仓库治理与多机交接) | ✅ 已完成 |
| Phase 13I | Real Vision Client Benchmark & Calibration Baseline(真实客户端 Benchmark 与校准基线) | ✅ Phase COMPLETED / Real Vision = NOT_READY |
| Phase 13I.1 | Hybrid Local Perception & Background Capture Feasibility(混合本地感知与后台捕获可行性) | ✅ Phase COMPLETED / Real Vision = FOUNDATION_ONLY |
| Phase 13I.2 | Cross-Machine Perception Calibration & Profile Generalization(跨机校准与 Profile 泛化) | ✅ Phase COMPLETED |
| Phase 13I.3 | Cross-Machine Evidence Gate(Office 暂停检查点恢复;HOME/OFFICE 证据门) | ✅ Phase COMPLETED / Real Vision = FOUNDATION_ONLY |
| Phase 13I.4 | Segmented HP/MP Bar Perception Calibration(分段 HP/MP 条感知校准) | ✅ Phase COMPLETED / Real Vision = FOUNDATION_ONLY |
| Phase 13-J | Knowledge Graph & Semantic State Foundation(知识图谱与语义游戏状态基础) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-K | Temporal Memory & Semantic State Evolution(时间记忆与语义状态演化) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-L | Knowledge Acquisition Pipeline & Dataset Foundation(知识获取管线与数据集基础) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-M | Real Knowledge Dataset Acquisition & Validation(真实知识数据集获取与验证) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-N | Knowledge Graph Relationship & Planning Reference Foundation(知识图谱关系与规划参考基础) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-O | Context Reasoning Layer(上下文推理层) | ✅ Phase COMPLETED / Knowledge = FOUNDATION_ONLY |
| Phase 13-P | Evaluation / Simulation Layer(评估与仿真层) | ✅ Phase COMPLETED / Overall = NOT_READY |
| Phase 13-Q | Planning Reference Foundation(规划参考基础) | ✅ Phase COMPLETED / Overall = NOT_READY |

### Phase 13-N: Knowledge Graph Relationship & Planning Reference Foundation

Phase 13-N 在既有 Phase 4-E Generic Import Pipeline、Phase 13-L 数据包和 Phase 13-J/13-K 语义边界上增加了可审计关系层：`Map CONTAINS NPC`、`NPC GIVES Quest`、`Quest REQUIRES Item`、`Monster DROPS Item`、`Quest REWARDS Item`。关系保留来源 provenance 与 confidence，并对重复边、悬空端点、非法类型/端点、缺失来源和非法置信度做确定性拒绝校验。

关系查询只返回相关知识参考；`PlanningContext` 只包含当前语义状态、相关知识和可能参考，不包含 command、action、input 或 executor。当前真实脱敏快照已验证 132 条关系（CONTAINS 12、GIVES 20、REQUIRES 100）；快照中没有足够可证明的怪物掉落或任务奖励字段，因此没有臆造这两类数据。Readiness 仍由既有质量门自动保持 `Knowledge = FOUNDATION_ONLY`、Overall=`NOT_READY`。

### Phase 13-O: Context Reasoning Layer

Phase 13-O 在 `SemanticGameState`、Phase 13-K 生命周期、Phase 13-N 已校验关系和 provenance/confidence 之上生成只读 `ContextUnderstanding`。规则是确定性的：可见地图-NPC-任务关系生成 `QUEST_RELATED_CONTEXT`，可见任务-背包物品需求生成 `ITEM_QUEST_CONTEXT`；低置信度关系、冲突、未知、丢失和过期实体均保留为 uncertainty 或历史参考，不被强制提升为当前事实。

上下文置信度采用输入最小值公式：`min(state confidence, entity confidence, relation confidence)`，不制造高于输入的确定性。该层不生成 planner、command、action、input 或执行权限；`PlanningContext` 保持原样。当前 readiness 仍为 `Knowledge = FOUNDATION_ONLY`、Overall=`NOT_READY`。

### Phase 13-Q: Planning Reference Foundation

Phase 13-Q 在既有 `ContextUnderstanding`、`SemanticGameState`、TemporalState 和 `KnowledgeGraph` 之上生成只读 `PlanningReference`。它只回答“当前有哪些值得关注的信息”：任务上下文、未确认的任务条件、已知地点、相关实体、信息缺口和冲突提示；不生成 planner、action、input 或执行建议。置信度不超过最弱输入，未知、冲突、过期和低置信度关系保持不确定性，readiness 仍为 `Overall=NOT_READY`。

当前架构路线:

```text
Observation → Vision Evaluation → Knowledge → Decision → Planning
→ Human Confirmation → Permission Sandbox(MOCK_ONLY) → Reflection → Evaluation
→ Memory / Semantic Memory → Maple Context → Quest Reasoning → Perception Fusion
→ L1 Reflex(状态感知参考)
→ Vision Runtime(窗口视觉读取,结构化观察)
→ Game State Understanding(玩家/地图/实体/任务状态建模)
→ World Knowledge(外部知识 -> 地图图谱 -> 世界模型参考)
→ Spatial World Model(地图内部空间 / Portal / NPC / 任务区域)
→ Navigation Planning Reference(只规划,不执行)
→ Behavior Planning Reference(规划行为,不执行)
→ Action Proposal Reference(生成动作建议,不执行)
→ Safety Gate Reference(安全审核,不执行)
→ Action Outcome Verification(验证动作预期与实际状态变化,不执行动作)
→ Recovery Reference(检测失败并提出恢复建议,不执行)
→ Controlled Execution Architecture Review(仅评审,未启用真实输入)
→ Safety Contract vNext(仅契约,未启用)
→ Gate Enforcement Hardening(文档 Gate == 代码 Gate == 测试 Gate)
→ Real Vision Validation Gate(readiness 当前 NOT_READY,未虚报)
→ Knowledge Quality Gate(readiness 当前 FOUNDATION_ONLY,未虚报)
→ Real Vision Client Benchmark(13-I 真实客户端数据校准基线,readiness 不虚报)
→ Hybrid Local Perception(13-I.1:change detection / geometry / template / selective OCR)
→ WGC Background Capture Feasibility(13-I.1:后台/遮挡可用,minimized 不支持)
→ Cross-Machine Profile & Evidence Gate(13-I.2/13-I.3:归一化 profile、display/client 分辨率分离、HOME+OFFICE 证据)
→ Future Controlled Execution Prerequisites
→ Future Isolated Input Prototype
```

保持:`READ_ONLY_FIRST / DATA_DRIVEN / MOCK_EXECUTOR_ONLY`,禁止真实键鼠控制与输入注入。

### Phase 11-C: World Knowledge Foundation

```text
External Game Knowledge
        ↓
Map Graph
        ↓
World Model Reference
```

当前阶段只建立世界理解(地图节点/连接/关联查询),为未来 Navigation Planner 提供只读基础。
**未实现**:Navigation、Input、Automation、路径跟随、移动控制。

### Phase 11-D: Spatial World Model

```text
World Knowledge
    ↓
Spatial World Model
    ↓
Future Navigation Planner
```

当前阶段只理解空间(Portal 位置 / NPC 位置 / Monster 区域 / Quest 目标区域 / 基础空间约束)。
**不执行导航**;所有空间输出仅为 Reference,不是移动命令。

### Phase 12-A: Navigation Planning

```text
Spatial World Model
    ↓
Navigation Planning Reference
    ↓
Future Behavior Planner
```

当前阶段只规划(BFS 路径搜索 / Portal 路由 / 成本估算 / 目标解析),输出仅 Navigation Reference。
**不执行移动**;禁止 Move / Execute 按钮与任何移动控制。

### Phase 12-B: Behavior Planning

```text
Navigation Planning
    ↓
Behavior Planning Reference
    ↓
Future Action Proposal
```

当前阶段规划高层行为(NAVIGATE / INTERACT / COMBAT / COLLECT / VERIFY 等语义步骤),
输出仅 Behavior Reference。**不执行**;COMBAT_REFERENCE 不是 Attack Command,
禁止 Execute / Run 按钮与任何真实输入。

### Phase 12-C: Action Proposal

```text
Behavior Planning
    ↓
Action Proposal Reference
    ↓
Future Safety Gate
    ↓
Future Input Layer
```

当前阶段把行为步骤转换为语义动作建议(OBSERVE / NAVIGATE / INTERACT / COMBAT / COLLECT / VERIFY / WAIT),
输出仅 Action Proposal Reference。**不执行**;禁止 Execute / Run / Send 按钮与任何真实输入。

### Phase 13-A: Safety Gate

```text
Action Proposal
    ↓
Safety Gate
    ↓
Future Input Isolation
```

当前阶段对动作建议执行确定性安全审核(HP 风险 / 死亡风险 / 未知目标 / 非法动作),
输出仅 SafetyEvaluationReference(ALLOW_REFERENCE / WARNING_REFERENCE / BLOCKED_REFERENCE)。
**不执行**;审核结果不是执行许可,禁止 Approve Execute / Run / Send。

### Phase 13-B: Failure Recovery

```text
Action Proposal
    ↓
Safety Gate
    ↓
Recovery Foundation
    ↓
Future Input Isolation
```

当前阶段检测动作失败(导航超时 / 状态不匹配 / 战斗失败 / 安全阻止)并提出恢复建议
(RETRY / WAIT_OBSERVATION / REPLAN / CHANGE_TARGET / ABORT)。
输出仅 RecoveryReference。**不执行恢复**;禁止 Execute / Retry Now / Run 按钮与任何真实输入。

### Phase 13-C: Action Outcome Verification

```text
Action Proposal
→ Safety Gate
→ Action Outcome Verification
→ Failure Recovery
→ Future Virtual Input Isolation
```

当前阶段验证动作预期与实际状态变化(Before/After GameState 比较 + 结构化证据 +
SUCCESS / PARTIAL_SUCCESS / FAILED / TIMEOUT / INCONCLUSIVE / BLOCKED 判定)。
**不执行动作**;HP 下降仅作为战斗证据,不单独判定失败;所有输出仅为 Reference。

### Phase 13-D: Controlled Execution Architecture Review

```text
Action Verification
↓ Recovery
↓ Controlled Execution Architecture Review
↓ Future Safety Contract vNext
↓ Future Isolated Input Prototype
```

本阶段仅产出受控执行架构评审文档
(`docs/architecture/execution_transition/`,含 Contract Draft / Threat Model / Migration Plan / ADR-001)。
**Phase 13-D does not enable live input.** `SAFETY_MODE` 仍为 `MOCK_ONLY`,
无真实 Input / SendInput / Virtual HID / Automation;只有未来 Architecture Review
批准 Safety Contract vNext 后才允许受控原型。

### Phase 13-E: Safety Contract vNext Formalization

```text
Controlled Execution Architecture Review
↓ Safety Contract vNext(仅契约)
↓ Real Vision Validation Gate
↓ Knowledge Quality Gate
↓ Future Controlled Execution Prerequisites
↓ Future Isolated Input Prototype
```

**Safety vNext is contract only.** Runtime remains `MOCK_ONLY`.
No real input is enabled.ADR-001 已批准**架构方向**,但不授权任何真实输入;
Real Vision 当前 `NOT_READY`、Knowledge 当前 `FOUNDATION_ONLY`,
整体 Controlled Execution readiness 当前 `NOT_READY`。

### Phase 13-E.1: Safety vNext Gate Enforcement Hardening

```text
13-E Safety Contract vNext
↓ 13-E.1 Gate Enforcement Hardening
↓ 13-F Real Vision Validation
↓ 13-G Knowledge Quality Gate
↓ Future Controlled Execution Prerequisites
```

Safety vNext 文档 Gate 与 machine-readable Gate 已完全对齐
(强类型 `GateInputReference` + 10 级 gate + `GateCheckReference` 审计 + 预算/过期/杀开关全量 enforce)。
仍不启用真实输入;Overall Controlled Execution Readiness 仍为 `NOT_READY`。

### Phase 13-F: Real Vision Validation

```text
13-E.1 Gate Enforcement
↓ 13-F Real Vision Validation(只读)
↓ 13-G Knowledge Acquisition & Quality Gate
↓ Future Controlled Execution Prerequisites
```

已实现真实只读验证基础设施:Windows 窗口绑定截图 Provider、真实 OCR backend 适配
(Windows OCR / Tesseract,可配置)、ROI 配置、数据集 manifest、Benchmark 引擎、
延迟与置信度校准、Readiness 策略(自动生成,禁止手工 PASSED)、只读 smoke 脚本
`scripts/validate_real_vision.py`。

**阶段完成 ≠ Gate PASSED**:Real Vision Readiness 当前为 `NOT_READY`
(本机未验证真实 Maple 客户端;OCR backend 当前环境不可用),不虚报。

### Phase 13-G: Knowledge Acquisition & Quality Gate

```text
13-F Real Vision Foundation
↓ 13-G Knowledge Acquisition & Quality Gate
↓ Real Vision Client Benchmark
↓ Controlled Execution Prerequisite Review
↓ Future Isolated Input Prototype
```

已实现:来源 Provenance(`KnowledgeSourceReference`)、Canonical 映射(`CanonicalMapper`)、
Source Adapter(LocalStatic / ManualCurated 可运行;Wiki / Static Game Resource 预留)、
Generic Import Pipeline 复用(不新增第三套 importer)、World adapter 重构(`import_from_dataset`,
unknown relation 不静默 PORTAL)、拓扑校验、KnowledgeQualityBenchmark、KnowledgeReadinessPolicy、
自动 Readiness、versioned dataset 输出(`knowledge/versions/<version>/`)、CLI
`scripts/validate_knowledge_quality.py`。

**阶段完成 ≠ Knowledge Gate READY**:Knowledge Readiness 当前为 `FOUNDATION_ONLY`
(demo 数据 canonical 未全覆盖、无 production denominator),不虚报。

### Phase 13-I: Real Vision Client Benchmark & Calibration Baseline

```text
13-F Real Vision Foundation
↓ 13-I Real Client Benchmark(真实窗口发现 / ImageGrab 截图 / Tesseract OCR)
↓ Real Dataset(LOCAL ONLY,manifest + hashes)
↓ Map / HP/MP / Quest 实测指标
↓ Calibration Baseline(ROI / OCR / latency / confidence)
↓ Real Vision Gate(自动生成,禁止手工 PASSED)
```

已实现:只读窗口发现(`scripts/list_windows.py`)、真实截图 + OCR 校验脚本
(`scripts/validate_real_vision.py`,支持 `--window-title / --profile / --frames /
--interval / --dataset-dir / --capture-samples / --ground-truth / --ocr-lang`)、
Tesseract 真实 OCR 桥接(chi_sim+eng)、ROI 裁剪 OCR、LOCAL dataset manifest +
suggested labels、`real_vision_client_benchmark.json` 报告、WebUI 状态映射。

**阶段完成 ≠ Real Vision PASSED**:Real Vision Readiness 由真实数据自动生成,
本阶段输出以实际 Home PC 实测为准(遮挡/前台条件分别记录),不虚报。

### Phase 13-I.1: Hybrid Local Perception & Background Capture Feasibility

```text
13-I Real Client Benchmark
↓ 13-I.1 Hybrid Local Perception(OCR 不再是唯一路径)
↓ Frame/ROI Change Detection → Cheap CV → Selective OCR → Local Model
↓ WGC Background Capture Feasibility(后台/遮挡可用,minimized 不支持)
↓ Privacy Boundary(raw vision data = local private)
```

已实现:`hybrid_vision` 模块(PerceptionEvidence / FrameChangeDetector /
VisionScheduler / HpMpGeometryExtractor / MapleVisualTemplateLibrary /
KnowledgeGuidedResolver / BenchmarkPrivacySanitizer)、
`WindowsGraphicsCaptureProvider`(WGC,后台/遮挡窗口捕获)、
`scripts/benchmark_hybrid_vision.py`(逐 provider 延迟 + 隐私双输出)、
`scripts/probe_capture_conditions.py`(四条件独立测量)、
`scripts/probe_windows_graphics_capture.py` / `scripts/probe_onnx_runtime.py`。

真实 Home PC 结果(详见
`docs/architecture/vision/hybrid_local_perception.md` 与
`docs/architecture/vision/real_vision_13i1_public.json`):

- HP geometry:40/40 找到,均值 0.987(真值 1.0);MP ROI 需校准
- change detection:80ms,false/missed=0;template:4ms
- WGC:FOREGROUND / BACKGROUND_VISIBLE / BACKGROUND_OCCLUDED 可用,
  **MINIMIZED = NOT_SUPPORTED**(ImageGrab 与 WGC 均失败)
- PaddleOCR:未采用(>1GB,当前版本组合 Windows CPU 运行时错误)
- OmniParser:NOT_USEFUL_FOR_GAME_HUD;ONNX:CPU 路径可行

**Readiness 不虚报**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
Overall=NOT_READY;原始截图与真实数据仅存本地 sessions/。

### Phase 13-I.3: Cross-Machine Evidence Gate(HOME 恢复 Office 暂停检查点)

```text
13-I.2 Profile 泛化(归一化 ROI + display/client 分辨率分离)
↓ 13-I.3(Office pause 8f41cb7 → HOME resume)
↓ HOME 真实采集:FOREGROUND/BACKGROUND_VISIBLE/BACKGROUND_OCCLUDED/MINIMIZED
↓ HOME HP/MP/map 实测 + 跨机对比 + repository-safe public report
```

本轮 HOME 实测:

- 四条件:FG(WGC 166ms/ImageGrab 335ms)、BV(WGC 388ms)、OCC(WGC 392ms)、
  MINIMIZED=NOT_SUPPORTED(0 帧,与 OFFICE 25 帧 WINDOW_INVALID 一致)
- Map 判别:2 地图(射手村/射手村集市)28 查询 top1=100%、unknown=0、FP=0、
  margin≈0.86(跨分辨率归一化模板匹配)
- HP/MP:绿色分段条读取 0.128/0.074 vs 真值 1.0 → **FAIL(13-I.4 分段条模型校准)**
- Event scheduler:idle 跳过 OCR(7 帧),变化触发 template+OCR
- OFFICE evidence 原样保留(1366×768 client、WGC fg 405ms、MINIMIZED NOT_SUPPORTED、
  HP/MP/map=N/A)

公开报告:`docs/architecture/vision/real_vision_13i3_public.json`(隐私安全)。
Readiness:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
Overall=NOT_READY(不虚报)。

### Phase 13-I.4: Segmented HP/MP Bar Perception Calibration

```text
13-I.3 证实 HP/MP blocker(绿色分段条读取 0.128/0.074 vs 真值 1.0)
↓ 13-I.4 真实校准
```

真实发现:该 Unity 客户端的 HP/MP 显示实为 **cur/max 数字**(底部中央,
如 `472/472`、`MP 273/273`),而非可几何量化的条。

- 实现 `BarFillModel`(AUTO/CONTINUOUS/SEGMENTED 策略 + 段检测 + partial +
  confidence 分离 + failure taxonomy),合成测试覆盖 0/25/50/75/100/
  partial/gap/noise/border/多分辨率
- 实现 `HpMpNumericExtractor`(多尺度数字 OCR + 多数投票,真实主路径)
- 真实 HOME 结果:HP MAE=0.023(full 1.0 / mid 0.547 vs GT 1.0/0.5)、
  MP MAE=0.022(full 0.979)、检出率 100%;低状态 coverage=INSUFFICIENT(用户无法制造)
- 对比:旧 median-row 绿条误差 0.87/0.93 → 新数字路径 0.023/0.022
- 无 post-hoc 补偿、无机器名硬编码、AUTO 依据 gap 规律选择

**Readiness 不虚报**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
Overall=NOT_READY。公开报告:`docs/architecture/vision/real_vision_13i4_public.json`。
Vision closure:**VISION_CAN_PAUSE**(HP/MP 稳定可用,低状态覆盖与数字 OCR
延迟为已知限制)。

## Multi-machine Development

项目支持在 Office / Home / Future PC 之间切换开发,并支持 Git clone 与 ZIP snapshot
两种获取方式。所有 AI Agent 开工前请阅读 `AGENTS.md`(统一入口)与 `.project/CURRENT_STATE.yaml`,
完整流程见 [docs/governance/MULTI_MACHINE_WORKFLOW.md](docs/governance/MULTI_MACHINE_WORKFLOW.md)。

```text
Phase 13H = 仓库治理与多机交接(AGENTS 入口 / Governance 文档 / .project 状态 / preflight)
```

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
