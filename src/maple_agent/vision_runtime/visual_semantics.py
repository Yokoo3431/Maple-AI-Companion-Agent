"""Experimental visual-semantic provider contract (read-only, no network)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from enum import StrEnum
from typing import Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

from maple_agent.hybrid_vision.models import ChangeResult


class VisualCandidateType(StrEnum):
    """Bounded categories for visible facts, not actions."""

    MAP = "MAP"
    HP = "HP"
    MP = "MP"
    UI_TEXT = "UI_TEXT"


class VisualValueSemantics(StrEnum):
    """Meaning of candidate_value; HP/MP never accept ambiguous text."""

    AUTO = "AUTO"
    VISIBLE_TEXT = "VISIBLE_TEXT"
    NORMALIZED_RATIO = "NORMALIZED_RATIO"


class VisualSemanticStatus(StrEnum):
    """Provider result state; unavailable/invalid never becomes evidence."""

    VALID = "VALID"
    UNKNOWN = "UNKNOWN"
    INVALID = "VLM_OUTPUT_INVALID"
    UNAVAILABLE = "PROVIDER_UNAVAILABLE"


class VisualSemanticTrigger(StrEnum):
    """Reasons allowed to open the low-frequency visual fallback gate."""

    INITIAL_UNKNOWN = "INITIAL_UNKNOWN"
    SCENE_CHANGE = "SCENE_CHANGE"
    MAP_REGION_CHANGE = "MAP_REGION_CHANGE"
    PERSISTENT_UNKNOWN = "PERSISTENT_UNKNOWN"
    OCR_FAILURE = "OCR_FAILURE"
    STALE_EVIDENCE = "STALE_EVIDENCE"
    MANUAL_PROBE = "MANUAL_PROBE"
    NO_TRIGGER = "NO_TRIGGER"
    LOCAL_EVIDENCE_SUFFICIENT = "LOCAL_EVIDENCE_SUFFICIENT"
    COOLDOWN_ACTIVE = "COOLDOWN_ACTIVE"
    COOLDOWN_EXPIRED = "COOLDOWN_EXPIRED"


_SAFE_ROIS = frozenset({"full_frame", "map_label", "hp", "mp", "ui_text"})
_PRIVATE_REFERENCE = re.compile(
    r"(?:[A-Za-z]:[\\/]|\\\\|/Users/|/home/|://|\.(?:png|jpg|jpeg|bmp|webp)\b)",
    re.IGNORECASE,
)
_ACTION_PREFIX = re.compile(
    r"^\s*(?:click|move(?:\s+to)?|attack|use(?:\s+item)?|execute|send\s+key|"
    r"点击|移动到?|攻击|使用(?:物品)?|执行|发送按键)",
    re.IGNORECASE,
)


def _assert_action_free_text(value: str) -> str:
    if _ACTION_PREFIX.search(value):
        raise ValueError("visual semantic output contains action semantics")
    return value


class VisualSemanticRequest(BaseModel):
    """Privacy-safe request metadata; image transport is provider-owned."""

    model_config = ConfigDict(extra="forbid")

    provider_profile: str
    model_profile: str = "UNBOUND"
    frame_reference: str
    roi: str = "full_frame"
    trigger: VisualSemanticTrigger
    requested_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    prompt_version: str = "visible-facts-v1"

    @model_validator(mode="after")
    def validate_safe_reference(self) -> VisualSemanticRequest:
        if not self.provider_profile.strip():
            raise ValueError("provider profile is required")
        if not self.frame_reference.strip() or _PRIVATE_REFERENCE.search(
            self.frame_reference
        ):
            raise ValueError("frame reference must be an opaque, privacy-safe token")
        if self.roi not in _SAFE_ROIS:
            raise ValueError("unsupported ROI")
        return self

    def provider_payload(self) -> dict[str, str]:
        """Return only bounded metadata; never serializes raw pixels or OCR."""
        return {
            "provider_profile": self.provider_profile,
            "model_profile": self.model_profile,
            "frame_reference": self.frame_reference,
            "roi": self.roi,
            "trigger": self.trigger.value,
            "prompt_version": self.prompt_version,
        }


class VisualSemanticCandidate(BaseModel):
    """A structured visible fact candidate, not a game action."""

    model_config = ConfigDict(extra="forbid")

    provider: str
    model: str = "UNBOUND"
    frame_reference: str
    candidate_type: VisualCandidateType
    candidate_value: str
    value_semantics: VisualValueSemantics = VisualValueSemantics.AUTO
    confidence: float = Field(ge=0, le=1)
    uncertainties: list[str] = Field(default_factory=list)
    visible_text_summary: str = ""
    source: str = "VLM_VISUAL_OBSERVATION"
    latency_ms: float | None = Field(default=None, ge=0)
    provider_confidence: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_output(self) -> VisualSemanticCandidate:
        if not self.provider.strip() or not self.candidate_value.strip():
            raise ValueError("provider and candidate value are required")
        if _PRIVATE_REFERENCE.search(self.frame_reference):
            raise ValueError("candidate frame reference is not privacy-safe")
        _assert_action_free_text(self.candidate_value)
        _assert_action_free_text(self.visible_text_summary)
        for uncertainty in self.uncertainties:
            _assert_action_free_text(uncertainty)
        if self.candidate_type in (
            VisualCandidateType.HP,
            VisualCandidateType.MP,
        ):
            if self.value_semantics is VisualValueSemantics.AUTO:
                self.value_semantics = VisualValueSemantics.NORMALIZED_RATIO
            if self.value_semantics is not VisualValueSemantics.NORMALIZED_RATIO:
                raise ValueError("HP/MP candidate must use normalized ratio semantics")
            try:
                ratio = float(self.candidate_value)
            except ValueError as exc:
                raise ValueError("HP/MP candidate_value must be a normalized ratio") from exc
            if not 0 <= ratio <= 1:
                raise ValueError("HP/MP normalized ratio must be between 0 and 1")
        elif self.value_semantics is VisualValueSemantics.AUTO:
            self.value_semantics = VisualValueSemantics.VISIBLE_TEXT
        return self


class VisualSemanticResponse(BaseModel):
    """Validated provider output; invalid or unavailable output is fail-closed."""

    model_config = ConfigDict(extra="forbid")

    status: VisualSemanticStatus = VisualSemanticStatus.UNKNOWN
    candidates: list[VisualSemanticCandidate] = Field(default_factory=list)
    validation_status: str = "VALIDATED"
    structured_output_failure_count: int = Field(default=0, ge=0)
    latency_ms: float | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def normalize_status(self) -> VisualSemanticResponse:
        if self.status is not VisualSemanticStatus.VALID and self.candidates:
            raise ValueError("non-valid response cannot contain candidates")
        return self

    @classmethod
    def from_payload(cls, payload: object) -> VisualSemanticResponse:
        """Parse an untrusted provider payload without leaking free-form output."""
        try:
            return cls.model_validate(payload)
        except Exception:
            return cls(
                status=VisualSemanticStatus.INVALID,
                validation_status=VisualSemanticStatus.INVALID.value,
                structured_output_failure_count=1,
            )


@runtime_checkable
class VisualSemanticProvider(Protocol):
    """Provider boundary for observation only; no executor methods exist."""

    provider_id: str

    def observe(self, request: VisualSemanticRequest) -> VisualSemanticResponse: ...


class MockVisualSemanticProvider:
    """Deterministic CI provider; never accesses a window or external service."""

    provider_id = "mock_visual_semantics"

    def __init__(
        self,
        response: VisualSemanticResponse | None = None,
        *,
        available: bool = True,
    ) -> None:
        self.response = response or VisualSemanticResponse()
        self.available = available
        self.call_count = 0

    def observe(self, request: VisualSemanticRequest) -> VisualSemanticResponse:
        self.call_count += 1
        if not self.available:
            return VisualSemanticResponse(status=VisualSemanticStatus.UNAVAILABLE)
        return self.response.model_copy(deep=True)


class VisualSemanticGateDecision(BaseModel):
    """Auditable decision to call or skip the experimental provider."""

    model_config = ConfigDict(extra="forbid")

    call_allowed: bool
    trigger: VisualSemanticTrigger
    reason: str
    cooldown_remaining_seconds: float = Field(default=0.0, ge=0)


class VisualSemanticGate:
    """Low-frequency, deterministic gate; local evidence always wins."""

    def __init__(
        self,
        *,
        cooldown_seconds: float = 30.0,
        persistent_unknown_limit: int = 2,
        roi_change_threshold: float = 0.05,
    ) -> None:
        if cooldown_seconds < 0 or persistent_unknown_limit < 1:
            raise ValueError("invalid gate configuration")
        self.cooldown_seconds = cooldown_seconds
        self.persistent_unknown_limit = persistent_unknown_limit
        self.roi_change_threshold = roi_change_threshold
        self._last_call_at: datetime | None = None
        self._unknown_streak = 0

    def evaluate(
        self,
        *,
        now: datetime,
        change: ChangeResult | None = None,
        local_candidate_available: bool = False,
        previous_unknown: bool = True,
        previous_evidence_stale: bool = False,
        ocr_failed: bool = False,
        manual_probe: bool = False,
    ) -> VisualSemanticGateDecision:
        if local_candidate_available:
            return VisualSemanticGateDecision(
                call_allowed=False,
                trigger=VisualSemanticTrigger.LOCAL_EVIDENCE_SUFFICIENT,
                reason="local structured evidence is sufficient",
            )
        remaining = 0.0
        if self._last_call_at is not None:
            elapsed = max(0.0, (now - self._last_call_at).total_seconds())
            remaining = max(0.0, self.cooldown_seconds - elapsed)
            if remaining > 0:
                return VisualSemanticGateDecision(
                    call_allowed=False,
                    trigger=VisualSemanticTrigger.COOLDOWN_ACTIVE,
                    reason="provider cooldown is active",
                    cooldown_remaining_seconds=round(remaining, 4),
                )
        trigger = VisualSemanticTrigger.NO_TRIGGER
        if manual_probe:
            trigger = VisualSemanticTrigger.MANUAL_PROBE
        elif ocr_failed:
            trigger = VisualSemanticTrigger.OCR_FAILURE
        elif previous_evidence_stale:
            trigger = VisualSemanticTrigger.STALE_EVIDENCE
        elif change is not None and change.roi_scores.get(
            "map_label", 0.0
        ) >= self.roi_change_threshold:
            trigger = VisualSemanticTrigger.MAP_REGION_CHANGE
        elif change is not None and change.changed:
            trigger = VisualSemanticTrigger.SCENE_CHANGE
        elif previous_unknown and self._unknown_streak >= self.persistent_unknown_limit:
            trigger = VisualSemanticTrigger.PERSISTENT_UNKNOWN
        elif previous_unknown and self._last_call_at is not None:
            trigger = VisualSemanticTrigger.COOLDOWN_EXPIRED
        elif self._last_call_at is None and previous_unknown:
            trigger = VisualSemanticTrigger.INITIAL_UNKNOWN
        if trigger is VisualSemanticTrigger.NO_TRIGGER:
            return VisualSemanticGateDecision(
                call_allowed=False,
                trigger=trigger,
                reason="no configured visual fallback trigger",
            )
        return VisualSemanticGateDecision(
            call_allowed=True,
            trigger=trigger,
            reason=f"triggered by {trigger.value}",
        )

    def record_call(
        self,
        *,
        at: datetime,
        response: VisualSemanticResponse,
    ) -> None:
        self._last_call_at = at
        if response.status is VisualSemanticStatus.VALID and response.candidates:
            self._unknown_streak = 0
        else:
            self._unknown_streak += 1


class StrategyMetrics(BaseModel):
    """Comparable aggregate metrics with honest null denominators."""

    model_config = ConfigDict(extra="forbid")

    strategy: str
    invocations: int = Field(ge=0)
    valid_candidates: int = Field(default=0, ge=0)
    verified_candidates: int = Field(default=0, ge=0)
    false_candidates: int = Field(default=0, ge=0)
    unknown: int = Field(default=0, ge=0)
    average_latency_ms: float | None = Field(default=None, ge=0)
    p95_latency_ms: float | None = Field(default=None, ge=0)
    useful_yield: float | None = Field(default=None, ge=0, le=1)
    estimated_calls_per_minute: float | None = Field(default=None, ge=0)
    structured_output_failure_count: int = Field(default=0, ge=0)

    @classmethod
    def from_samples(
        cls,
        *,
        strategy: str,
        invocations: int,
        valid_candidates: int = 0,
        verified_candidates: int = 0,
        false_candidates: int = 0,
        unknown: int = 0,
        latencies_ms: list[float] | None = None,
        duration_seconds: float | None = None,
        structured_output_failure_count: int = 0,
    ) -> StrategyMetrics:
        samples = sorted(latencies_ms or [])
        average = sum(samples) / len(samples) if samples else None
        p95 = samples[max(0, int(len(samples) * 0.95) - 1)] if len(samples) >= 2 else None
        return cls(
            strategy=strategy,
            invocations=invocations,
            valid_candidates=valid_candidates,
            verified_candidates=verified_candidates,
            false_candidates=false_candidates,
            unknown=unknown,
            average_latency_ms=round(average, 4) if average is not None else None,
            p95_latency_ms=round(p95, 4) if p95 is not None else None,
            useful_yield=(round(valid_candidates / invocations, 4) if invocations else None),
            estimated_calls_per_minute=(
                round(invocations / (duration_seconds / 60), 4)
                if duration_seconds and duration_seconds > 0
                else None
            ),
            structured_output_failure_count=structured_output_failure_count,
        )
