"""VisionPipelineValidator:窗口 → 捕获 → 坐标 → OCR → Fusion 全链路只读校验。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel

from maple_agent.fusion import FusionService
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.providers.ocr import OCRProvider, OCRRequest, OCRResult
from maple_agent.vision.capture import CaptureProvider
from maple_agent.vision.coordinate.alignment import VisionAlignmentService
from maple_agent.vision.coordinate.mapper import VisionCoordinateMapper
from maple_agent.vision.coordinate.models import VisionFrameCoordinate
from maple_agent.vision.models import Observation, ScreenFrame
from maple_agent.window.binding import BoundWindow, WindowBindingService
from maple_agent.window.detector import WindowDetector

logger = logging.getLogger("maple_agent.validation")


class PipelineValidationError(RuntimeError):
    """全链路校验失败。"""


class PipelineStatus(BaseModel):
    """校验状态快照。"""

    window: str = "MISSING"
    capture: str = "-"
    ocr: str = "SKIPPED"
    world: str = "SKIPPED"
    overall: str = "FAILED"


class PipelineResult(BaseModel):
    """校验结果。"""

    status: PipelineStatus
    frame: ScreenFrame
    coordinate: VisionFrameCoordinate
    ocr: OCRResult | None = None
    world: WorldState | None = None
    trace_id: str = ""


class VisionPipelineValidator:
    """校验真实窗口感知链一致性(只读,无输入)。"""

    def __init__(
        self,
        detector: WindowDetector,
        capture: CaptureProvider,
        knowledge: KnowledgeProvider,
        *,
        ocr: OCRProvider | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.detector = detector
        self.capture = capture
        self.ocr = ocr
        self.knowledge = knowledge
        self.fusion = FusionService(knowledge)
        self.sessions_dir = Path(sessions_dir)
        self.last_result: PipelineResult | None = None

    def validate_once(
        self,
        *,
        trace_id: str | None = None,
        run_ocr: bool = True,
    ) -> PipelineResult:
        with TraceContext(trace_id=trace_id) as trace:
            tid = trace.trace_id
            try:
                info = self.detector.find_window(trace_id=tid)
                if info is None or info.hwnd <= 0:
                    raise PipelineValidationError("窗口缺失或句柄无效")
                if info.client_rect.width <= 0 or info.client_rect.height <= 0:
                    raise PipelineValidationError("client_rect 无效")

                bound = WindowBindingService(sessions_dir=self.sessions_dir).bind(
                    info, trace_id=tid
                )
                if hasattr(self.capture, "bound"):
                    self.capture.bound = bound
                frame, image = self.capture.capture_with_image(trace_id=tid)
                if (
                    frame.width != info.client_rect.width
                    or frame.height != info.client_rect.height
                ):
                    raise PipelineValidationError(
                        "尺寸不一致: "
                        f"frame={frame.width}x{frame.height} "
                        f"client={info.client_rect.width}x{info.client_rect.height}"
                    )

                coordinate = VisionAlignmentService().align(
                    frame_width=frame.width,
                    frame_height=frame.height,
                    bound=bound,
                    trace_id=tid,
                )
                mapper = VisionCoordinateMapper(coordinate, bound)

                ocr_result = None
                observations: list[Observation] = []
                if run_ocr and self.ocr is not None:
                    ocr_path = self._ensure_ocr_image(image, tid)
                    ocr_result = self.ocr.recognize(
                        OCRRequest(image_path=ocr_path),
                        trace_id=tid,
                    )
                    if not ocr_result.text:
                        raise PipelineValidationError("OCR 无文本")
                    observations = [
                        Observation(
                            element="ocr_text",
                            type="text",
                            raw_value=ocr_result.text,
                            normalized_value=ocr_result.text,
                            confidence=ocr_result.confidence,
                            source=ocr_result.source,
                            coordinate_space=coordinate.target_space.value,
                            mapped_bbox=mapper.map_bbox(ocr_result.bbox),
                        )
                    ]

                world = (
                    self.fusion.fuse(observations, trace_id=tid)
                    if observations
                    else None
                )
                method = getattr(self.capture, "last_capture_method", None) or "-"
                status = PipelineStatus(
                    window="CONNECTED",
                    capture=method,
                    ocr="OK" if ocr_result is not None else "SKIPPED",
                    world=(
                        "READY"
                        if world is not None and world.current_map is not None
                        else ("EMPTY" if ocr_result is not None else "SKIPPED")
                    ),
                    overall="OK",
                )
                result = PipelineResult(
                    status=status,
                    frame=frame,
                    coordinate=coordinate,
                    ocr=ocr_result,
                    world=world,
                    trace_id=tid,
                )
                self.last_result = result
                self._write_replay(tid, bound, method, coordinate, ocr_result, world)
                logger.info("pipeline validation OK: trace=%s", tid)
                return result
            except PipelineValidationError:
                raise
            except Exception as exc:
                raise PipelineValidationError(f"pipeline 校验失败: {exc}") from exc

    def _ensure_ocr_image(self, image, trace_id: str) -> str:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "ocr_input.png"
        image.convert("RGB").save(path, "PNG")
        return str(path)

    def _write_replay(
        self,
        trace_id: str,
        bound: BoundWindow,
        method: str,
        coordinate: VisionFrameCoordinate,
        ocr_result: OCRResult | None,
        world: WorldState | None,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "window": bound.window.model_dump(mode="json"),
            "capture": {
                "method": method,
                "frame_size": {
                    "width": bound.window.client_rect.width,
                    "height": bound.window.client_rect.height,
                },
            },
            "coordinate": {
                "source_space": coordinate.source_space.value,
                "target_space": coordinate.target_space.value,
                "dpi_scale": coordinate.dpi_scale,
                "offset": {"x": coordinate.offset_x, "y": coordinate.offset_y},
            },
            "ocr": {
                "text": ocr_result.text if ocr_result else "",
                "bbox": ocr_result.bbox.model_dump() if ocr_result else None,
                "mapped_bbox": None,
            },
            "fusion": {
                "map": world.current_map.name if world and world.current_map else None,
                "npcs": [npc.name for npc in world.known_npcs] if world else [],
                "monsters": [monster.name for monster in world.known_monsters] if world else [],
            },
        }
        (directory / "pipeline_validation.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
