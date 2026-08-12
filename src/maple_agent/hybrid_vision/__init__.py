"""Hybrid Local Perception(Phase 13-I.1,只读,OCR 只是其中一种证据)。"""

from maple_agent.hybrid_vision.capture_condition import (
    classify_window_state,
    window_state_from_provider,
)
from maple_agent.hybrid_vision.change_detector import (
    ChangeDetectorBenchmark,
    FrameChangeDetector,
)
from maple_agent.hybrid_vision.hpmp import HpMpGeometryExtractor
from maple_agent.hybrid_vision.knowledge_resolution import (
    KnowledgeGuidedResolver,
)
from maple_agent.hybrid_vision.models import (
    CaptureCondition,
    ChangeResult,
    HpMpGeometryResult,
    PerceptionEvidence,
    PerceptionMethod,
    PlannedVisionTask,
    ResolutionResult,
    TemplateMatch,
)
from maple_agent.hybrid_vision.sanitizer import (
    BenchmarkPrivacySanitizer,
)
from maple_agent.hybrid_vision.schedule import VisionScheduler
from maple_agent.hybrid_vision.template import (
    MapleVisualTemplateLibrary,
)

__all__ = [
    "BenchmarkPrivacySanitizer",
    "CaptureCondition",
    "ChangeDetectorBenchmark",
    "ChangeResult",
    "FrameChangeDetector",
    "HpMpGeometryExtractor",
    "HpMpGeometryResult",
    "KnowledgeGuidedResolver",
    "MapleVisualTemplateLibrary",
    "PerceptionEvidence",
    "PerceptionMethod",
    "PlannedVisionTask",
    "ResolutionResult",
    "TemplateMatch",
    "VisionScheduler",
    "classify_window_state",
    "window_state_from_provider",
]
