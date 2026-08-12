"""VisionDetector:OCR 文本 -> 画面元素(确定性规则,无 AI)。"""

from __future__ import annotations

from maple_agent.vision_runtime.models import (
    DetectedElement,
    OcrResult,
    VisionFrame,
)


class VisionDetector:
    """按前缀规则把 OCR 行分类为画面元素。"""

    _PREFIX_MAPPING = {
        "地图": "MAP_LABEL",
        "MAP": "MAP_LABEL",
        "NPC": "NPC",
        "MONSTER": "MONSTER",
        "怪物": "MONSTER",
        "ITEM": "ITEM",
        "道具": "ITEM",
        "UI": "UI_ELEMENT",
        "UI_ELEMENT": "UI_ELEMENT",
    }
    _META_PREFIXES = ("HP", "MP", "任务")

    def detect(
        self,
        frame: VisionFrame,
        ocr: OcrResult,
    ) -> list[DetectedElement]:
        elements: list[DetectedElement] = []
        for line in ocr.lines:
            if ":" not in line:
                continue
            prefix, _, value = line.partition(":")
            value = value.strip()
            if not value:
                continue
            normalized = prefix.strip().upper()
            if normalized in self._META_PREFIXES:
                continue
            element_type = self._PREFIX_MAPPING.get(
                normalized,
                "UNKNOWN",
            )
            elements.append(
                DetectedElement(
                    element_type=element_type,
                    name=value,
                    confidence=ocr.confidence,
                )
            )
        return elements
