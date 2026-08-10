"""Reflection 闭环反思层(Phase 5-D,只读,禁止真实执行)。"""

from maple_agent.reflection.engine import ReflectionEngine
from maple_agent.reflection.memory import ReflectionMemory
from maple_agent.reflection.models import (
    FailureType,
    ReflectionResult,
    ReflectionState,
)
from maple_agent.reflection.trigger import ReflectionTrigger, TriggerDecision

__all__ = [
    "FailureType",
    "ReflectionEngine",
    "ReflectionMemory",
    "ReflectionResult",
    "ReflectionState",
    "ReflectionTrigger",
    "TriggerDecision",
]
