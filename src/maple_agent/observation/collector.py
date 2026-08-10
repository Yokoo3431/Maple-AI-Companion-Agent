"""ObservationCollector:截图采集 + 状态识别 + observation trace(只读)。"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from maple_agent.logging_setup import TraceContext
from maple_agent.observation.adapter import ObservationAdapter
from maple_agent.observation.models import ObservationFrame, ObservationState
from maple_agent.providers.knowledge import KnowledgeProvider


class ObservationCollector:
    """负责获取截图、构建观察状态并保存 replay。"""

    def __init__(
        self,
        adapter: ObservationAdapter,
        *,
        knowledge: KnowledgeProvider | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.adapter = adapter
        self.knowledge = knowledge
        self.sessions_dir = Path(sessions_dir)
        self.last_frame: ObservationFrame | None = None
        self.last_state: ObservationState | None = None

    def collect(
        self,
        *,
        image_path: str | Path | None = None,
        image_bytes: bytes | None = None,
        source: str = "observation",
        trace_id: str | None = None,
    ) -> ObservationFrame:
        frame = self.adapter.adapt(
            image_path=image_path,
            image_bytes=image_bytes,
            source=source,
            trace_id=trace_id,
        )
        self.last_frame = frame
        return frame

    def build_state(self, frame: ObservationFrame) -> ObservationState:
        """从 OCR 文本识别地图名与可见实体(Data Driven)。"""
        text = frame.ocr_text.strip()
        map_name = ""
        entities: list[str] = []
        observations: list[str] = []
        if text:
            observations.append(text)
            resolved = (
                self.knowledge.resolve_alias(text, trace_id=frame.frame_id)
                if self.knowledge is not None
                else None
            )
            if resolved:
                map_name = resolved
            else:
                map_name = text
            if self.knowledge is not None:
                map_info = self.knowledge.get_map(
                    map_name,
                    trace_id=frame.frame_id,
                )
                if map_info is not None:
                    try:
                        entities.extend(
                            npc.name
                            for npc in self.knowledge.get_npcs_by_map(
                                map_info.map_id,
                                trace_id=frame.frame_id,
                            )
                        )
                    except Exception:
                        pass
                    try:
                        entities.extend(
                            monster.name
                            for monster in self.knowledge.get_monsters_by_map(
                                map_info.map_id,
                                trace_id=frame.frame_id,
                            )
                        )
                    except Exception:
                        pass
        return ObservationState(
            map_name=map_name,
            visible_entities=entities,
            confidence=frame.confidence,
            observations=observations,
            timestamp=datetime.now(UTC),
        )

    def collect_and_save(
        self,
        *,
        image_path: str | Path | None = None,
        image_bytes: bytes | None = None,
        source: str = "observation",
        trace_id: str | None = None,
    ) -> ObservationState:
        with TraceContext(trace_id=trace_id) as trace:
            frame = self.collect(
                image_path=image_path,
                image_bytes=image_bytes,
                source=source,
                trace_id=trace.trace_id,
            )
            state = self.build_state(frame)
            self.last_state = state
            self._save_trace(frame, state, trace.trace_id)
            return state

    def _save_trace(
        self,
        frame: ObservationFrame,
        state: ObservationState,
        trace_id: str,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "frame_id": frame.frame_id,
            "ocr": frame.ocr_text,
            "confidence": frame.confidence,
            "entities": state.visible_entities,
            "state": state.map_name,
            "frame": frame.model_dump(mode="json"),
            "observation_state": state.model_dump(mode="json"),
            "timestamp": state.timestamp.isoformat(),
        }
        (directory / "observation_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
