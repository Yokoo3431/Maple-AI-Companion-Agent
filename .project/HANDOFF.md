# Handoff(13-I.1 → 13-I.2)

- **Last completed phase**:13-I.1 Hybrid Local Perception & Background Capture Feasibility
- **Current phase**:13-I.2 Cross-Machine Perception Calibration & Profile Generalization(COMPLETED)
- **Baseline**:`9774e9bc4f6f98abd0459ce0cf5a0d803e94edf8`(source)
- **What changed**:
  - Normalized ROI + VisionProfileTransformer + Base/Machine Profile 继承(`hybrid_vision/profile.py`)
  - `maple_classic_default`(归一化)+ `office_pc_1920x1080`(继承,不复制坐标)+ home 迁移兼容
  - HP/MP 几何增强:median-row extent 抗边框污染;confidence 与 ratio 语义分离(无结果补偿)
  - 多地图模板判别:`discriminate()` top1/top2/margin + 误报保护
  - `CaptureManager`:WGC 优先 + 条件感知 failover(occluded 不静默 fallback;MINIMIZED=NOT_SUPPORTED)
  - 双显示器 client-local 坐标;window_mode 判定不再硬编码 2560 宽度
  - CrossMachineVisionBenchmark + docs(`cross_machine_vision_profile.md`)
- **OFFICE 环境**:pywin32 / opencv-python / pytesseract / onnxruntime(CPU)/ windows-capture 已装;
  Tesseract 二进制不可用(OCR 为 auxiliary);Maple 窗口当前 minimized → WGC EMPTY(MINIMIZED=NOT_SUPPORTED)
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY
- **Tests / CI**:本地全绿;GitHub Actions 3.11/3.12 待 push 后确认
- **Open issues**:OFFICE 前台/后台/遮挡真实帧采集(需用户恢复窗口);MP 真实校准;
  MINIMIZED 捕获留待 VM/Virtual Display 独立阶段
- **Next action**:Real Vision Client Benchmark(OFFICE)或 Knowledge Dataset Expansion
- **Files most relevant**:`src/maple_agent/hybrid_vision/profile.py`、`hpmp.py`、`template.py`、
  `src/maple_agent/real_vision/capture_manager.py`、`configs/vision_profiles/*`、
  `docs/architecture/vision/cross_machine_vision_profile.md`
