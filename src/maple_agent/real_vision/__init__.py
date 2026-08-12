"""Real Vision Validation 层(Phase 13-F,真实只读视觉验证,无输入)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.real_vision.benchmark import RealVisionBenchmark
from maple_agent.real_vision.capture import WindowsScreenshotProvider
from maple_agent.real_vision.dataset import VisionValidationDataset
from maple_agent.real_vision.models import (
    CaptureStatus,
    ConfidenceBucket,
    RealVisionBenchmarkResult,
    RealVisionReadinessPolicy,
    VisionGroundTruth,
    VisionValidationSample,
)
from maple_agent.real_vision.ocr import (
    RealOCRProvider,
    TesseractOCRAdapter,
    WindowsOCRAdapter,
)
from maple_agent.real_vision.profile import (
    VisionROIProfile,
    load_vision_profiles,
)
from maple_agent.real_vision.readiness import build_real_vision_readiness


def save_real_vision_validation_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    provider: dict,
    window: dict,
    dataset: dict,
    metrics: RealVisionBenchmarkResult,
    readiness: dict,
    validation: str,
) -> None:
    """写入 real_vision_validation_trace.json(不存截图二进制)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "provider": provider,
        "window": window,
        "dataset": dataset,
        "metrics": metrics.model_dump(mode="json"),
        "readiness": readiness,
        "validation": validation,
    }
    (directory / "real_vision_validation_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "CaptureStatus",
    "ConfidenceBucket",
    "RealOCRProvider",
    "RealVisionBenchmark",
    "RealVisionBenchmarkResult",
    "RealVisionReadinessPolicy",
    "TesseractOCRAdapter",
    "VisionGroundTruth",
    "VisionROIProfile",
    "VisionValidationDataset",
    "VisionValidationSample",
    "WindowsOCRAdapter",
    "WindowsScreenshotProvider",
    "build_real_vision_readiness",
    "load_vision_profiles",
    "save_real_vision_validation_trace",
]
