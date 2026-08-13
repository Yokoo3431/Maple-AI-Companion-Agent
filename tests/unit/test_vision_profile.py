"""Vision Profile / ROI / HP-MP / 模板判别 / WGC failover / 跨机对比 单测(Phase 13-I.2)。"""

from __future__ import annotations

import pytest
from PIL import Image, ImageDraw

from maple_agent.hybrid_vision import (
    NormalizedROI,
    VisionProfile,
    VisionProfileRegistry,
    VisionProfileTransformer,
    build_cross_machine_benchmark,
)
from maple_agent.hybrid_vision.hpmp import HpMpGeometryExtractor
from maple_agent.hybrid_vision.models import CaptureCondition
from maple_agent.hybrid_vision.template import MapleVisualTemplateLibrary
from maple_agent.real_vision.capture_manager import CaptureManager

try:
    import cv2  # noqa: F401

    _CV2_AVAILABLE = True
except ImportError:
    _CV2_AVAILABLE = False


def _draw_bar(
    *,
    width: int,
    height: int,
    roi: dict,
    ratio: float,
    color: tuple[int, int, int],
    border: bool = False,
) -> Image.Image:
    image = Image.new("RGB", (width, height), (0, 0, 0))
    draw = ImageDraw.Draw(image)
    x = roi["x"]
    y = roi["y"]
    bar_width = int(roi["width"] * ratio)
    draw.rectangle(
        (x, y, x + bar_width, y + roi["height"]),
        fill=color,
    )
    if border:
        draw.rectangle((x, y, x + 2, y + roi["height"]), fill=color)
        draw.rectangle(
            (
                x + roi["width"] - 2,
                y,
                x + roi["width"],
                y + roi["height"],
            ),
            fill=color,
        )
    return image


def test_normalized_to_pixel_round_trip():
    roi = NormalizedROI(x=0.5, y=0.25, width=0.25, height=0.1)
    pixel = VisionProfileTransformer.to_pixel(
        roi,
        client_width=2560,
        client_height=1440,
    )
    assert pixel["x"] == 1280
    assert pixel["y"] == 360
    assert pixel["width"] == 640
    assert pixel["height"] == 144
    back = VisionProfileTransformer.to_normalized(
        pixel,
        client_width=2560,
        client_height=1440,
    )
    assert abs(back.x - roi.x) < 0.001
    assert abs(back.width - roi.width) < 0.001


def test_pixel_to_normalized_migration():
    legacy = VisionProfile(
        profile_id="legacy",
        resolution="2560x1440",
        legacy_pixel_rois={
            "hp_roi": {"x": 750, "y": 1210, "width": 750, "height": 120},
            "map_label_roi": {"x": 150, "y": 0, "width": 750, "height": 90},
        },
    )
    migrated = VisionProfileTransformer.migrate_legacy(
        legacy,
        client_width=2560,
        client_height=1440,
    )
    assert "hp" in migrated.normalized_rois
    assert abs(migrated.normalized_rois["hp"].x - 750 / 2560) < 0.001
    assert abs(migrated.normalized_rois["hp"].height - 120 / 1440) < 0.001


def test_base_profile_2560x1440():
    registry = VisionProfileRegistry()
    base = registry.resolved("maple_classic_default")
    assert base.profile_id == "maple_classic_default"
    assert "hp" in base.normalized_rois
    hp = VisionProfileTransformer.to_pixel(
        base.normalized_rois["hp"],
        client_width=2560,
        client_height=1440,
    )
    assert hp["x"] == 750
    assert hp["y"] == 1210
    assert hp["width"] == 750


def test_office_profile_1920x1080_inherits_base():
    registry = VisionProfileRegistry()
    office = registry.resolved("office_pc_1920x1080")
    assert office.base_profile == "maple_classic_default"
    assert "hp" in office.normalized_rois
    hp = VisionProfileTransformer.to_pixel(
        office.normalized_rois["hp"],
        client_width=1920,
        client_height=1080,
    )
    assert abs(hp["x"] - 562) <= 2


def test_dpi_metadata_handling():
    roi = NormalizedROI(x=0.1, y=0.1, width=0.5, height=0.1)
    pixel = VisionProfileTransformer.to_pixel(
        roi,
        client_width=1920,
        client_height=1080,
        dpi_scale=1.25,
    )
    assert pixel["x"] == int(round(0.1 * 1920 * 1.25))
    assert pixel["width"] == int(round(0.5 * 1920 * 1.25))


def test_negative_desktop_coordinates_do_not_affect_roi():
    roi = NormalizedROI(x=0.5, y=0.25, width=0.25, height=0.1)
    pixel = VisionProfileTransformer.to_pixel(
        roi,
        client_width=1920,
        client_height=1080,
    )
    assert pixel["x"] == 960
    assert pixel["y"] == 270


def test_wgc_preferred_provider(monkeypatch):
    manager = CaptureManager(window_title="MapleStory")
    # 环境无关:WGC available -> 首选 wgc;否则 imagegrab
    if manager.wgc.available:
        assert manager.preferred == "wgc"
    else:
        assert manager.preferred == "imagegrab"
    assert manager.imagegrab is not None


def test_occluded_wgc_failure_no_fallback(monkeypatch):
    manager = CaptureManager(window_title="MapleStory")
    monkeypatch.setattr(manager.wgc, "available", True)

    def fail_capture(*, trace_id=""):
        from maple_agent.vision_runtime.models import VisionFrame

        return VisionFrame(
            frame_id="f",
            image_reference="unavailable://wgc-failed",
            confidence=0.0,
        )

    monkeypatch.setattr(manager.wgc, "capture", fail_capture)
    monkeypatch.setattr(manager.imagegrab, "capture", fail_capture)
    frame, provider, reason = manager.capture(
        condition=CaptureCondition.BACKGROUND_OCCLUDED.value
    )
    assert provider == "wgc"
    assert "no-fallback" in reason
    assert frame.confidence == 0.0


def test_minimized_not_supported():
    manager = CaptureManager(window_title="MapleStory")
    frame, provider, reason = manager.capture(
        condition=CaptureCondition.MINIMIZED.value
    )
    assert provider == "none"
    assert "minimized-not-supported" in reason
    assert frame.confidence == 0.0


def test_hp_geometry_multi_resolution():
    extractor = HpMpGeometryExtractor()
    for width, height in ((2560, 1440), (1920, 1080)):
        roi = {
            "x": int(0.293 * width),
            "y": int(0.84 * height),
            "width": int(0.293 * width),
            "height": int(0.083 * height),
        }
        image = _draw_bar(
            width=width,
            height=height,
            roi=roi,
            ratio=0.85,
            color=(220, 40, 40),
        )
        ratio, _ = extractor.extract_ratio(image, roi, kind="hp")
        assert ratio is not None
        assert abs(ratio - 0.85) < 0.12


def test_mp_geometry_border_contamination():
    extractor = HpMpGeometryExtractor()
    width, height = 1920, 1080
    roi = {
        "x": int(0.293 * width),
        "y": int(0.785 * height),
        "width": int(0.293 * width),
        "height": int(0.052 * height),
    }
    image = _draw_bar(
        width=width,
        height=height,
        roi=roi,
        ratio=0.7,
        color=(40, 40, 220),
        border=True,
    )
    ratio, confidence = extractor.extract_ratio(image, roi, kind="mp")
    assert ratio is not None
    assert abs(ratio - 0.7) < 0.18
    assert confidence > 0.0


def test_confidence_semantics_separate_from_ratio():
    extractor = HpMpGeometryExtractor()
    width, height = 1920, 1080
    roi = {
        "x": int(0.293 * width),
        "y": int(0.84 * height),
        "width": int(0.293 * width),
        "height": int(0.083 * height),
    }
    image = _draw_bar(
        width=width,
        height=height,
        roi=roi,
        ratio=0.85,
        color=(220, 40, 40),
    )
    ratio, confidence = extractor.extract_ratio(image, roi, kind="hp")
    assert ratio is not None and 0 < ratio <= 1
    assert 0 < confidence <= 1


@pytest.mark.skipif(
    not _CV2_AVAILABLE,
    reason="opencv required for template matching",
)
def test_template_multi_class_discrimination(tmp_path):
    library = MapleVisualTemplateLibrary(
        manifest_path=tmp_path / "manifest.json",
        local_dir=tmp_path / "templates",
    )
    template_ids = []
    for index in range(4):
        template_id = f"map_{index}"
        template_ids.append(template_id)
        image = Image.new("RGB", (200, 100), (20, 20, 20))
        draw = ImageDraw.Draw(image)
        draw.rectangle(
            (30 + index * 15, 20, 120 + index * 15, 80),
            fill=(80 + index * 40, 60, 60),
        )
        path = tmp_path / f"{template_id}.png"
        image.save(path)
        library.add_template(
            template_id=template_id,
            kind="map",
            image_path=path,
        )
    for template_id in template_ids[:3]:
        result = library.discriminate(
            tmp_path / f"{template_id}.png",
            kind="map",
            threshold=0.5,
            min_margin=0.01,
            query_id=template_id,
        )
        assert result.top1 is not None
        assert result.top1.template_id == template_id
        assert result.margin > 0


@pytest.mark.skipif(
    not _CV2_AVAILABLE,
    reason="opencv required for template matching",
)
def test_template_false_positive_protection(tmp_path):
    library = MapleVisualTemplateLibrary(
        manifest_path=tmp_path / "manifest.json",
        local_dir=tmp_path / "templates",
    )
    image_a = Image.new("RGB", (100, 60), (30, 30, 30))
    draw = ImageDraw.Draw(image_a)
    draw.rectangle((20, 10, 80, 50), fill=(120, 60, 60))
    image_a.save(tmp_path / "map_a.png")
    image_b = Image.new("RGB", (100, 60), (30, 30, 30))
    draw = ImageDraw.Draw(image_b)
    draw.rectangle((19, 10, 81, 50), fill=(120, 60, 60))
    image_b.save(tmp_path / "map_b.png")
    library.add_template(
        template_id="map_a",
        kind="map",
        image_path=tmp_path / "map_a.png",
    )
    library.add_template(
        template_id="map_b",
        kind="map",
        image_path=tmp_path / "map_b.png",
    )
    result = library.discriminate(
        tmp_path / "map_a.png",
        kind="map",
        threshold=0.9,
        min_margin=0.3,
        query_id="map_a",
    )
    assert result.matched is False
    assert "margin" in result.reason


def test_cross_machine_benchmark():
    home = {
        "resolution": "2560x1440",
        "dpi": 1.0,
        "capture_provider": "wgc+imagegrab",
        "hp_error": 0.013,
        "mp_error": 0.253,
        "map_top1_accuracy": 0.676,
        "capture_latency_ms": 169.0,
        "geometry_latency_ms": 138.0,
        "template_latency_ms": 4.0,
        "ocr_latency_ms": 760.0,
        "profile_transform_status": "OK",
    }
    office = {
        "resolution": "1920x1080",
        "dpi": 1.0,
        "capture_provider": "wgc-deps-ok;window-minimized",
        "hp_error": None,
        "mp_error": None,
        "map_top1_accuracy": None,
        "capture_latency_ms": None,
        "geometry_latency_ms": None,
        "template_latency_ms": None,
        "ocr_latency_ms": None,
        "profile_transform_status": "OK",
    }
    benchmark = build_cross_machine_benchmark(home=home, office=office)
    assert len(benchmark.entries) == 2
    assert benchmark.generalization["profile_transform"] == "PASS"
    assert benchmark.generalization["hp_error"] == "N/A"
    assert benchmark.generalization["resolution"] == "PASS"
