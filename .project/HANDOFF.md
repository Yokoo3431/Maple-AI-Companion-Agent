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
