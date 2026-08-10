"""ObservationAdapter:统一真实观察接口(image/frame -> ObservationFrame,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.observation.models import ObservationFrame
from maple_agent.providers.ocr import OCRProvider, OCRRequest


class ObservationAdapter:
    """输入 image/frame,输出标准化 ObservationFrame;禁止任何动作。"""

    def __init__(
        self,
        *,
        ocr: OCRProvider | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.ocr = ocr
        self.sessions_dir = Path(sessions_dir)
        self.last_frame: ObservationFrame | None = None

    def adapt(
        self,
        *,
        image_path: str | Path | None = None,
        image_bytes: bytes | None = None,
        source: str = "observation",
        trace_id: str | None = None,
    ) -> ObservationFrame:
        """把图像输入转换为 ObservationFrame(OCR 可选)。"""
        with TraceContext(trace_id=trace_id) as trace:
            image_available = image_path is not None or image_bytes is not None
            metadata: dict = {}
            ocr_text = ""
            confidence = 0.0
            request_path: str | Path | None = image_path
            if image_bytes is not None:
                tmp_dir = self.sessions_dir / "tmp"
                tmp_dir.mkdir(parents=True, exist_ok=True)
                request_path = tmp_dir / f"{new_id()}.png"
                request_path.write_bytes(image_bytes)
                metadata["image_bytes_saved"] = True
            if image_available and self.ocr is not None:
                result = self.ocr.recognize(
                    OCRRequest(image_path=str(request_path or "")),
                    trace_id=trace.trace_id,
                )
                ocr_text = result.text
                confidence = result.confidence
                metadata["ocr_source"] = result.source
                metadata["ocr_schema_version"] = result.schema_version
            frame = ObservationFrame(
                frame_id=new_id(),
                timestamp=datetime.now(UTC),
                source=source,
                image_available=image_available,
                ocr_text=ocr_text,
                confidence=round(confidence, 4),
                metadata=metadata,
            )
            self.last_frame = frame
            return frame
