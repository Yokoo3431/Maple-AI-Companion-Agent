"""VisionRuntimeValidator:屏幕观察校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.vision_runtime.models import (
    ScreenObservation,
    VisionFrame,
)


class VisionRuntimeVerdict(StrEnum):
    """视觉运行校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class VisionRuntimeValidationResult(BaseModel):
    """视觉运行校验结果。"""

    verdict: VisionRuntimeVerdict
    issues: list[str] = Field(default_factory=list)


class VisionRuntimeValidator:
    """检查帧 / 观察完整性 / 数值范围。"""

    def validate(
        self,
        frame: VisionFrame,
        observation: ScreenObservation,
    ) -> VisionRuntimeValidationResult:
        if not frame.frame_id:
            return VisionRuntimeValidationResult(
                verdict=VisionRuntimeVerdict.BLOCKED,
                issues=["missing frame id"],
            )
        if not (0 <= frame.confidence <= 1) or not (
            0 <= observation.confidence <= 1
        ):
            return VisionRuntimeValidationResult(
                verdict=VisionRuntimeVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        for value in (
            observation.hp_reference,
            observation.mp_reference,
        ):
            if value is not None and not (0 <= value <= 1):
                return VisionRuntimeValidationResult(
                    verdict=VisionRuntimeVerdict.BLOCKED,
                    issues=["hp/mp out of range"],
                )
        issues: list[str] = []
        if not observation.visible_map:
            issues.append("missing map")
        if not observation.visible_entities:
            issues.append("missing entities")
        if observation.hp_reference is None:
            issues.append("missing hp")
        if observation.mp_reference is None:
            issues.append("missing mp")
        if observation.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            VisionRuntimeVerdict.VALID
            if not issues
            else VisionRuntimeVerdict.WARNING
        )
        return VisionRuntimeValidationResult(
            verdict=verdict,
            issues=issues,
        )
