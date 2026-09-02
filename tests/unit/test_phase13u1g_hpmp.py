"""Phase 13-U.1g: bounded HP/MP calibration and player-state contract tests."""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.companion_runtime.observation_adapter import (
    ExistingVisionObservationAdapter,
)
from maple_agent.hybrid_vision import (
    HpMpNumericExtractor,
    VisionProfileRegistry,
    resolve_pixel_rois_for,
)
from maple_agent.vision_runtime.models import ScreenObservation
from maple_agent.vision_runtime.visual_semantics import (
    VisualCandidateType,
    VisualSemanticCandidate,
    VisualValueSemantics,
)


def test_office_profile_exposes_dedicated_numeric_rois_at_client_size():
    registry = VisionProfileRegistry()
    rois = resolve_pixel_rois_for(
        registry,
        "office_pc_1920x1080",
        client_width=1366,
        client_height=768,
    )
    assert rois["hp_numeric"]["width"] > 0
    assert rois["mp_numeric"]["width"] > 0
    assert rois["hp_numeric"]["y"] > 700
    assert rois["mp_numeric"]["y"] > 700


def test_numeric_extractor_uses_valid_binary_when_env_is_directory(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", r"C:\invalid-tesseract-directory")
    extractor = HpMpNumericExtractor()
    assert extractor.available is True
    assert extractor.command.lower().endswith("tesseract.exe")


def test_numeric_extractor_without_binary_is_explicitly_unavailable(monkeypatch):
    monkeypatch.setenv("TESSERACT_CMD", r"C:\invalid-tesseract-directory")
    monkeypatch.setattr(
        "maple_agent.hybrid_vision.hpmp.shutil.which",
        lambda name: None,
    )
    monkeypatch.setattr(
        "maple_agent.hybrid_vision.hpmp.Path.is_file",
        lambda self: False,
    )
    extractor = HpMpNumericExtractor()
    assert extractor.available is False
    result = extractor.extract(
        None,
        hp_box={"x": 0, "y": 0, "width": 1, "height": 1},
        mp_box={"x": 0, "y": 0, "width": 1, "height": 1},
    )
    assert result.hp_ratio is None
    assert result.mp_ratio is None
    assert result.hp_failure == "ocr-unavailable"
    assert result.mp_failure == "ocr-unavailable"


def test_real_screen_ratio_enters_existing_player_state_contract():
    screen = ScreenObservation(hp_reference=0.8, mp_reference=None)
    current = ExistingVisionObservationAdapter.from_screen_observation(
        observation_id="real-obs",
        timestamp=datetime(2026, 9, 2, tzinfo=UTC),
        frame_id="real-frame",
        observation=screen,
    )
    assert current.evidence == []
    assert current.player_status is not None
    assert current.player_status.hp == 0.8
    assert current.player_status.mp is None


def test_ambiguous_current_max_text_is_not_a_normalized_ratio():
    try:
        VisualSemanticCandidate(
            provider="test",
            model="test",
            frame_reference="frame-1",
            candidate_type=VisualCandidateType.HP,
            candidate_value="472/472",
            value_semantics=VisualValueSemantics.NORMALIZED_RATIO,
            confidence=0.8,
        )
    except ValueError:
        return
    raise AssertionError("cur/max text must not enter ratio contract")
