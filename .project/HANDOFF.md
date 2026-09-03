# Handoff(13-U.1h,REVIEW_REQUIRED)

- **Current phase**:13-U.1h Antigravity Visual Bootstrap & First Real Semantic Scene Closure
- **Previous completed phase**:13-U.1g HP/MP Live Signal Recalibration & First Real Player-State Closure
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Governance**:开始时 main、工作树 clean；`git fetch origin` 因 `.git/FETCH_HEAD` 权限失败，使用只读 local HEAD/origin/main hash 复核同步；未修改 `.project/BASELINE.json`
- **Reference study**:只借鉴 Project Aegis 的 frame-diff/provider isolation、4x-game-agent 的 cheap-local/low-frequency fallback、Cradle 的 screenshot/provider separation、AiGameCompanion 的 WGC/provider isolation；没有复制代码、模型、截图或执行逻辑
- **Provider preflight**:当前 PATH 未发现 `antigravity` 或 `gemini` CLI；Google Cloud CLI 不是已验证图像 provider，且其配置读取权限受阻。未读取认证状态或 credentials，未修改 OpenClaw/Hermes/Gateway/其他配置
- **Implementation**:复用既有 `VisualSemanticProvider`、`VisualSemanticRequest`、`VisualSemanticCandidate`、`VisualSemanticResponse`；新增 `AntigravityVisualSemanticProvider`、`EphemeralFrameStore` 和 `VisualSemanticAgreementGate`。临时图像使用 opaque token，provider 调用后在 finally 清理；CLI 无 shell 执行且必须声明 `{image_path}`
- **HP/MP contract**:HP/MP 仍使用 `NORMALIZED_RATIO`；新增可选 `observed_current`、`observed_max`、`normalized_ratio` 一致性校验，current-only 不进入比例证据；继续使用既有 `PlayerStateReference`
- **Real diagnostic**:未执行真实 3–5 分钟 VLM 诊断，因为没有可用 provider/image CLI；`vlm_invocations=0`、`real_image_sent=false`、真实 candidate/GT 均为 0，状态 `PENDING_PROVIDER`
- **CI contract**:新增 mock subprocess、invalid JSON/extra field/action rejection、timeout/unavailable、temporary cleanup、frame-token mismatch、multi-frame consistency tests；CI 不要求外部 provider
- **Result**:`INSUFFICIENT_EVIDENCE`; `REAL_SEMANTIC_EVIDENCE=NOT_CLOSED`; Local Map 仍 `MAP_TEMPLATE_ASSET_GAP`，Local HP/MP 仍 `INSUFFICIENT_VISUAL_SIGNAL`
- **Privacy**:未提交截图、ROI、base64、OCR raw、VLM transcript、credentials、PID/HWND、窗口标题、绝对路径或 raw session；provider 只接收临时图像路径，日志/报告不保存路径
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; NO AUTOMATION；无 keyboard/mouse/Input Provider/Executor/Planner/hooks/DLL/memory reading/client modification
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Session=`REAL_SESSION_VALIDATED_LEVEL_A` / Real Semantic Evidence=`NOT_CLOSED` / Visual Bootstrap=`INSUFFICIENT_EVIDENCE` / Overall=`NOT_READY`
- **Next action**:等待用户提供合法、已配置且支持图像输入的 Antigravity/Gemini CLI route 后，再考虑真实短诊断；不进入 Phase 13-V，不处理 Map template，不调用外部 provider，不扩展 Planner/Executor

# Handoff(13-U.1g,REVIEW_REQUIRED)

- **Current phase**:13-U.1g HP/MP Live Signal Recalibration & First Real Player-State Closure
- **Previous completed phase**:13-U.1f Hybrid Visual Semantic Perception Feasibility
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Governance**:实际仓库为 GIT 模式，开始时 main、工作树 clean、HEAD 与 origin/main 同步；未修改 .project/BASELINE.json
- **Historical path**:13-I.4 HOME 真实路径使用 2560×1440 fullscreen-windowed、底部中央专用 hp_numeric/mp_numeric ROI、Tesseract eng digit whitelist、3/5/7 倍缩放、PSM 7/13、多数投票，cur/max 解析为 normalized ratio；历史 aggregate 报告记录 HP/MP 候选存在，但低状态 ground truth 覆盖有限
- **Current audit**:Notebook 当前窗口为 1366×768，使用既有 office_pc_1920x1080 normalized profile transform；Tesseract 5.4.0.20240606，语言包 chi_sim/eng/osd 可用。原环境 TESSERACT_CMD 错误指向目录而非 executable，项目已安全回退到现有官方 executable，并识别嵌套 tessdata；没有修改全局环境
- **Bounded fix**:实时验证脚本优先复用 canonical hybrid profile 的 numeric ROI；numeric 结果仍通过既有 ScreenObservation → ExistingVisionObservationAdapter → PlayerStateReference 路径；HpMpGeometryResult 增加 candidate/parseable denominator；VisualSemanticCandidate 的 HP/MP 值语义固定为 NORMALIZED_RATIO，禁止将 472/472 等原文当比例
- **Real diagnostic**:真实只读诊断跨度 149.46 秒，30/30 capture 成功；HP numeric 调用 30、MP numeric 调用 30，HP/MP digit candidate 与 parseable candidate 均为 0，PlayerStateReference=0，SemanticState non-empty=0，CompanionSnapshot=30，异常=0；OCR aggregate success=0.5667，包含 2 次黑帧和 12 次低置信度分类
- **ROI matrix**:1 个真实临时帧，专用 HP 85×19、MP 100×28，宽 HP 752×27、MP 758×7；original/scale2/scale3/threshold 四种有限变体均为 0 个 cur/max candidate。原始帧/ROI/OCR 只保留在本机临时目录并已清理
- **Result**: GAP_IDENTIFIED；当前具体 blocker 为 HP_MP_SIGNAL_NOT_VISIBLE_OR_PROFILE_LAYOUT_MISMATCH，已排除单一 Tesseract executable 配置错误，但尚无足够证据区分布局错位与当前 UI 未暴露数字
- **Ground truth**: UNKNOWN_GT，没有产生候选，故没有人工验证样本；不得提升 REAL_SEMANTIC_EVIDENCE
- **Map/VLM boundary**:Map 仍为 MAP_TEMPLATE_ASSET_GAP，本阶段未下载或生成模板；VLM/Antigravity 未调用、未发送图片；未新增实体 detector
- **Tests**:新增 U.1g bounded tests 与诊断脚本；定向测试通过，完整 pytest、architecture contract、Ruff、diff check 需在本阶段最终提交前完成
- **Privacy**:未提交截图、ROI、OCR raw、账号/角色/chat、PID/HWND、窗口标题、绝对路径、credentials 或 raw session
- **Safety**:SAFETY_MODE=MOCK_ONLY；READ ONLY；NO INPUT；NO EXECUTION；NO AUTOMATION；无 keyboard/mouse/Input Provider/Executor/Planner/hooks/DLL/memory reading/client modification
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Companion Session=REAL_SESSION_VALIDATED_LEVEL_A / Player State Evidence=NOT_CLOSED / Real Semantic Evidence=NOT_CLOSED / Overall=NOT_READY
- **Next action**:停止在 Phase 13-U.1g；仅建议用户人工确认 HP/MP 数字是否确实可见后，再做合法的 profile/layout 复核；不要进入 Phase 13-V，不处理 Map template 或 VLM

# Handoff(13-U.1f,REVIEW_REQUIRED)

- **Current phase**:13-U.1f Hybrid Visual Semantic Perception Feasibility
- **Previous completed phase**:13-U.1e Minimal Real Semantic Evidence Closure
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Decision**:选择 `LOCAL_FIRST`；已有 FrameChangeDetector/VisionScheduler 负责变化门控，新增 `VisualSemanticProvider` 仅为严格隔离的低频实验契约。Notebook 没有稳定 Antigravity/Gemini CLI 或 provider 配置，真实决策为 `INSUFFICIENT_EVIDENCE`
- **Real sample**:U.1f 真实事件门控诊断运行 63.05 秒：42/42 capture、42 snapshots、23 次 frame change、OCR 调用 1（约 0.95 次/分钟）、OCR 非空 1、结构化 candidate 0、Map/HP/MP candidate 均 0、PerceptionEvidence 0、Resolver input 0、SemanticState 0、异常 0；OCR useful yield=0/1=0.0%，不能用 OCR 非空率代替
- **Local path**:Map candidate=0，原因仍为 `MAP_TEMPLATE_ASSET_GAP`；HP/MP candidate 各为 0，当前样本为 `INSUFFICIENT_VISUAL_SIGNAL`；没有新增模板、OCR 引擎或 detector family
- **VLM path**:只实现 schema validation、privacy-safe request metadata、fail-closed response、cooldown/scene-change/unknown gate、mock provider 和 metrics；VLM invocation=0、valid candidate=0、外部图片发送=0
- **Tests**:新增 8 项 deterministic visual semantic tests；定向 tests 与 Ruff 已通过；真实事件门控样本证明 42 帧未触发每帧 OCR，完整回归和 CI 待本阶段最终验证
- **Files**:参考审阅 `docs/architecture/vision/phase13u1f_reference_review.md`；脱敏 feasibility report `docs/architecture/vision/phase13u1f_feasibility_report.json`
- **Privacy**:未提交截图、ROI、OCR raw、VLM image/transcript、credentials、PID/HWND、绝对路径或 raw session
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; NO AUTOMATION; no planner/executor/hooks/DLL/memory reading
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Session=`REAL_SESSION_VALIDATED_LEVEL_A` / Real Semantic Evidence=`NOT_CLOSED` / Overall=`NOT_READY`
- **Next action**:保持 `REVIEW_REQUIRED`；只建议在合法且用户明确授权的条件下补齐 map template asset 或复核 HP/MP profile，并另行进行真实 VLM/短诊断；不进入 Phase 13-V

# Handoff(13-U.1e,REVIEW_REQUIRED)

- **Current phase**:13-U.1e Minimal Real Semantic Evidence Closure
- **Previous completed phase**:13-U.1d Real Vision → Semantic Evidence Gap Audit
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Minimal change**:在既有 `ExistingVisionObservationAdapter` 增加 `from_screen_observation()`；只复制已有 map/entity/quest 字段为既有 `PerceptionEvidence`，并复用 `PlayerStateParser` 把 HP/MP 放入 `PlayerStateReference`，不做知识补全或视觉推理
- **Real diagnostic**:用户手动保持客户端可见，运行 `93.39` 秒；27/27 capture 成功、27/27 frame 可用、OCR 调用 27、非空 15、map detector candidate 0、HP/MP numeric candidate 0、Adapter input 27、PerceptionEvidence 0、Resolver input 0、27/27 Snapshot 成功、异常 0
- **Root cause**:Map 侧确认 `MAP_TEMPLATE_ASSET_GAP`（仓库 template manifest/assets 缺失，live runtime 也未调用 matcher）；HP/MP 侧在匹配的 1366x768 profile-aware ROI 下无数字候选。Adapter 已能处理非空 `ScreenObservation`，但不能从空上游结果创造证据
- **Result**:`REAL_SEMANTIC_EVIDENCE=NOT_CLOSED`; 没有真实 candidate，不能宣称 map/HP/MP semantic closure；报告为 `docs/architecture/companion/phase13u1e_semantic_evidence_report.json`
- **Privacy**:未提交截图、ROI、OCR 原文、账号/角色/chat、PID/HWND、窗口标题、绝对路径、raw observation/session；临时帧已清理
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; NO AUTOMATION; no keyboard/mouse, planner, executor, hooks, DLL injection or memory reading
- **Readiness**:Companion Session=`REAL_SESSION_VALIDATED_LEVEL_A` / REAL_SEMANTIC_EVIDENCE=`NOT_CLOSED` / Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Overall=`NOT_READY`
- **Next action**:保持 `REVIEW_REQUIRED`；只建议补齐合法的 map template asset/manifest 或修复已确认 HP/MP visual signal 后重跑短诊断，不进入 Phase 13-V

# Handoff(13-U.1d,COMPLETED)

- **Last completed phase**:13-U.1d Real Vision → Semantic Evidence Gap Audit
- **Current phase**:13-U.1d(COMPLETED)
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Diagnostic**:用户手动保持 Maple 客户端可见、非最小化、前台；短诊断运行 `60.84` 秒，`41/41` 次 capture 成功、`41/41` 帧可用、`41/41` 次 OCR 返回非空结果、`41` 个 CompanionSnapshot 成功，snapshot timestamp 单调且 history append-only
- **Evidence pipeline**:VisionDetector 调用 `41` 次但地图候选 `0`；专用 HP/MP numeric detector 在本次 live runtime 未被调用且独立 probe 无数字候选；parser HP/MP 检查 `41` 次但无候选；`PerceptionEvidence=0`、`CurrentObservation.evidence=0`、Resolver 输入 `0`、resolved/unresolved `0`
- **Root cause**:断点确定为已有 OCR 输出没有满足当前 `VisionDetector` 的结构化 prefix/value 契约，且当前画面未产生可用 HP/MP 数字候选；不是 Capture、窗口绑定、Adapter 丢失或 Companion Runtime 崩溃。Adapter 保持薄层，不补造事实
- **Result**:记录 `GAP_IDENTIFIED`，没有新增 Vision V2、NPC/Monster/Item detector、第二 Evidence model、第二 Resolver、Planner 或 Executor；脱敏计数报告为 `docs/architecture/companion/phase13u1d_evidence_gap_report.json`
- **Privacy**:原始帧仅保存在临时目录并清理；未提交截图、ROI、OCR 原文、账号/角色/chat、PID/HWND、窗口标题、绝对路径或 raw observation
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; NO AUTOMATION; no keyboard/mouse, activation, hooks, DLL injection or memory reading
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Loop=`FOUNDATION` / Companion Session=`REAL_SESSION_VALIDATED_LEVEL_A` / Overall=`NOT_READY`
- **Next action**:停止在 Phase 13-U.1d；下一步只建议修复已确认的 Vision→Evidence 断点并重新做短诊断，不自动开始 Phase 13-V

# Handoff(13-U.1c,COMPLETED)

- **Last completed phase**:13-U.1c Level A HOME Real Read-only Companion Session
- **Current phase**:13-U.1c(COMPLETED)
- **GitHub**:本阶段成果将同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Real session**:用户手动保持 Maple 客户端可见、非最小化、前台；连续运行 `600.58` 秒，使用既有 `WindowsScreenshotProvider` 的 `windows/imagegrab` 路径；584 次 capture/observation 与584次 CompanionSnapshot 全部生成，capture/observation/snapshot failure=0，exception=0
- **Runtime hardening**:同一个 `CompanionRuntimeCoordinator` 与 append-only history 持续工作；history size=584，append-only=true，重复历史=0，snapshot timestamp monotonic=true；平均 observation latency=635.99ms，max=804.83ms，cognitive=0.88ms，snapshot=0.17ms
- **Semantic evidence honesty**:真实帧没有产生可进入解析器的结构化实体 evidence，resolved/unresolved/unknown 均为0，故记录 `INSUFFICIENT_EVIDENCE`；本结果证明运行链路稳定，不证明 OCR/CV accuracy，也不代表 Vision/Knowledge READY
- **Provenance**:runtime 使用实际加载的社区数据 metadata：`COMMUNITY_DATABASE` / `maple-cms-classic-community` / `cn-nostalgic-community` / `mxdc-cn-community-20260814-v1`
- **Privacy**:报告 `docs/architecture/companion/phase13u1c_real_session_report.json` 仅含脱敏聚合指标；原始帧仅存在本次进程临时目录并清理，未提交截图、ROI、OCR原文、PID/HWND、标题、账号、角色或路径
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; no keyboard/mouse, activation, automation, executor, hooks, DLL injection or memory reading
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Loop=`FOUNDATION` / Companion Session=`REAL_SESSION_VALIDATED_LEVEL_A` / Overall=`NOT_READY`
- **Next action**:停止在 Phase 13-U.1c；不自动开始 Phase 13-V，等待人工审核

# Handoff(13-U.1a,COMPLETED)

- **Last completed phase**:13-U Real Session Evidence Validation framework
- **Current phase**:13-U.1a Read-only Window Binding Compatibility Fix(COMPLETED)
- **GitHub**:本阶段成果将同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Root cause**:旧入口和 Provider 默认精确查找 `MapleStory` / `MapleStory.exe`；当前国服客户端使用 `Maplestory_Classic` / `冒险岛怀旧服`，且脚本之间默认值不一致
- **Compatibility fix**:新增唯一 `GameWindowProfile`(`maple_classic_cn`) 和 `WindowsWindowDiscovery`；对可见顶层窗口做进程/标题候选匹配、确定性排序和结构化结果输出；不激活窗口、不发送输入
- **Runtime boundary**:Existing Vision capture 仅复用新的只读绑定结果；没有修改 OCR/CV/template matching/WGC/ImageGrab 算法，也没有修改 Knowledge、Companion Runtime 或真实 Session 流程
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; no automation, executor, hooks, DLL injection, memory reading or client modification
- **Real session**:本阶段明确没有开始 Level A/B；真实 Session 仍为 pending，绑定兼容性修复不等于真实 Vision 验证
- **Validation**:新增 CN/legacy match、unknown rejection、duplicate deterministic selection、no visible window、false-positive rejection 测试；Ruff 与 diff check 通过；本机 pytest 被失效的 Python 3.12 `.venv` 启动器阻塞，CI 需完成最终回归
- **Privacy**:测试只使用脱敏候选窗口数据；没有提交真实 HWND、PID、窗口标题、截图、OCR 或 raw session
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Session=`FOUNDATION_ONLY / NOT_VALIDATED` / Overall=`NOT_READY`
- **Next action**:停止在 Phase 13-U.1a；不自动开始 Phase 13-U 真实 Session，等待人工审核和环境修复

# Handoff(13-U,COMPLETED)

- **Last completed phase**:13-T Real Companion Session Validation & Runtime Hardening
- **Current phase**:13-U Real Session Evidence Validation(COMPLETED)
- **GitHub**:本阶段成果将同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Real session gate**:Notebook 预检未检测到用户手动启动的 Maple/MapleStory 客户端，因此没有运行或模拟 Level A 10 分钟 session；`phase13u_real_session_report.json` 明确为 `REAL_SESSION_PENDING`，real duration/observation/snapshot 均为 0
- **Unified runtime boundary**:Phase 13-U 只验证已有 Existing Vision Observation → CurrentObservation → CompanionRuntimeCoordinator → CompanionSnapshot 的契约准备；没有创建 RealRuntime/ReplayRuntime、Vision V2、第二 resolver、第二 temporal memory、第二 graph 或第二套 companion loop
- **Replay baseline**:复用 Phase 13-R A-J 回放与 Phase 13-T 101-event hardening；回放用于检查确定性、history append-only、timestamp 单调和异常计数，不能解释成 Vision accuracy 或真实会话成功
- **Runtime report**:报告仅含脱敏 aggregate metrics、failure category、latency/history/lifecycle counters、provenance 状态、privacy 和 safety 状态；无截图、OCR raw、ROI、账号/角色/聊天、PID/HWND、绝对路径或 raw observation
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; READ ONLY; NO INPUT; NO EXECUTION; no keyboard/mouse, automation, executor, hooks, DLL injection, memory reading or client modification
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Companion Loop=`FOUNDATION` / Companion Session=`FOUNDATION_ONLY / NOT_VALIDATED` / Overall=`NOT_READY`
- **Known limitations**:真实 capture/OCR/CV、窗口状态、真实生命周期、真实 session memory growth 和 10 分钟连续性仍未测量；需要用户在 HOME 手动启动 Maple 后提供本地真实证据。当前不提升任何 readiness，不开始下一阶段
- **Next action**:停止在 Phase 13-U；等待 HOME Level A/B 真实 session evidence 与人工审核，后续阶段需显式授权

# Handoff(13-T,COMPLETED)

- **Last completed phase**:13-S Runtime Contract Reconciliation & Real/Replay Companion Session Validation
- **Current phase**:13-T Real Companion Session Validation & Runtime Hardening(COMPLETED)
- **GitHub**:本阶段成果将同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Unified runtime**:structured replay 与 Existing Vision Result → CurrentObservation 均进入同一个 CompanionRuntimeCoordinator；没有新增 RealRuntime/ReplayRuntime、Vision V2 或第二套认知链
- **Hardening**:101 event replay 生成 101 snapshots，history size=101，exception=0，snapshot timestamp monotonic=true，history append-only=true，duplicate history entries=0，context deterministic=true；平均 observation latency、snapshot latency、observation interval、unknown/unresolved/stale 和 peak memory 均记录在脱敏报告
- **Real session**:Notebook 未检测到 Maple 客户端，未伪造 Level A/Level B；phase13t_real_session_report.json status=REAL_SESSION_PENDING，real observation/snapshot/duration counters=0，HOME 真实验证仍 pending
- **Replay regression**:Phase 13-R A-J 全部通过，action leakage=0，confidence bound violations=0；replay hardening 不等于 Vision accuracy
- **Privacy**:只提交 aggregate metrics、capability status 和 sanitized report；无截图、OCR raw、聊天、账号/角色信息、PID/HWND、绝对路径或 raw observation
- **Safety**:SAFETY_MODE=MOCK_ONLY; READ ONLY; NO INPUT; NO EXECUTION; no keyboard/mouse, automation, hooks, DLL injection, memory reading or client modification
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Companion Loop=FOUNDATION / Companion Session=FOUNDATION_ONLY / NOT_VALIDATED / Overall=NOT_READY
- **Known limitations**:真实客户端 session 尚未在 HOME 运行；当前只能证明 replay 和 runtime hardening baseline，不能证明 real capture、OCR、window-state 或生产稳定性
- **Next action**:停止在 Phase 13-T；等待 HOME real session evidence 与人工审核，后续阶段需显式授权

---

# Handoff(13-S,COMPLETED)

- **Last completed phase**:13-R End-to-End Read-Only Companion Loop Integration
- **Current phase**:13-S Runtime Contract Reconciliation & Real/Replay Companion Session Validation(COMPLETED)
- **GitHub**:本阶段成果将同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Contract ownership**:Phase 13-J/9-D 的 MapleKnowledgeGraph 负责 canonical evidence lookup 与 alias resolution；Phase 4-A/13-N 的 KnowledgeGraph 负责 relation truth；Phase 13-M KnowledgeDatasetPackage manifest 负责 source dataset metadata；新增 RuntimeKnowledgeBundle 只组合现有图引用和 metadata，不保存第三套知识事实
- **Source-backed audit**:复用既有 Phase 4-E build_dataset，从 knowledge_dataset 包建立两个历史图视图；resolution graph 与 relationship graph 均为 400 entities，canonical overlap=400，canonical mismatch=0，missing left/right=0，alias/profile/provenance/version mismatch=0，audit valid=true
- **Provenance fix**:生产 CompanionRuntimeCoordinator 已移除 maple-v113 fixture default；无可信 metadata 时为 UNKNOWN/UNBOUND 并写入 data quality；fixture profile 仅保留在 benchmark factory；真实社区包使用 maple-cms-classic-community / cn-nostalgic-community / mxdc-cn-community-20260814-v1
- **Unified runtime**:structured replay 和 ExistingVisionObservationAdapter 产生的 CurrentObservation 均进入同一个 CompanionRuntimeCoordinator；adapter 不捕获窗口、不运行 OCR、不新增 Vision backend
- **Real session**:Notebook 未检测到 Maple 客户端，未运行伪造的 10 分钟/30–60 分钟 session；phase13s_real_session_report.json 明确为 REAL_SESSION_PENDING，HOME 真实证据待后续本地采集
- **Baseline governance**:BASELINE.json 保持 Phase 13-I.4 reference snapshot，未修改；本阶段将其 active/reference 区分记录为 GOVERNANCE_AMBIGUITY，等待人工确认
- **Privacy**:提交的报告只包含脱敏 aggregate metrics、canonical counters、profile/version/hash metadata 和 capability status；无截图、ROI、OCR raw、账号/角色/chat、PID/HWND、绝对路径或 raw observation
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Companion Loop=FOUNDATION / Companion Session=FOUNDATION_ONLY / Overall=NOT_READY
- **Safety**:SAFETY_MODE=MOCK_ONLY; READ ONLY; NO INPUT; NO EXECUTION; no automation, hooks, DLL injection or memory reading
- **Known limitations**:跨图一致性验证不是完整 Maple Knowledge 验证；真实 session 尚未在 HOME 运行；当前不新增 intelligence rule、planner、executor 或 action path
- **Next action**:停止在 Phase 13-S；等待人工审核和 HOME 真实 session evidence，后续阶段需显式授权

---

# Handoff(13-R,COMPLETED)

- **Last completed phase**:13-Q Planning Reference Foundation
- **Current phase**:13-R End-to-End Read-Only Companion Loop Integration(COMPLETED)
- **GitHub**:本阶段成果同步到 [Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Architecture**:新增 `companion_runtime/` 组合协调层；严格串联既有 Phase 13-J Resolver/Semantic State、Phase 13-K ObservationHistory/StateReducer、Phase 13-N KnowledgeGraph、Phase 13-O ContextReasoner 和 Phase 13-Q PlanningReferenceEngine，未创建第二套 resolver、memory、graph、context reasoner 或 planner
- **CompanionSnapshot**:输出脱敏的语义状态摘要、时间状态、上下文理解、PlanningReference、information gaps、uncertainties、confidence、data quality/readiness notes 和 source provenance；公开快照不含 raw evidence、OCR payload、evidence IDs、私人路径、PID/HWND 或动作字段
- **Session**:一个 `CompanionSession` 对应一个既有 append-only `ObservationHistory`；结构化 replay 支持 `VISIBLE -> LOST -> EXPIRED` 连续投影；session 仅保存 snapshot/history reference IDs，不持久化原始观测
- **Replay**:A-J 共 10 个脱敏场景，覆盖正常任务、未知 NPC、任务物品未确认、location conflict、低置信关系、时间生命周期、缺失关系、社区 provenance、多 NPC 和空证据；另有 101 observation long-run smoke
- **Benchmark**:输出 scenario pass rate、unknown/conflict preservation、temporal continuity、planning-reference consistency、provenance preservation、confidence bound violation、action leakage 和 snapshot generation，并保留 denominator；空分母为 `INSUFFICIENT_DATA`
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no keyboard/mouse, Input Provider, Executor, automation, action planning, hooks, DLL injection, memory reading or client modification
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Context Reasoning=`FOUNDATION` / Companion Loop=`FOUNDATION` / Overall=`NOT_READY`
- **Known limitations**:仅验证现有认知链的确定性组合和安全边界；有限社区 fixture 不代表完整 Maple 数据，也不代表真实客户端 OCR/视觉 readiness；没有增加新的理解规则、规划规则或执行能力
- **Next action**:停止在 Phase 13-R；后续阶段需显式授权

---

# Handoff(13-Q,COMPLETED)

- **Last completed phase**:13-P Evaluation / Simulation Layer
- **Current phase**:13-Q Planning Reference Foundation(COMPLETED)
- **GitHub**:本阶段成果同步到 [Yokoo3431/Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Architecture**:新增 `planning_reference/`，消费既有 `SemanticGameState`、Phase 13-K `TemporalState`、Phase 13-N `KnowledgeGraph` 和 Phase 13-O `ContextUnderstanding`；没有修改 Vision/OCR/CV、Resolver、Temporal Reducer、Importer、KnowledgeGraph Core 或 Safety Contract
- **Planning boundary**:新增 `PlanningReference` 仅表示值得人工关注的信息；没有 Planner、Action Planner、命令、输入、执行器、移动/战斗/任务执行路径，也没有把 Phase 13-N `PlanningContext` 改造成 Planner
- **Reference types**:支持 `QUEST_CONTEXT`、`MISSING_REQUIREMENT`、`KNOWN_LOCATION`、`RELATED_ENTITY`、`INFORMATION_GAP`、`CONFLICT_NOTICE`；它们是信息分类，不是动作类型
- **Rules**:确认地图-NPC-任务关系时生成任务上下文；任务需要的物品未在已确认背包中时使用“未确认拥有”，不写成已确认缺少；未知/不足生成信息缺口；冲突不自动择一；过期实体不进入 supporting entities；低置信度关系只保留 uncertainty
- **Confidence**:PlanningReference confidence 使用 state/context/supporting entity/relation 的最小值，不增加输入可信度；每条 reference 都包含 uncertainties 和 limitations
- **Benchmark**:复用 Phase 13-P 脱敏语义 fixture，新增 6 个 Phase 13-Q reference cases，覆盖任务、未确认条件、未知、冲突、过期、低置信度和无动作泄漏验证；无截图、OCR raw、session、个人路径或私人数据
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Context Reasoning=`FOUNDATION` / Overall=`NOT_READY`
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no keyboard/mouse, input provider, automation, executor, movement/combat/quest execution, hooks, DLL injection or memory reading
- **Known limitations**:参考层不是行为规划器；fixture 规模小且沿用有限社区快照；信息缺口只说明当前证据不足，不代表游戏事实不存在
- **Next action**:停止在 Phase 13-Q；后续阶段需显式授权

---

# Handoff(13-P,COMPLETED)

- **Last completed phase**:13-O Context Reasoning Layer
- **Current phase**:13-P Evaluation / Simulation Layer(COMPLETED)
- **GitHub**:本阶段成果同步到 [Yokoo3431/Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Architecture**:新增 `evaluation/` 只读评估入口，消费现有 `ContextReasoner`、Phase 13-K `TemporalState` 和 `SemanticGameState`；没有修改 Vision/OCR/CV、resolver、temporal reducer、importer、KnowledgeGraph core、Safety Contract 或输入相关代码
- **Compatibility**:仓库原有 Phase 5-F Agent Loop 的 `EvaluationResult/AgentMetrics` 保持兼容；Phase 13-P 使用独立的 `ContextEvaluationResult`，避免破坏旧执行评估模型，也没有创建第二套执行链
- **Benchmark**:新增脱敏结构化 `phase13p_benchmark.json`，覆盖 A-G 七类语义场景：正常任务、任务物品、未知、过期、丢失、冲突、低置信度关系；不含截图、OCR raw、session、个人路径或私人游戏数据
- **Metrics**:报告输出 context accuracy、unknown preservation、conflict preservation、false promotion、expired exclusion、lost handling、confidence bound violations，并保存每项 denominator；空分母返回 `INSUFFICIENT_DATA`/`null`，不伪造 100%
- **Temporal replay**:复用 Phase 13-K/13-O 的生命周期投影，验证 `VISIBLE -> LOST -> EXPIRED`；`semantic_context_replay_report.json` 只保存生命周期、上下文类型、active/historical 和 uncertainty count
- **Confidence**:评估记录上下文置信度与最弱输入置信度边界；任何越界计数，不自动修正或提升语义确定性
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Context Reasoning=`FOUNDATION` / Overall=`NOT_READY`
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, execution, hooks, DLL injection or memory reading
- **Known limitations**:基准是小型脱敏结构化 fixture，不代表完整 Maple 数据；评估验证确定性规则稳定性，不等于真实客户端精度或 READY；未启动任何规划或执行能力
- **Next action**:停止在 Phase 13-P；后续阶段需显式授权

---

# Handoff(13-O,COMPLETED)

- **Last completed phase**:13-N Knowledge Graph Relationship & Planning Reference Foundation
- **Current phase**:13-O Context Reasoning Layer(COMPLETED)
- **GitHub**:本阶段成果同步到 [Yokoo3431/Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Architecture boundary**:新增 `context_reasoning/` 纯只读分析包，消费现有 `SemanticGameState`、Phase 13-K 生命周期投影和唯一 Phase 13-N `KnowledgeGraph`；没有修改 Vision/OCR/CV、Generic Importer、resolver、Safety Contract、Input 相关代码，也没有创建第二套 memory/graph/planner
- **Context model**:`ContextUnderstanding` 包含 context id、语义状态引用、相关实体、相关关系、描述性 `ContextType`、置信度、reasoning trace 和 uncertainties；没有 command/action/input/executor 等字段
- **Rules**:可见 Map-NPC 的 `CONTAINS` 加 NPC-Quest 的 `GIVES` 生成 `QUEST_RELATED_CONTEXT`；可见 Quest-Inventory Item 的 `REQUIRES` 生成 `ITEM_QUEST_CONTEXT`；Location/NPC/Item 等仅产生描述性 fallback context；未知保持 `UNKNOWN_CONTEXT`
- **Temporal integration**:`TemporalState` 只是由 Phase 13-K `SemanticGameState` 派生的 lifecycle/history/stale/conflict 只读视图，不存储第二份历史；`VISIBLE` 可参与当前推理，`LOST` 仅历史参考，`EXPIRED` 不参与当前上下文，`UNKNOWN` 保留不确定性
- **Confidence**:上下文置信度使用 `min(semantic state confidence, participating entity confidence, participating relation confidence)`，四舍五入到 4 位；低于默认 `0.7` 的关系只进入 uncertainty，不进入 active related relations
- **Dataset integration**:使用现有 Phase 13-M 社区快照和 Phase 4-E importer 构建图；真实脱敏关系链已完成 `CONTAINS + GIVES → QUEST_RELATED_CONTEXT` 集成验证，relation provenance 保留 `mxdc-cn-community`
- **Benchmark**:`ContextReasoningBenchmark` 输出 total/promoted/uncertain/context-type counts、promotion rate、uncertainty rate 和 relation provenance coverage；没有输入样本时 coverage 保持 `None`
- **Tests**:Phase 13-O tests `10 passed`；覆盖 location/NPC/quest、item/quest、unknown、conflict、expired、lost、low-confidence、temporal projection、real snapshot integration、no action leakage
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Overall=`NOT_READY`
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input, automation, execution, hooks, DLL injection or memory reading
- **Known limitations**:规则集是小型确定性基础，不是 LLM/ML 推理；社区数据仍是有限快照，缺失引用和数据覆盖限制继续存在；上下文理解不等于 planner，也不输出动作建议
- **Next action**:停止在 Phase 13-O；后续阶段需显式授权

---

# Handoff(13-N,COMPLETED)

- **Last completed phase**:13-M Real Knowledge Dataset Acquisition & Validation
- **Current phase**:13-N Knowledge Graph Relationship & Planning Reference Foundation(COMPLETED)
- **GitHub**:本阶段成果同步到 [Yokoo3431/Maple-AI-Companion-Agent](https://github.com/Yokoo3431/Maple-AI-Companion-Agent)
- **Architecture**:复用唯一的 Phase 4-E Generic Import Pipeline、Phase 13-L `KnowledgeDatasetPackage`、Phase 13-G provenance/quality gate、Phase 13-J resolver 和 Phase 13-K temporal memory；没有新增 importer、第二知识图或第二 resolver
- **Relation model**:`Relation` 新增可审计 `provenance` 与 `confidence`；支持 `CONTAINS`、`GIVES`、`REQUIRES`、`DROPS`、`REWARDS`，并保留既有关系枚举兼容性。`KnowledgeGraph` 扩展到 Map/NPC/Monster/Item/Equipment/Quest/Story-Lore，并提供只读相关实体查询
- **Graph validation**:确定性拒绝重复边、悬空 source/target、非法实体类型、非法关系类型、非法端点、缺失关系 provenance 和越界 confidence；不静默修复、不覆盖观测证据
- **Planning reference**:`PlanningContext` 只保存当前 `SemanticGameState`、相关知识和可能参考，明确不含 command/action/input/executor；没有动作规划或执行路径
- **Real snapshot**:`knowledge_dataset/` 当前 50 maps / 100 NPCs / 50 quests / 200 items，新增 132 条真实快照可证明关系：`CONTAINS=12`、`GIVES=20`、`REQUIRES=100`；清单 hash 已更新为 `abfc7480502030a1a4a126d22b7613f1cb7dd1457b086576066f9392ce2db316`
- **Quality result**:package valid；entity coverage maps/NPC/quest/item 均 `1.0`；provenance coverage `1.0`；duplicate IDs `0`；alias conflicts `0`；relation duplicate edges `0`；dangling relation endpoints `0`；invalid entity/relation/endpoint `0`；missing relation provenance `0`；bounded snapshot missing references `129` 仍作为有限切片 warning 保留
- **Benchmark meaning**:132 条关系已进入同一导入器并由同一图校验器验证；没有为没有来源分母的 `DROPS` / `REWARDS` 伪造生产数据，测试 fixture 覆盖其 schema/端点规则
- **Privacy**:仅保存脱敏结构化实体、关系、manifest、canonical index 和来源字段；无截图、会话、日志、个人路径、客户端提取结果或私有数据
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Overall=`NOT_READY`；自动质量门没有因为关系层完成而虚报 READY
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, hooks, DLL injection or memory reading
- **Tests**:Phase 13-N 定向测试 `6 passed`；此前定向兼容回归 `23 passed, 1 warning`；全量 pytest `999 passed, 1 warning`；architecture contract `10 passed, 1 warning`；Ruff `All checks passed`
- **Known limitations**:当前社区快照并非官方腾讯/Nexon 数据，也不是已证明的特定国服构建；没有可验证怪物表和任务奖励字段；关系查询只提供参考，不提供动作、命令或执行器
- **Next action**:停止在 Phase 13-N；后续阶段需显式授权

---

# Handoff(13-M,COMPLETED)

- **Last completed phase**:13-L Knowledge Acquisition Pipeline & Dataset Foundation
- **Current phase**:13-M Real Knowledge Dataset Acquisition & Validation(COMPLETED)
- **Source qualification**:使用 [冒险岛怀旧服小册子](https://mxdc.dvg.cn/) 的公开中文资料，登记为 `COMMUNITY_DATABASE`；这是社区整理资料，不宣称为官方腾讯/Nexon 数据，也不把它当作现有 `maple-v113` profile
- **Dataset package**:`knowledge_dataset/`，版本 `mxdc-cn-community-20260814-v1`，server profile `cn-nostalgic-community`，内容 hash `3563ca50e176b8eec534a5fd15a0d16c073045b04400761d77ae80fa460ead27`
- **Dataset scope**:50 maps / 100 NPCs / 50 quests / 200 items；monsters/equipment/story_lore/relations 当前为空数组，属于有限验证切片而非完整生产库
- **Validation**:计数覆盖率均为 `1.0`，provenance coverage `1.0`，duplicate IDs `0`，alias conflicts `0`，bounded-snapshot missing references `129`（作为有限切片警告保留，未伪装为全量覆盖），invalid relations `0`
- **Architecture**:
  - `KnowledgeDatasetPackage` 读取 manifest、实体文件、canonical index 并校验 hash、计数、ID、别名、引用和 provenance
  - `KnowledgeDatasetPackageAdapter` 复用现有 Phase 13-G `KnowledgeSourceAdapter`；导入仍进入唯一的 Phase 4-E Generic Import Pipeline
  - source-ID→canonical-ID 映射解决跨类型同名歧义，不新增 resolver；CLI 同时验证 Phase 13-J resolver 与 Phase 13-K temporal memory 兼容性
  - `scripts/validate_phase13m_dataset.py` 输出 package validation、import manifest、benchmark 和 readiness
- **Benchmark**:实际导入 400 entities；entity coverage `1.0`，canonical ID coverage `1.0`，provenance/profile/version binding 均 `1.0`，unresolved reference rate `0.0`，validation score `0.9886`；alias coverage 为 `N/A`，因为快照没有可信别名分母
- **Privacy**:仅提交结构化 ID、中文名称、最小语义引用、canonical index 和 provenance；不含截图、图标/资源 URL、客户端文件、原始会话、日志、私有路径或个人数据
- **Readiness**:Real Vision=`FOUNDATION_ONLY` / Knowledge=`FOUNDATION_ONLY` / Semantic State=`FOUNDATION` / Temporal Memory=`FOUNDATION` / Overall=`NOT_READY`；readiness 由现有门自动保持，未因有限数据包虚报 READY
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, hooks, DLL injection or memory reading
- **Tests**:full pytest `993 passed, 1 warning`; architecture contract `10 passed, 1 warning`; Phase 13-M tests `6 passed`; Ruff `All checks passed`
- **Known limitations**:社区来源的确切服务器构建未被官方证明；地图/NPC/任务/道具只是定量切片；缺失引用 129 个；没有生产级全量知识、爬虫、逆向、客户端提取或运行时网络 adapter
- **Next action**:停止在 Phase 13-M；后续阶段需显式授权

---

# Handoff(13-L,COMPLETED)

- **Last completed phase**:13-K Temporal Memory & Semantic State Evolution
- **Current phase**:13-L Knowledge Acquisition Pipeline & Dataset Foundation(COMPLETED)
- **Baseline semantics**:`.project/BASELINE.json` remains on its 13-I.4 source commit; no recursive metadata commit created
- **What changed**:
  - versioned dataset metadata now carries `dataset_version`, `game_profile`, `server_profile`, source provenance, content hash and adapter identity/version
  - existing Phase 13-G `KnowledgeSourceAdapter` boundary is formalized with adapter identity/version; Manual Curated / Local Static / offline Wiki / Static Game Resource adapters remain offline-only and no crawler, reverse engineering or client extraction was added
  - existing Phase 4-E Generic Import Pipeline remains the only import path; equipment, quest and story/lore records now flow through the same importer, canonical mapper and Phase 13-J resolver compatibility boundary
  - Knowledge Quality Benchmark now reports entity coverage, canonical coverage, alias coverage, missing-reference count/rate, conflict and provenance coverage; metrics with no honest denominator remain unavailable instead of being fabricated
  - versioned dataset records and acquisition traces write sanitized metadata only; raw source packets, screenshots, sessions, private paths and personal data are not persisted
  - design record: `docs/architecture/knowledge/phase13l_design.md`
  - tests: `tests/unit/test_phase13l_dataset_foundation.py` covers versioning, provenance, adapter contract, quality metrics, privacy sanitization and resolver compatibility
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY(自动生成;本阶段不虚报为 READY)
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, hooks, DLL injection or memory reading
- **Tests**:full pytest `987 passed, 1 warning`; architecture contract `10 passed, 1 warning`; Ruff `All checks passed`; initial uncorrected local OCR environment had 1 failure because inherited `TESSDATA_PREFIX` pointed one level above the actual `tessdata` directory, corrected only in the test process and no system setting changed
- **Next action**:停止在 Phase 13-L；后续阶段需显式授权

---

# Handoff(13-K,COMPLETED)

- **Last completed phase**:13-J Knowledge Graph & Semantic State Foundation
- **Current phase**:13-K Temporal Memory & Semantic State Evolution(COMPLETED)
- **Baseline semantics**:`.project/BASELINE.json` remains on its 13-I.4 source commit; no recursive metadata commit created
- **What changed**:
  - append-only `ObservationHistory` stores timestamp, evidence, resolution, confidence and source without pruning
  - `StateReducer` performs deterministic recency-weighted confidence aggregation over multiple observations
  - explicit `VISIBLE / LOST / UNKNOWN / EXPIRED` lifecycle projection with stale and expiry thresholds
  - conflict detection for competing single-value location evidence; nearby multi-entity observations remain valid
  - unknown evidence remains an explicit `UNKNOWN` reference and is never converted into absence
  - sanitized `semantic_memory_trace.json` stores transition summaries only, without screenshots, private paths or raw session values
  - design record: `docs/architecture/knowledge/phase13k_design.md`
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY(自动生成)
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, hooks, injection or memory reading
- **Tests**:full pytest `981 passed, 1 warning`; architecture contract `10 passed, 1 warning`; Ruff passed
- **Next action**:停止在 Phase 13-K；后续阶段需显式授权

---

# Handoff(13-J,COMPLETED)

- **Last completed phase**:13-I.4 Segmented HP/MP Perception Calibration
- **Current phase**:13-J Knowledge Graph & Semantic State Foundation(COMPLETED)
- **Baseline semantics**:`.project/BASELINE.json` remains on its 13-I.4 source commit; no recursive metadata commit created
- **What changed**:
  - canonical Map/NPC/Monster/Item/Equipment/Quest/Story-Lore entities with aliases, version and Phase 13-G-aligned provenance
  - deterministic `Perception Evidence → Resolution Candidate` resolver; observations remain immutable and unresolved/conflict cases remain explicit
  - read-only `CurrentObservation` and `SemanticGameState`, with location/player status/nearby entities/quest context/inventory references
  - Phase 4-E generic importer extended for the new entity types; no second importer framework
  - sanitized Phase 13-J fixture, semantic quality metrics and automatic readiness evaluation
  - design record: `docs/architecture/knowledge/phase13j_design.md`
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY(自动生成)
- **Safety**:`SAFETY_MODE=MOCK_ONLY`; no input provider, keyboard/mouse control, automation, hooks, injection or memory reading
- **Tests**:定向 Phase 13-J tests、architecture contract、full pytest 与 Ruff 均在项目 `.venv` 中验证
- **Next action**:停止在 Phase 13-J；后续阶段需显式授权

---

# Handoff(13-I.3 → 13-I.4,COMPLETED)

- **Last completed phase**:13-I.3 Cross-Machine Evidence Gate
- **Current phase**:13-I.4 Segmented HP/MP Bar Perception Calibration(COMPLETED)
- **Baseline**:`61e3cf8bcd3b5a2d262e8a15090b38848e438188`(source)
- **What changed**:
  - `BarFillModel`(`hybrid_vision/bar_model.py`):AUTO/CONTINUOUS/SEGMENTED 策略、
    段检测(run-length/gap 规律)、partial segment、confidence 与 ratio 分离、
    failure taxonomy;无 post-hoc 补偿、无机器名硬编码
  - `HpMpNumericExtractor`(`hpmp.py`):多尺度数字 OCR + 多数投票(cur/max 解析),
    该 Unity 客户端真实主路径
  - profiles:hp/mp numeric ROI(归一化校准元数据)+ legacy 迁移扩展
  - benchmark:`--hpmp-mode geometry|numeric|auto`、实际帧尺寸自动探测
  - `scripts/build_hpmp_13i4_report.py` + `docs/architecture/vision/real_vision_13i4_public.json`
  - README 重复 Phase 13-I.2 修复 + 13-I.4 行/章节;测试(test_hpmp_13i4.py 24 项)
- **真实发现**:该 Unity 客户端 HP/MP 显示为 **cur/max 数字**(底部中央,
  `472/472`、`MP 273/273`),非几何条;数字 OCR 为正确主路径
- **真实 HOME 结果(REAL_HOME)**:
  - HP:full 1.0(5/5)、mid 0.5466(5/5,GT≈0.5 用户近似);MAE=0.0233
  - MP:full 0.9785(5/5,GT 1.0);mid 0.7584(5/5,GT UNKNOWN,仅检出)
  - 检出率 100%;旧 median-row 绿条误差 0.87/0.93 → 新数字路径 0.023/0.022
  - 低状态 coverage=INSUFFICIENT(用户无法方便制造,诚实记录)
- **合成测试**:0/25/50/75/100/partial/gap/noise/border/多分辨率;
  SYNTHETIC 不计入真实 readiness
- **Vision closure**:VISION_CAN_PAUSE(HP/MP 稳定可用;低状态覆盖与数字 OCR
  延迟 ~1.65s 为已知限制)
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
  Overall=NOT_READY(自动生成)
- **Tests / CI**:本地全绿;CI 3.11/3.12 以 push 后实际为准
- **Next action(推荐)**:Knowledge Dataset Expansion(优先);如继续视觉,
  13-I.5 仅做低状态覆盖 + 数字 OCR 延迟优化;minimized 留 VM/Virtual Display
- **Files most relevant**:`src/maple_agent/hybrid_vision/bar_model.py`、
  `hpmp.py`、`scripts/benchmark_hybrid_vision.py`、`scripts/build_hpmp_13i4_report.py`、
  `configs/vision_profiles/*`、`docs/architecture/vision/*`、`.project/CURRENT_STATE.yaml`
