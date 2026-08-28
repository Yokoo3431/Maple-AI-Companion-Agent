# Phase 13-U.1f 外部架构参考审阅

本文件只记录公开仓库的架构观察，不复制第三方代码、模型、素材或自动化逻辑。审阅日期：2026-08-29。

## 可借鉴的观察架构

| 参考项目 | 可借鉴内容 | 本项目的采用边界 |
|---|---|---|
| [sonpiaz/4x-game-agent](https://github.com/sonpiaz/4x-game-agent) | 分层的本地感知、OCR、状态模型与低频 LLM fallback；其 README 说明本地感知处理大多数情况，LLM 只在卡住或需要复核时介入 | 只借鉴 cheap-first / fallback 思路；本项目不采用其 ADB、FSM 工作流、tap/swipe、自动执行或策略规划。该仓库声明 MIT，但未复制代码 |
| [ninja-otaku/Project_Aegis](https://github.com/ninja-otaku/Project_Aegis) | 外部屏幕输入、frame diff、低频 provider 调用、结构化分析和 provider 可替换边界；其 README 明确描述变化不足时跳过 API 调用 | 复用“变化门控 + 结构化 provider contract”思想；本项目继续使用已有 Windows capture，不引入网络 intake、TTS、overlay 或执行路径。该仓库声明 MIT，但未复制代码 |
| [Wintersta7e/AiGameCompanion](https://github.com/Wintersta7e/AiGameCompanion) | 独立 companion 窗口、WGC 截图和多 provider 隔离；其 README 明确将观察窗口与游戏进程分离 | 只参考隔离和 provider 配置边界；不采用 overlay hotkey、CLI 调度、截图问答或任何输入/焦点行为。该仓库声明 MIT，但未复制代码 |
| [C0k11/game-ui-cv-agent](https://github.com/C0k11/game-ui-cv-agent) | 训练/验证数据分离、结构化 UI detector、数字 OCR 与 fail-closed 质量闸 | 只参考 denominator、candidate yield 和数据质量审计；不采用其 YOLO 权重、素材、模拟器、点击、战斗或 automation 代码。仓库页面标示 MIT 入口，但 README 同时包含个人学习用途免责声明，因此不进行代码或数据复用。 |

## 不能直接借鉴的内容

- ADB、tap/swipe、keyboard/mouse、overlay hotkey、executor、workflow、combat 或 bot loop；这些与 Maple 项目当前 `MOCK_ONLY` 边界冲突。
- 第三方截图、训练数据、模型权重、OCR 原文、账号/会话数据和游戏资源；来源、许可和隐私均未纳入本项目资产。
- 第三方 provider 的自由文本响应；本项目必须先通过 `VisualSemanticResponse` schema，再按已有 `PerceptionEvidence` / `PlayerStateReference` 路径处理。

## 选型结论

采用 `LOCAL_FIRST` 作为架构默认：已有 `FrameChangeDetector` / `VisionScheduler` / ROI OCR / HP/MP extractor 优先工作；只有 local result 为 UNKNOWN、stale 或 OCR failure 且 cooldown 允许时，才开放实验性 `VisualSemanticProvider`。本次 63.05 秒真实事件门控诊断中 42 帧只调用 OCR 1 次（约 0.95 次/分钟），但 structured candidate 仍为 0；说明门控减少了重复 OCR，却没有解决当前信号/模板缺口。本机没有稳定 Antigravity/Gemini CLI 或 provider credentials，Phase 13-U.1f 不执行外部调用，当前真实决策记录为 `INSUFFICIENT_EVIDENCE`，不是 VLM 胜出。
