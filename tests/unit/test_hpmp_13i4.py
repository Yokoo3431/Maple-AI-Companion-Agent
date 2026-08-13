"""Phase 13-I.4 Segmented HP/MP Bar 单测(CI 安全,合成 mask + 回归)。"""

from __future__ import annotations

import json
import random
from pathlib import Path

from maple_agent.hybrid_vision import (
    BarFillModel,
    BenchmarkPrivacySanitizer,
    HpMpNumericExtractor,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _segmented_mask(
    *,
    width: int = 800,
    height: int = 30,
    segments: int = 10,
    seg_width: int = 60,
    gap: int = 20,
    fill: float = 1.0,
    partial_fraction: float = 0.5,
    noise: float = 0.0,
    border: bool = False,
) -> tuple[bytes, int, int]:
    """合成分段条 mask(0..1 填充;最后一段可部分点亮)。"""
    mask = bytearray(width * height)
    period = seg_width + gap
    filled_units = fill * segments
    full_segments = int(filled_units)
    rng = random.Random(42)
    for segment in range(segments):
        x0 = segment * period
        if segment < full_segments:
            lit = seg_width
        elif segment == full_segments and filled_units > full_segments + 1e-9:
            lit = max(0, int(seg_width * partial_fraction))
        else:
            lit = 0
        for y in range(height):
            base = y * width
            for x in range(x0, min(width, x0 + lit)):
                value = 255
                if noise:
                    value = 255 if rng.random() > noise else 0
                mask[base + x] = value
    if border:
        for y in range(height):
            mask[y * width] = 255
            mask[y * width + width - 1] = 255
    return bytes(mask), width, height


def _continuous_mask(
    *, width: int = 800, height: int = 30, fill: float = 1.0
) -> tuple[bytes, int, int]:
    """合成连续条 mask(左到右实心填充)。"""
    mask = bytearray(width * height)
    lit = int(width * fill)
    for y in range(height):
        base = y * width
        for x in range(lit):
            mask[base + x] = 255
    return bytes(mask), width, height


def _ratio(mask, *, strategy="SEGMENTED"):
    model = BarFillModel(strategy=strategy)
    result = model.analyze(mask, width=mask[1], height=mask[2])
    return result


def test_segmented_0_percent():
    mask = _segmented_mask(fill=0.0)
    result = _ratio(mask)
    assert result.ratio is not None
    assert result.ratio <= 0.02


def test_segmented_25_percent():
    mask = _segmented_mask(fill=0.25)
    result = _ratio(mask)
    assert result.ratio is not None
    assert 0.15 <= result.ratio <= 0.35


def test_segmented_50_percent():
    mask = _segmented_mask(fill=0.5)
    result = _ratio(mask)
    assert result.ratio is not None
    assert 0.40 <= result.ratio <= 0.60


def test_segmented_75_percent():
    mask = _segmented_mask(fill=0.75)
    result = _ratio(mask)
    assert result.ratio is not None
    assert 0.65 <= result.ratio <= 0.85


def test_segmented_100_percent():
    mask = _segmented_mask(fill=1.0)
    result = _ratio(mask)
    assert result.ratio is not None
    assert result.ratio >= 0.90


def test_segmented_partial_last_segment():
    mask = _segmented_mask(fill=0.55, partial_fraction=0.5)
    result = _ratio(mask)
    assert result.ratio is not None
    assert 0.45 <= result.ratio <= 0.65
    assert result.partial_segment_fraction > 0


def test_segmented_different_gaps():
    for gap in (10, 30, 50):
        width = 10 * (60 + gap)  # 保证全部段可见
        mask = _segmented_mask(
            width=width, gap=gap, fill=0.5
        )
        result = _ratio(mask)
        assert result.ratio is not None
        assert 0.40 <= result.ratio <= 0.60


def test_segmented_different_resolutions():
    for width, height in ((640, 24), (1920, 60), (2560, 80)):
        # width 需容纳 10 段(period=80),测试不同分辨率下的确定性
        full_width = 10 * 80
        mask = _segmented_mask(
            width=full_width, height=height, fill=0.75
        )
        result = _ratio(mask)
        assert result.ratio is not None
        assert 0.65 <= result.ratio <= 0.85


def test_segmented_noise_tolerance():
    mask = _segmented_mask(fill=0.75, noise=0.1)
    result = _ratio(mask)
    assert result.ratio is not None
    assert 0.55 <= result.ratio <= 0.95


def test_segmented_border_does_not_break():
    mask = _segmented_mask(fill=0.75, border=True)
    result = _ratio(mask)
    assert result.ratio is not None
    assert result.ratio >= 0.55


def test_auto_selects_segmented():
    segmented = _segmented_mask(fill=0.5)
    result = BarFillModel(strategy="AUTO").analyze(
        segmented, width=segmented[1], height=segmented[2]
    )
    assert result.strategy == "SEGMENTED"


def test_auto_selects_continuous():
    continuous = _continuous_mask(fill=0.5)
    result = BarFillModel(strategy="AUTO").analyze(
        continuous, width=continuous[1], height=continuous[2]
    )
    assert result.strategy == "CONTINUOUS"


def test_continuous_regression():
    full = _continuous_mask(fill=1.0)
    half = _continuous_mask(fill=0.5)
    full_result = _ratio(full, strategy="CONTINUOUS")
    half_result = _ratio(half, strategy="CONTINUOUS")
    assert full_result.ratio is not None and full_result.ratio >= 0.9
    assert half_result.ratio is not None and 0.35 <= half_result.ratio <= 0.65


def test_no_magic_ratio_compensation():
    # 50% 必须读 ~0.5,禁止任何常数补偿
    half = _continuous_mask(fill=0.5)
    result = _ratio(half, strategy="CONTINUOUS")
    assert result.ratio is not None
    assert abs(result.ratio - 0.5) < 0.15


def test_confidence_separate_from_ratio():
    mask = _segmented_mask(fill=0.75)
    result = _ratio(mask)
    assert result.ratio is not None and result.confidence > 0
    assert result.ratio != result.confidence  # 语义分离


def test_numeric_extractor_max_group_heuristic(monkeypatch):
    extractor = HpMpNumericExtractor()

    def fake_candidates_full(image, box):
        return [(92, 472), (492, 472), (2, 472), (472, 472)]

    monkeypatch.setattr(
        extractor, "_read_candidates", fake_candidates_full
    )
    ratio, confidence, failure = extractor._read_ratio(None, {"x": 0})
    assert ratio == 1.0
    assert not failure

    def fake_candidates_mid(image, box):
        return [(59, 472), (259, 472), (9, 472)]

    monkeypatch.setattr(extractor, "_read_candidates", fake_candidates_mid)
    ratio, _, _ = extractor._read_ratio(None, {"x": 0})
    assert abs(ratio - 0.549) < 0.01


def test_13i4_public_report_privacy_and_content():
    report_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i4_public.json"
    )
    assert report_path.is_file()
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    sanitizer = BenchmarkPrivacySanitizer()
    sanitizer.assert_safe(payload)
    rendered = json.dumps(payload, ensure_ascii=False)
    assert ":\\" not in rendered
    assert "sessions" not in rendered
    assert payload["hp_metrics"]["mae"] is not None
    assert payload["mp_metrics"]["mae"] is not None
    assert payload["readiness"]["real_vision"] == "FOUNDATION_ONLY"
    assert payload["vision_closure"] == "VISION_CAN_PAUSE"


def test_13i4_synthetic_not_counted_as_real():
    report_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i4_public.json"
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    provenance = payload["provenance"]
    assert provenance["SYNTHETIC"].startswith("segmented bar algorithm tests")
    assert "REAL_HOME" in provenance
    assert provenance["REAL_OFFICE"].startswith("N/A")


def test_readme_no_duplicate_phase_id():
    readme = (REPO_ROOT / "README.md").read_text(encoding="utf-8")
    lines = [
        line.strip()
        for line in readme.splitlines()
        if line.strip().startswith("| Phase ")
    ]
    phase_ids = []
    for line in lines:
        parts = [part.strip() for part in line.split("|") if part.strip()]
        if parts:
            phase_ids.append(parts[0])
    duplicates = {
        phase_id
        for phase_id in phase_ids
        if phase_ids.count(phase_id) > 1
    }
    assert not duplicates, f"duplicate phase IDs: {duplicates}"
    assert "Phase 13I.4" in phase_ids
