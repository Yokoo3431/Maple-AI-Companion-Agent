# Handoff(13-I → 13-I.1)

- **Last completed phase**:13-I Real Vision Client Benchmark & Calibration Baseline
- **Current phase**:13-I.1 Hybrid Local Perception & Background Capture Feasibility(COMPLETED)
- **Baseline**:`ed1f87919a648a0e43cf9b1a61a5c35fdfa1139a`(source)
- **What changed**:
  - `hybrid_vision` 模块:PerceptionEvidence / FrameChangeDetector / VisionScheduler /
    HpMpGeometryExtractor / MapleVisualTemplateLibrary / KnowledgeGuidedResolver /
    BenchmarkPrivacySanitizer / CaptureCondition
  - `WindowsGraphicsCaptureProvider`(WGC,后台/遮挡窗口捕获,复用 ScreenshotProvider 契约)
  - 脚本:`benchmark_hybrid_vision.py`、`probe_capture_conditions.py`、
    `probe_windows_graphics_capture.py`、`probe_onnx_runtime.py`
  - 文档:`docs/architecture/vision/hybrid_local_perception.md` +
    `real_vision_13i1_public.json`(repository-safe)
- **Real Home PC 验证**:
  - HP geometry:40/40 找到,均值 0.987(真值 1.0);MP 均值 0.747(ROI 需校准)
  - change detection 80ms(false/missed=0);template 4ms;Tesseract ROI 760ms(0%)
  - WGC:FOREGROUND/BACKGROUND_VISIBLE/BACKGROUND_OCCLUDED 可用(~150-180ms);
    MINIMIZED=NOT_SUPPORTED(0 帧/20s)
  - PaddleOCR 未采用(paddleocr 3.7+paddle 3.3 Windows CPU 运行时错误,>1GB)
  - OmniParser NOT_USEFUL_FOR_GAME_HUD;ONNX CPU 路径可行(GPU 需 onnxruntime-gpu)
  - Knowledge resolution 实测 0 伪造(OCR 乱码未解析任何候选)
- **Readiness**:Real Vision=FOUNDATION_ONLY / Knowledge=FOUNDATION_ONLY /
  Overall=NOT_READY(不虚报,未调阈值)
- **Tests / CI**:本地全绿;GitHub Actions 3.11/3.12 以 push 后实际为准
- **Open issues**:MP ROI、HP/MP confidence 启发式、模板多地图区分性、
  minimized 捕获(Virtual Display/VM 独立阶段)
- **Next action**:13-I.2 targeted perception calibration 或 Knowledge Dataset Expansion
- **Files most relevant**:`src/maple_agent/hybrid_vision/*`、
  `src/maple_agent/real_vision/wgc.py`、`scripts/benchmark_hybrid_vision.py`、
  `docs/architecture/vision/*`、`.project/CURRENT_STATE.yaml`
