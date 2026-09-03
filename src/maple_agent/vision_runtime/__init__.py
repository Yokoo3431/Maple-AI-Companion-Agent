"""Vision Runtime 层(Phase 11-A,窗口视觉读取 -> 结构化观察,只读)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.vision_runtime.antigravity import (
    AntigravityVisualSemanticProvider,
    EphemeralFrameStore,
    VisualSemanticAgreementGate,
    VisualSemanticAgreementResult,
)
from maple_agent.vision_runtime.capture import (
    MockScreenshotProvider,
    ScreenshotProvider,
)
from maple_agent.vision_runtime.detector import VisionDetector
from maple_agent.vision_runtime.models import (
    CaptureReference,
    DetectedElement,
    OcrResult,
    ScreenObservation,
    VisionFrame,
    VisionSource,
)
from maple_agent.vision_runtime.ocr import MockOCRProvider, OCRProvider
from maple_agent.vision_runtime.parser import GameStateParser
from maple_agent.vision_runtime.validator import (
    VisionRuntimeValidationResult,
    VisionRuntimeValidator,
    VisionRuntimeVerdict,
)
from maple_agent.vision_runtime.visual_semantics import (
    MockVisualSemanticProvider,
    StrategyMetrics,
    VisualCandidateType,
    VisualSemanticCandidate,
    VisualSemanticGate,
    VisualSemanticGateDecision,
    VisualSemanticProvider,
    VisualSemanticRequest,
    VisualSemanticResponse,
    VisualSemanticStatus,
    VisualSemanticTrigger,
    VisualValueSemantics,
)


def save_vision_runtime_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    frame: VisionFrame,
    observation: ScreenObservation,
    validation: str,
) -> None:
    """写入 vision_runtime_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "frame": frame.model_dump(mode="json"),
        "observation": observation.model_dump(mode="json"),
        "validation": validation,
    }
    (directory / "vision_runtime_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "CaptureReference",
    "DetectedElement",
    "GameStateParser",
    "MockOCRProvider",
    "MockScreenshotProvider",
    "OCRProvider",
    "OcrResult",
    "ScreenObservation",
    "ScreenshotProvider",
    "VisionDetector",
    "VisionFrame",
    "VisionRuntimeValidationResult",
    "VisionRuntimeValidator",
    "VisionRuntimeVerdict",
    "VisionSource",
    "AntigravityVisualSemanticProvider",
    "EphemeralFrameStore",
    "VisualSemanticAgreementGate",
    "VisualSemanticAgreementResult",
    "MockVisualSemanticProvider",
    "StrategyMetrics",
    "VisualCandidateType",
    "VisualValueSemantics",
    "VisualSemanticCandidate",
    "VisualSemanticGate",
    "VisualSemanticGateDecision",
    "VisualSemanticProvider",
    "VisualSemanticRequest",
    "VisualSemanticResponse",
    "VisualSemanticStatus",
    "VisualSemanticTrigger",
    "save_vision_runtime_trace",
]
