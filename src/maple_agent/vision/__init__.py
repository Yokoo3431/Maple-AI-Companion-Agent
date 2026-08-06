"""Vision 感知基础(Phase 1.1:仅感知,无 OCR / 输入 / 控制)。"""

from maple_agent.vision.capture import (
    CaptureProvider,
    MockCaptureProvider,
    WindowsCaptureProvider,
)
from maple_agent.vision.models import Observation, ObservationRef, ScreenFrame, VisionState
from maple_agent.vision.policy import ScreenshotPolicy, enforce_capacity
from maple_agent.vision.worker import VisionWorker, VisionWorkerError, VisionWorkerState

__all__ = [
    "CaptureProvider",
    "MockCaptureProvider",
    "Observation",
    "ObservationRef",
    "ScreenFrame",
    "ScreenshotPolicy",
    "VisionState",
    "VisionWorker",
    "VisionWorkerError",
    "VisionWorkerState",
    "WindowsCaptureProvider",
    "enforce_capacity",
]
