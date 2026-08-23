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
