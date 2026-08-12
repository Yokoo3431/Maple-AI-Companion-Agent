"""GameStateParser:画面元素 + OCR -> ScreenObservation(确定性解析)。"""

from __future__ import annotations

import re

from maple_agent.vision_runtime.models import (
    DetectedElement,
    OcrResult,
    ScreenObservation,
    VisionFrame,
)


class GameStateParser:
    """把帧与 OCR 解析为结构化屏幕观察。"""

    _QUEST_RE = re.compile(r"任务\s*[:：]\s*([^\n]+)")

    def parse(
        self,
        frame: VisionFrame,
        ocr: OcrResult,
        detected: list[DetectedElement],
    ) -> ScreenObservation:
        visible_map = next(
            (
                element.name
                for element in detected
                if element.element_type == "MAP_LABEL"
            ),
            "",
        )
        visible_entities = [
            element.name
            for element in detected
            if element.element_type in ("NPC", "MONSTER", "ITEM")
        ]
        ui_elements = [
            element.name
            for element in detected
            if element.element_type == "UI_ELEMENT"
        ]
        hp = self._ratio(ocr.text, "HP")
        mp = self._ratio(ocr.text, "MP")
        quests = self._quests(ocr.text)
        confidence = round(
            min(1.0, (frame.confidence + ocr.confidence) / 2),
            4,
        )
        return ScreenObservation(
            visible_map=visible_map,
            visible_entities=list(dict.fromkeys(visible_entities)),
            ui_elements=list(dict.fromkeys(ui_elements)),
            hp_reference=hp,
            mp_reference=mp,
            quest_reference=list(dict.fromkeys(quests)),
            confidence=confidence,
        )

    @staticmethod
    def _ratio(text: str, key: str) -> float | None:
        match = re.search(
            rf"{key}\s*[:：]?\s*(\d+(?:\.\d+)?)\s*%?",
            text,
            re.IGNORECASE,
        )
        if match is None:
            return None
        raw = float(match.group(1))
        ratio = raw / 100 if raw > 1 else raw
        return round(min(1.0, max(0.0, ratio)), 4)

    @staticmethod
    def _quests(text: str) -> list[str]:
        quests: list[str] = []
        for match in GameStateParser._QUEST_RE.finditer(text):
            quests.extend(
                part.strip()
                for part in match.group(1).split(",")
                if part.strip()
            )
        return quests
