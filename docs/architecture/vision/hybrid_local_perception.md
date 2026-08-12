# Hybrid Local Perception(Phase 13-I.1)

> 状态:Phase 13-I.1 COMPLETED(实现 + 真实 Home PC 验证)
> 安全:SAFETY_MODE = MOCK_ONLY,只读,无输入/执行/自动化

## 1. 设计原则

不再采用「全帧截图 -> 全帧 OCR -> AI」作为主策略。目标链路:

```text
Capture
→ Frame/ROI Change Detection(80ms,无变化即停止)
→ Cheap CV(HP/MP geometry 138ms / template 4ms)
→ Selective OCR(仅 ROI 变化时,~760ms ROI)
→ Local Model / Screen Parser(可选,ONNX 路径)
→ Perception Evidence
→ Knowledge-guided Resolution(只解析,不伪造)
→ GameStateReference
```

OCR 只是其中一个 Evidence Provider,不再承担全部视觉任务。

## 2. Perception Evidence Contract

新增统一证据模型 `PerceptionEvidence`(`src/maple_agent/hybrid_vision/models.py`):

- evidence_id / evidence_type / roi / value
- canonical_candidate_id / confidence / source / timestamp / frame_id
- method(TEMPLATE / COLOR_GEOMETRY / OCR / LOCAL_CLASSIFIER /
  LOCAL_DETECTOR / SCREEN_PARSER / KNOWLEDGE_RESOLUTION)

证据可流入现有 `VisualObservation` / `PerceptionFusionReference` /
`GameStateReference` 链路,不创建第二套 GameState。

## 3. 事件驱动调度

`VisionScheduler`(`schedule.py`):

- HP/MP:COLOR_GEOMETRY 每 tick(cheap,高频)
- Map:仅 map ROI 变化时 TEMPLATE + OCR
- Quest/Dialog:仅对应 ROI 变化时 OCR
- Entity:按配置频率(不要求每帧)
- 未变化时跳过昂贵 OCR(已实测计数)

## 4. HP/MP Geometry(主路径,非 OCR)

`HpMpGeometryExtractor`(`hpmp.py`):颜色掩码 + 水平延伸计算填充率。

真实 Home PC 40 样本结果(真值 100%/100%):

| 项 | 实测 |
| --- | --- |
| HP 找到率 | 40/40 |
| HP 平均比例 | 0.9872(MAE≈0.013) |
| MP 找到率 | 40/40 |
| MP 平均比例 | 0.7467(MAE≈0.253,MP ROI 需校准) |
| 延迟 | mean 138ms / p95 145ms |

结论:HP geometry 路径有效;MP ROI 位置需 13-I.2 校准;数字 OCR 仅作 secondary。

## 5. Map 多策略对比

| 策略 | 准确率 | 延迟 | 结论 |
| --- | --- | --- | --- |
| Tesseract 全帧(baseline) | 0.0 | 2490ms | 不可用 |
| Tesseract ROI | 0.0 | 760ms | 花体字无法读取 |
| 预处理 + Tesseract | 未改善 | - | 字体为根因,非预处理 |
| OpenCV 模板(同图一致性) | 0.676 | 4ms | 快速,但需多地图区分性验证 |
| PaddleOCR | 未采用 | - | 安装 >1GB;paddleocr 3.7+paddle 3.3 在 Windows CPU 报 oneDNN/PIR 错误 |

模板库 `MapleVisualTemplateLibrary`:`configs/vision_templates/manifest.json`
只保存元数据/哈希,GitHub 不含模板图片;真实模板 local-only。

## 6. Knowledge-guided Resolution

`KnowledgeGuidedResolver`(`knowledge_resolution.py`):

- Knowledge = PRIOR / RESOLUTION CONTEXT
- 视觉证据为空 / 低置信度 / 不在候选集合 -> 一律 unresolved
- 实测 65 个 OCR 证据,resolved_count = 0(OCR 乱码未解析任何候选)
- **不变量:expected != observed;Knowledge 不能伪造视觉观察**

## 7. Background / Minimized Capture

四种条件分别实测(窗口状态由用户手动切换):

| 条件 | ImageGrab | WGC |
| --- | --- | --- |
| FOREGROUND | ✅ 100% | ✅ ~169ms |
| BACKGROUND_VISIBLE | ⚠️ 抓到遮挡内容 | ✅ ~179ms |
| BACKGROUND_OCCLUDED | ⚠️ 抓到遮挡内容 | ✅ ~152ms |
| MINIMIZED | ❌ 0% | ❌ 0 帧/20s |

结论:

- **WGC(Windows.Graphics.Capture)解决后台/遮挡窗口捕获**,不激活窗口、无 Hook
- **MINIMIZED_CAPTURE = NOT_SUPPORTED**(ImageGrab 与 WGC 均失败)
- PrintWindow 对该 Unity 客户端不可用;DXGI Desktop Duplication 仅为显示器
  捕获(桌面合成),不是可靠的最小化窗口捕获
- 未来:Virtual Display / VM Isolation Feasibility 独立阶段(不在本阶段实现)

## 8. 可选本地模型可行性

- ONNX Runtime:CPU 可用(1.28.0),GPU EP 需 onnxruntime-gpu + CUDA/cuDNN
- PaddleOCR:可行但重(>1GB + 模型下载),当前版本组合有运行时错误
- OmniParser:面向 Web UI 的 screen parser,游戏 HUD 花体字适配差,
  模型大,评审结论 **NOT_USEFUL_FOR_GAME_HUD**
- 本地 detector/classifier:未来可导出 ONNX 小型模型,完全本地推理

## 9. Privacy Boundary

- `RAW_VISION_DATA = LOCAL_PRIVATE`:真实截图/ROI 禁止 commit
- `sessions/`、`logs/` 保持 gitignore(有自动化测试守护)
- `BenchmarkPrivacySanitizer`:LOCAL RAW -> REPOSITORY SAFE
  (删除绝对路径/PID/HWND/窗口标题/截图引用/聊天文本)
- 仓库只保存:schema / sample count / hashes / 聚合指标 / failure taxonomy /
  provider names / readiness / sanitized labels
- 公开摘要见 `real_vision_13i1_public.json`

## 10. Readiness

```text
Real Vision = FOUNDATION_ONLY(真实数据,未达标)
Knowledge   = FOUNDATION_ONLY
Overall     = NOT_READY
```

HP/MP geometry 提升不等于 PASSED;完整 RealVisionReadinessPolicy 未调整。

## 11. 下一步(数据驱动)

- 13-I.2 targeted perception calibration:MP ROI 校准、HP/MP confidence 启发式、
  模板多地图区分性验证、WGC provider 正式接入
- 或 Knowledge Dataset Expansion
- 或 VM / Virtual Display Capture Feasibility(minimized 场景)
