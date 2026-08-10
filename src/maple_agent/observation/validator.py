"""ObservationValidator:空 frame / OCR 低置信 / 信息冲突检查(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.observation.models import ObservationFrame


class ObservationVerdict(StrEnum):
    """观察校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class ObservationValidationResult(BaseModel):
    """观察校验结果。"""

    verdict: ObservationVerdict
    issues: list[str] = Field(default_factory=list)


class ObservationValidator:
    """检查观察帧质量;不触发任何动作。"""

    def __init__(self, *, min_confidence: float = 0.5) -> None:
        self.min_confidence = min_confidence

    def validate(
        self,
        frame: ObservationFrame,
    ) -> ObservationValidationResult:
        issues: list[str] = []
        if not frame.frame_id:
            issues.append("空 frame: 缺少 frame_id")
        if not frame.image_available:
            issues.append("空 frame: 无图像数据")
        ocr_text = frame.ocr_text.strip()
        if not ocr_text:
            issues.append("OCR 文本为空")
        elif frame.confidence < self.min_confidence:
            issues.append(
                f"OCR 低置信: {frame.confidence:.2f} < {self.min_confidence:.2f}"
            )
        if frame.metadata.get("image_available") is True and not (
            frame.image_available
        ):
            issues.append("信息冲突: metadata 声明有图但实际无图")
        if frame.metadata.get("conflict") is True:
            issues.append("信息冲突: metadata 标记冲突")
        blocked = any(
            "空 frame" in issue or "信息冲突" in issue for issue in issues
        )
        if blocked:
            verdict = ObservationVerdict.BLOCKED
        elif issues:
            verdict = ObservationVerdict.WARNING
        else:
            verdict = ObservationVerdict.VALID
        return ObservationValidationResult(verdict=verdict, issues=issues)
