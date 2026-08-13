# Handoff(13-I.2 → 13-I.3,IN_PROGRESS 快照)

- **Last completed phase**:13-I.2 Cross-Machine Perception Calibration & Profile Generalization
- **Current phase**:13-I.3 Office Real Vision Validation & Cross-Machine Evidence Gate(IN_PROGRESS)
- **Baseline**:`eaed0de7bd3b005de53c10580566c269687afb28`(source)
- **13-I.3 已完成的探测(OFFICE 实测)**:
  - Maple 窗口发现:title `冒险岛怀旧服` / UnityWndClass / hwnd+PID 仅本地记录
  - 窗口可见时:client 1366×768、DPI 1.0、windowed、foreground=true、rect 在主屏(副屏负坐标场景已由 client-local ROI 架构覆盖)
  - WGC 单帧 FOREGROUND 捕获:OK,~405ms,帧非黑(1368×800)
  - 窗口最小化后:WGC 25 帧全部 WINDOW_INVALID → MINIMIZED=NOT_SUPPORTED(与 13-I.1 一致)
  - 能力:pywin32 / OpenCV 5.0 / pytesseract / onnxruntime CPU / windows-capture 可用;Tesseract 二进制不可用(OCR auxiliary)
- **等待用户操作**:用户手动恢复 Maple 窗口到可见/前台后,运行:
  - 采集:`scripts/collect_office_frames.py`(待实现)或复用 WGC provider 循环采集 20–30 帧到 sessions/office_13i3_frames/
  - 评估:`scripts/benchmark_hybrid_vision.py`(待补 profile transform 到 1366×768)
  - 汇总:CrossMachineVisionBenchmark + `real_vision_13i3_public.json` + RealVisionReadinessReference
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY(13-I.3 完成时按真实结果更新,不虚报)
- **Tests / CI**:13-I.2 基线全绿(940 passed / CI 3.11+3.12 success);13-I.3 追加测试待补
- **Open issues / blockers**:
  - Maple 窗口 minimized(user action required;禁止自动恢复)
  - 真实 HP/MP/map 样本与 ground truth 待采集(需用户配合 HP/MP 状态与多地图切换)
  - background-visible/occluded 条件测试需用户手动切换窗口状态
- **Next action(恢复后)**:真实帧采集 → benchmark(profile transform)→ 跨机对比 → repository-safe 报告 → readiness → commit/push/CI
- **Files most relevant(下一 Agent)**:`src/maple_agent/real_vision/capture_manager.py`、`wgc.py`、
  `src/maple_agent/hybrid_vision/profile.py`、`hpmp.py`、`template.py`、`cross_machine.py`、
  `scripts/benchmark_hybrid_vision.py`、`.project/CURRENT_STATE.yaml`、`docs/architecture/vision/*`
