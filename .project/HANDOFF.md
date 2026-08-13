# Handoff(13-I.3 → 13-I.4,COMPLETED)

- **Last completed phase**:13-I.3 Cross-Machine Evidence Gate
- **Current phase**:13-I.4 Segmented HP/MP Bar Perception Calibration(COMPLETED)
- **Baseline**:`bf83ba028211c810159678644fdb281b15224923`(source;13-I.4 主提交 hash 见 BASELINE)
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
