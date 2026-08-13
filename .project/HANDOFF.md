# Handoff(13-I.2 → 13-I.3,COMPLETED)

- **Last completed phase**:13-I.2 Cross-Machine Perception Calibration & Profile Generalization
- **Current phase**:13-I.3 Cross-Machine Evidence Gate(COMPLETED,从 OFFICE pause `8f41cb7` 恢复)
- **Baseline**:`bf83ba028211c810159678644fdb281b15224923`(source)
- **Office evidence(REAL_OFFICE,原样保留)**:
  - Maple 窗口发现:title 冒险岛怀旧服 / UnityWndClass;client≈1366×768、DPI 1.0、windowed
  - WGC 单帧 FOREGROUND:OK ~405ms;最小化:25 帧全部 WINDOW_INVALID → MINIMIZED=NOT_SUPPORTED
  - Tesseract 二进制不可用(OCR auxiliary)
- **Home evidence(REAL_HOME,2026-08-13 新采集)**:
  - 四条件:FG(WGC 166ms / ImageGrab 335ms,20 帧)、BV(WGC 388ms,10 帧)、
    OCC(WGC 392ms,10 帧)、MINIMIZED=NOT_SUPPORTED(0 帧)
  - Map:2 地图(射手村 / 射手村集市)28 查询 top1=1.0、unknown=0、FP=0、margin≈0.86
  - HP/MP:绿色分段条读取 0.128/0.074 vs 真值 1.0 → FAIL(blocker:分段条模型,需 13-I.4)
  - Event scheduler:idle 7 帧跳过 OCR,变化触发 template+OCR
  - 窗口模式切换实测:WGC 帧 1922×1112(client≈1920×1080 windowed),ROI 按实际尺寸换算
- **Profile 修正**:`office_pc_1920x1080.json` resolution 改为 GAME CLIENT 1366×768,
  `display_resolution=1920×1080`(仅元数据);base `maple_classic_default` HP/MP ROI 按
  绿色条位置更新(底部中央)
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
  Overall=NOT_READY(自动生成,不虚报)
- **Tests / CI**:13-I.3 追加测试(display/client 分离、provenance、public report 隐私、
  条件矩阵、N/A 不伪造);本地全绿;CI 3.11/3.12 以 push 后实际为准
- **Open issues / blockers**:
  - HP/MP 绿色分段条 bar-model 校准(13-I.4 focused visual fix)
  - minimized 捕获(VM/Virtual Display 独立阶段)
- **Next action**:A. 13-I.4 focused visual fix / B. Knowledge Dataset Expansion /
  C. VM / Virtual Display Capture Feasibility(禁止 Input Provider)
- **Files most relevant**:`scripts/collect_real_vision_frames.py`、
  `scripts/benchmark_hybrid_vision.py`、`scripts/trace_event_driven_vision.py`、
  `scripts/build_cross_machine_summary.py`、`src/maple_agent/hybrid_vision/*`、
  `configs/vision_profiles/*`、`docs/architecture/vision/*`、`.project/CURRENT_STATE.yaml`
