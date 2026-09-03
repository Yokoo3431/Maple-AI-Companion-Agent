"""Read-only Antigravity CLI bridge for bounded visual observation."""

from __future__ import annotations

import hashlib
import json
import os
import shlex
import shutil
import subprocess
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from maple_agent.vision_runtime.visual_semantics import (
    VisualSemanticRequest,
    VisualSemanticResponse,
    VisualSemanticStatus,
)

STRICT_VISUAL_PROMPT = """Observe only the supplied Maple game image or ROI.
Return JSON matching the existing VisualSemanticResponse schema.
Report only facts that are clearly visible in this image: MAP, HP, MP, or UI_TEXT.
Use UNKNOWN when a fact is not legible or not visible.
Do not infer hidden state from game knowledge, history, or a knowledge graph.
Do not output recommendations, commands, actions, or execution instructions.
For HP or MP, emit a candidate only when both visible current and maximum values
are reliable; provide observed_current, observed_max, normalized_ratio, and use
NORMALIZED_RATIO semantics. If maximum is not visible, return UNKNOWN instead.
"""


class EphemeralFrameStore:
    """Own temporary image bytes and expose only opaque frame tokens."""

    def __init__(self, root: str | Path | None = None) -> None:
        self._temporary_directory = (
            tempfile.TemporaryDirectory(prefix="maple_visual_")
            if root is None
            else None
        )
        self._root = Path(root) if root is not None else Path(self._temporary_directory.name)
        self._entries: dict[str, Path] = {}

    def put(self, image_bytes: bytes, *, suffix: str = ".png") -> str:
        """Store one image locally and return an opaque token, never a path."""
        if not image_bytes:
            raise ValueError("image bytes are required")
        if not suffix.startswith(".") or "/" in suffix or "\\" in suffix:
            raise ValueError("invalid image suffix")
        self._root.mkdir(parents=True, exist_ok=True)
        token = f"frame_{os.urandom(16).hex()}"
        path = self._root / f"{token}{suffix}"
        path.write_bytes(image_bytes)
        self._entries[token] = path
        return token

    def path_for(self, token: str) -> Path | None:
        """Resolve an owned token internally; callers must not log this path."""
        path = self._entries.get(token)
        return path if path is not None and path.is_file() else None

    def delete(self, token: str) -> None:
        path = self._entries.pop(token, None)
        if path is not None:
            path.unlink(missing_ok=True)

    def close(self) -> None:
        for token in tuple(self._entries):
            self.delete(token)
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None

    def __enter__(self) -> EphemeralFrameStore:
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        self.close()


class VisualSemanticAgreementResult(BaseModel):
    """Evidence-only multi-frame agreement result; it never raises confidence."""

    model_config = ConfigDict(extra="forbid")

    confirmed: bool = False
    candidate_count: int = Field(default=0, ge=0)
    agreement_count: int = Field(default=0, ge=0)
    conflict_count: int = Field(default=0, ge=0)
    confidence_bound: float | None = Field(default=None, ge=0, le=1)
    status: str = "INSUFFICIENT_DATA"


class VisualSemanticAgreementGate:
    """Require repeated identical structured observations before confirmation."""

    @staticmethod
    def evaluate(
        responses: Sequence[VisualSemanticResponse],
    ) -> VisualSemanticAgreementResult:
        valid = [
            response
            for response in responses
            if response.status is VisualSemanticStatus.VALID and response.candidates
        ]
        if len(valid) < 2:
            return VisualSemanticAgreementResult(
                candidate_count=len(valid),
                status="INSUFFICIENT_DATA",
            )
        signatures = {
            tuple(
                sorted(
                    (
                        candidate.candidate_type.value,
                        candidate.candidate_value,
                    )
                    for candidate in response.candidates
                )
            )
            for response in valid
        }
        confidence_values = [
            candidate.confidence
            for response in valid
            for candidate in response.candidates
        ]
        if len(signatures) == 1:
            return VisualSemanticAgreementResult(
                confirmed=True,
                candidate_count=len(valid),
                agreement_count=len(valid),
                confidence_bound=min(confidence_values),
                status="CONSISTENT",
            )
        return VisualSemanticAgreementResult(
            candidate_count=len(valid),
            conflict_count=len(valid),
            confidence_bound=min(confidence_values),
            status="CONFLICT",
        )


class AntigravityVisualSemanticProvider:
    """Invoke a configured CLI with one temporary image and fail closed."""

    provider_id = "antigravity_cli"

    def __init__(
        self,
        *,
        command: Sequence[str] | None = None,
        frame_store: EphemeralFrameStore | None = None,
        model_profile: str = "UNBOUND",
        timeout_seconds: float = 30.0,
    ) -> None:
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.command = tuple(command or ())
        self.frame_store = frame_store or EphemeralFrameStore()
        self.model_profile = model_profile or "UNBOUND"
        self.timeout_seconds = timeout_seconds
        self.last_call_metadata: dict[str, object] = {}

    @classmethod
    def from_environment(
        cls,
        *,
        frame_store: EphemeralFrameStore | None = None,
    ) -> AntigravityVisualSemanticProvider:
        command_text = os.environ.get("MAPLE_ANTIGRAVITY_COMMAND", "").strip()
        command = tuple(shlex.split(command_text, posix=False)) if command_text else ()
        model = (
            os.environ.get("MAPLE_ANTIGRAVITY_MODEL", "").strip()
            or os.environ.get("GEMINI_MODEL", "").strip()
            or "UNBOUND"
        )
        return cls(command=command, frame_store=frame_store, model_profile=model)

    @property
    def available(self) -> bool:
        return bool(self.command) and "{image_path}" in self.command and self._executable()

    def _executable(self) -> bool:
        executable = self.command[0] if self.command else ""
        return bool(shutil.which(executable) or Path(executable).is_file())

    def observe(self, request: VisualSemanticRequest) -> VisualSemanticResponse:
        request_hash = hashlib.sha256(
            json.dumps(request.provider_payload(), sort_keys=True).encode("utf-8")
        ).hexdigest()
        self.last_call_metadata = {
            "image_sent": False,
            "provider": self.provider_id,
            "model": request.model_profile
            if request.model_profile != "UNBOUND"
            else self.model_profile,
            "roi": request.roi,
            "request_hash": request_hash,
        }
        frame_path = self.frame_store.path_for(request.frame_reference)
        if frame_path is None:
            return self._unavailable("FRAME_TOKEN_NOT_FOUND")
        if not self.available:
            self.frame_store.delete(request.frame_reference)
            return self._unavailable("CLI_IMAGE_INPUT_UNAVAILABLE")

        started = time.perf_counter()
        command = [
            part.replace("{image_path}", str(frame_path)).replace(
                "{model}",
                request.model_profile
                if request.model_profile != "UNBOUND"
                else self.model_profile,
            )
            for part in self.command
        ]
        payload = {
            "request": request.provider_payload(),
            "prompt": STRICT_VISUAL_PROMPT,
        }
        try:
            completed = subprocess.run(
                command,
                input=json.dumps(payload, ensure_ascii=False),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
                shell=False,
            )
            elapsed_ms = round((time.perf_counter() - started) * 1000, 4)
            self.last_call_metadata.update(
                {"image_sent": completed.returncode == 0, "latency_ms": elapsed_ms}
            )
            if completed.returncode != 0:
                return self._unavailable("CLI_NONZERO_EXIT", latency_ms=elapsed_ms)
            response = VisualSemanticResponse.from_payload(
                json.loads(completed.stdout)
            )
            if response.status is VisualSemanticStatus.VALID and any(
                candidate.frame_reference != request.frame_reference
                for candidate in response.candidates
            ):
                return VisualSemanticResponse(
                    status=VisualSemanticStatus.INVALID,
                    validation_status="FRAME_REFERENCE_MISMATCH",
                    structured_output_failure_count=1,
                    latency_ms=elapsed_ms,
                )
            return response.model_copy(update={"latency_ms": elapsed_ms})
        except (json.JSONDecodeError, OSError):
            return VisualSemanticResponse(
                status=VisualSemanticStatus.INVALID,
                validation_status=VisualSemanticStatus.INVALID.value,
                structured_output_failure_count=1,
                latency_ms=round((time.perf_counter() - started) * 1000, 4),
            )
        except subprocess.TimeoutExpired:
            return self._unavailable("CLI_TIMEOUT")
        finally:
            self.frame_store.delete(request.frame_reference)

    def _unavailable(
        self,
        reason: str,
        *,
        latency_ms: float | None = None,
    ) -> VisualSemanticResponse:
        if latency_ms is not None:
            self.last_call_metadata["latency_ms"] = latency_ms
        return VisualSemanticResponse(
            status=VisualSemanticStatus.UNAVAILABLE,
            validation_status=reason,
            latency_ms=latency_ms,
        )
