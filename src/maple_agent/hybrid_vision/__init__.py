"""Hybrid Local Perception(Phase 13-I.1,只读,OCR 只是其中一种证据)。"""

from maple_agent.hybrid_vision.capture_condition import (
    classify_window_state,
    window_state_from_provider,
)
from maple_agent.hybrid_vision.change_detector import (
    ChangeDetectorBenchmark,
    FrameChangeDetector,
)
from maple_agent.hybrid_vision.cross_machine import (
    CrossMachineEntry,
    CrossMachineVisionBenchmark,
    build_cross_machine_benchmark,
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
    TemplateDiscrimination,
    TemplateMatch,
)
from maple_agent.hybrid_vision.profile import (
    NormalizedROI,
    VisionProfile,
    VisionProfileRegistry,
    VisionProfileTransformer,
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
    "CrossMachineEntry",
    "CrossMachineVisionBenchmark",
    "FrameChangeDetector",
    "HpMpGeometryExtractor",
    "HpMpGeometryResult",
    "KnowledgeGuidedResolver",
    "MapleVisualTemplateLibrary",
    "NormalizedROI",
    "PerceptionEvidence",
    "PerceptionMethod",
    "PlannedVisionTask",
    "ResolutionResult",
    "TemplateDiscrimination",
    "TemplateMatch",
    "VisionProfile",
    "VisionProfileRegistry",
    "VisionProfileTransformer",
    "VisionScheduler",
    "build_cross_machine_benchmark",
    "classify_window_state",
    "window_state_from_provider",
]
