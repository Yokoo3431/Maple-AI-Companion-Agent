# Handoff(13-H → 13-I)

- **Last completed phase**:13-H Repository Governance & Multi-Machine Handoff
- **Current phase**:13-I Real Vision Client Benchmark & Calibration Baseline(COMPLETED)
- **Baseline**:`a36532fe2a528f645f55cf4017ecd488d9d34083`(source)
- **What changed**:
  - 真实客户端 Benchmark 工具链:`scripts/list_windows.py`(只读窗口发现)、
    `scripts/validate_real_vision.py`(扩展 `--dataset-dir / --capture-samples /
    --ground-truth / --ocr-lang / --evaluate-manifest`)
  - 真实 OCR:Tesseract 5.4 桥接实现(chi_sim+eng,capability 探测,替换
    bridge-not-implemented)、`requirements-vision.txt` 增加 `pywin32`
  - Capture:PrintWindow 尝试路径(Unity 客户端返回失败 -> 诚实回退 ImageGrab)、
    窗口发现元数据(hwnd/pid/process/rect/DPI/mode/foreground)
  - 报告:`real_vision_client_benchmark.json` 组装器 + WebUI 状态映射
  - Profile:`configs/vision_profiles/home_pc_2560x1440.json`
- **Real benchmark(Home PC,真实客户端 `冒险岛怀旧服`)**:
  - 40 真实样本(30 OCR 帧 + 10 纯采集),前台条件
  - capture_success=1.0,capture latency mean 321ms / p95 335ms
  - OCR backend=tesseract(chi_sim+eng),ocr_success=1.0,mean 2490ms / p95 3881ms
  - map_accuracy=**0.0**(Tesseract 无法读取花体地图名「金银岛射手村」)
  - HP/MP numeric extraction=NOT_MEASURED(数字不可读;用户确认真值 100%)
  - Quest/UI=NOT_READY(右上「任务告知 (1/5)」部分可读)
  - Entity vision=NOT_SUPPORTED(无真实 CV detector)
  - PrintWindow=不可用(Unity GPU 合成,返回失败/黑帧);后台/最小化截图不支持
- **Readiness**:Real Vision=FOUNDATION_ONLY(真实数据,未达标)
  / Knowledge=FOUNDATION_ONLY / Overall=NOT_READY
- **Tests / CI**:本地全绿(897 collected);GitHub Actions 3.11/3.12 以 push 后实际为准
- **Open issues**:地图名/HP/MP 花体字 OCR 无法提取;后台/最小化无可靠截图方案
- **Next action**:13-I.1 targeted calibration(地图名 OCR 预处理/字体、HP/MP 数字
  提取、Quest ROI 确认),或先决策 Knowledge Dataset Expansion
- **Files most relevant**:`scripts/validate_real_vision.py`、`scripts/list_windows.py`、
  `src/maple_agent/real_vision/*`(ocr/capture/report)、
  `configs/vision_profiles/home_pc_2560x1440.json`、`.project/CURRENT_STATE.yaml`
