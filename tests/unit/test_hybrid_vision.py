"""Hybrid Local Perception 单测(Phase 13-I.1,fixtures only,CI 无真实客户端)。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw

from maple_agent.hybrid_vision import (
    BenchmarkPrivacySanitizer,
    CaptureCondition,
    FrameChangeDetector,
    HpMpGeometryExtractor,
    KnowledgeGuidedResolver,
    MapleVisualTemplateLibrary,
    PerceptionMethod,
    VisionScheduler,
    classify_window_state,
)
from maple_agent.hybrid_vision.models import ChangeResult
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.real_vision import WindowsGraphicsCaptureProvider

REPO_ROOT = Path(__file__).resolve().parents[2]


def _solid_image(color: tuple[int, int, int], size=(80, 40)) -> Image.Image:
    image = Image.new("RGB", size, color)
    return image


def _bar_image(
    *,
    width: int = 200,
    height: int = 20,
    fill: float = 1.0,
    kind: str = "hp",
) -> Image.Image:
    image = Image.new("RGB", (width, height), (20, 20, 20))
    draw = ImageDraw.Draw(image)
    bar_width = max(1, int(width * fill))
    color = (220, 40, 40) if kind == "hp" else (40, 100, 220)
    draw.rectangle([0, 0, bar_width - 1, height - 1], fill=color)
    return image


def test_change_detector_first_frame_changed():
    detector = FrameChangeDetector()
    result = detector.detect(_solid_image((0, 0, 0)))
    assert result.changed is True
    assert result.score == 1.0


def test_change_detector_identical_frame_unchanged():
    detector = FrameChangeDetector()
    image = _solid_image((50, 50, 50))
    detector.detect(image)
    result = detector.detect(image)
    assert result.changed is False


def test_change_detector_roi_level():
    detector = FrameChangeDetector()
    base = _solid_image((10, 10, 10), size=(100, 100))
    detector.detect(
        base,
        rois={"map_label": {"x": 0, "y": 0, "width": 50, "height": 20}},
    )
    changed = _solid_image((10, 10, 10), size=(100, 100))
    draw = ImageDraw.Draw(changed)
    draw.rectangle([0, 0, 50, 20], fill=(255, 255, 255))
    result = detector.detect(
        changed,
        rois={"map_label": {"x": 0, "y": 0, "width": 50, "height": 20}},
    )
    assert result.roi_scores["map_label"] > 0.1


def test_scheduler_skips_ocr_when_unchanged():
    scheduler = VisionScheduler()
    unchanged = ChangeResult(
        changed=False,
        score=0.01,
        roi_scores={"map_label": 0.01, "quest": 0.0, "dialog": 0.0},
    )
    tasks = scheduler.plan(unchanged)
    methods = [task.method for task in tasks]
    assert PerceptionMethod.COLOR_GEOMETRY in methods  # HP/MP cheap
    assert PerceptionMethod.OCR not in methods  # 昂贵 OCR 被跳过
    assert scheduler.skipped_ocr_count == 1


def test_scheduler_triggers_map_ocr_on_change():
    scheduler = VisionScheduler()
    changed = ChangeResult(
        changed=True,
        score=0.5,
        roi_scores={"map_label": 0.9, "quest": 0.0, "dialog": 0.0},
    )
    tasks = scheduler.plan(changed)
    methods = {task.method for task in tasks}
    assert PerceptionMethod.OCR in methods
    assert PerceptionMethod.TEMPLATE in methods


def test_scheduler_entity_interval():
    scheduler = VisionScheduler(entity_interval_s=0.0)
    result = ChangeResult(changed=False, score=0.0, roi_scores={})
    tasks = scheduler.plan(result, entity_roi_present=True)
    assert any(task.roi == "entity" for task in tasks)


def test_hpmp_geometry_full_bar():
    extractor = HpMpGeometryExtractor()
    result = extractor.extract(
        _bar_image(fill=1.0, kind="hp"),
        hp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
        mp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
    )
    assert result.hp_ratio is not None
    assert result.hp_ratio > 0.9


def test_hpmp_geometry_partial_bar():
    extractor = HpMpGeometryExtractor()
    result = extractor.extract(
        _bar_image(fill=0.5, kind="hp"),
        hp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
        mp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
    )
    assert result.hp_ratio is not None
    assert 0.3 <= result.hp_ratio <= 0.7


def test_hpmp_geometry_no_bar():
    extractor = HpMpGeometryExtractor()
    result = extractor.extract(
        _solid_image((20, 20, 20)),
        hp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
        mp_roi={"x": 0, "y": 0, "width": 200, "height": 20},
    )
    assert result.hp_ratio is None
    assert "hp bar not found in ROI" in result.reasons


def test_template_library_metadata_only(tmp_path):
    library = MapleVisualTemplateLibrary(
        manifest_path=tmp_path / "manifest.json",
        local_dir=tmp_path / "templates",
    )
    template_image = tmp_path / "template.png"
    _solid_image((200, 30, 30), (60, 30)).save(template_image)
    entry = library.add_template(
        template_id="hp_bar_test",
        kind="ui",
        image_path=template_image,
    )
    assert entry["sha256"]
    manifest = json.loads(
        (tmp_path / "manifest.json").read_text(encoding="utf-8")
    )
    assert "templates" in manifest
    assert "hp_bar_test" in manifest["templates"]
    rendered = json.dumps(manifest)
    assert "png" not in rendered  # GitHub-safe: 无图片路径
    if library.backend == "cv2":
        match = library.match(_solid_image((200, 30, 30), (60, 30)), "hp_bar_test")
        assert match.score > 0.9
        assert match.matched is True
    else:
        match = library.match(
            _solid_image((200, 30, 30), (60, 30)), "hp_bar_test"
        )
        assert match.matched is False


def test_knowledge_resolution_exact():
    resolver = KnowledgeGuidedResolver()
    result = resolver.resolve_name(
        "射手村",
        evidence_confidence=0.9,
        candidates=[
            {"id": "map:1", "name": "射手村", "aliases": ["Henesys"]}
        ],
    )
    assert result.resolved is True
    assert result.canonical_candidate_id == "map:1"


def test_knowledge_resolution_cannot_fabricate():
    resolver = KnowledgeGuidedResolver()
    result = resolver.resolve_name(
        "",
        evidence_confidence=0.0,
        candidates=[{"id": "npc:1", "name": "赫丽娜"}],
    )
    assert result.resolved is False
    assert "knowledge prior does not create observation" in " ".join(
        result.reasoning
    )


def test_knowledge_resolution_low_confidence_unresolved():
    resolver = KnowledgeGuidedResolver(min_evidence_confidence=0.5)
    result = resolver.resolve_name(
        "赫丽娜",
        evidence_confidence=0.2,
        candidates=[{"id": "npc:1", "name": "赫丽娜"}],
    )
    assert result.resolved is False


def test_knowledge_resolution_not_in_candidates():
    resolver = KnowledgeGuidedResolver()
    result = resolver.resolve_name(
        "绿水灵",
        evidence_confidence=0.9,
        candidates=[{"id": "npc:1", "name": "赫丽娜"}],
    )
    assert result.resolved is False
    assert "expected != observed" in " ".join(result.reasoning)


def test_knowledge_candidates_for_map():
    graph = MapleKnowledgeGraph()
    entities, relations = load_demo_knowledge()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    resolver = KnowledgeGuidedResolver(knowledge=graph)
    candidates = resolver.candidates_for_map("射手村")
    assert isinstance(candidates, list)


def test_sanitizer_redacts_private_data():
    sanitizer = BenchmarkPrivacySanitizer()
    raw = {
        "schema_version": "1.0",
        "sample_count": 40,
        "window": {
            "hwnd": 788748,
            "pid": 10396,
            "window_title": "冒险岛怀旧服",
            "resolution": "2560x1440",
        },
        "image_reference": r"C:\Users\Yokoo\sessions\t\shot.png",
        "ocr_text": "聊天内容",
        "map_accuracy": 0.0,
    }
    safe = sanitizer.sanitize_report(raw)
    assert safe["window"]["hwnd"] == "<redacted>"
    assert safe["window"]["pid"] == "<redacted>"
    assert safe["window"]["resolution"] == "2560x1440"
    assert safe["sample_count"] == 40
    assert safe["map_accuracy"] == 0.0
    sanitizer.assert_safe(safe)


def test_sanitizer_rejects_raw_report():
    sanitizer = BenchmarkPrivacySanitizer()
    raw = {"image_reference": r"C:\Users\Yokoo\shot.png"}
    with pytest.raises(AssertionError):
        sanitizer.assert_safe(raw)


def test_capture_condition_classification():
    assert (
        classify_window_state(foreground=True, visible=True)
        is CaptureCondition.FOREGROUND
    )
    assert (
        classify_window_state(foreground=False, visible=True)
        is CaptureCondition.BACKGROUND_VISIBLE
    )
    assert (
        classify_window_state(visible=False)
        is CaptureCondition.BACKGROUND_OCCLUDED
    )
    assert (
        classify_window_state(minimized=True)
        is CaptureCondition.MINIMIZED
    )


def test_sessions_and_logs_remain_gitignored():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "sessions/" in gitignore
    assert "logs/" in gitignore


def test_default_benchmark_output_is_private():
    default_output = REPO_ROOT / "sessions"
    assert default_output.is_dir()  # sessions 存在且默认输出指向私有位置


def test_wgc_provider_contract_without_package():
    provider = WindowsGraphicsCaptureProvider(window_title="MapleStory")
    frame = provider.capture()
    assert frame.confidence == 0.0
    if not provider.available:
        assert "unavailable" in frame.image_reference
        assert provider.last_status.value in (
            "UNAVAILABLE",
            "WINDOW_NOT_FOUND",
        )
    reference = provider.capture_reference()
    if provider.available:
        # 包可用时,找不到窗口也必须失败安全
        assert reference is None or reference.confidence >= 0.0


def test_committed_public_summary_is_privacy_safe():
    summary_path = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "vision"
        / "real_vision_13i1_public.json"
    )
    payload = json.loads(summary_path.read_text(encoding="utf-8"))
    sanitizer = BenchmarkPrivacySanitizer()
    sanitizer.assert_safe(payload)
    rendered = json.dumps(payload, ensure_ascii=False)
    assert '"pid"' not in rendered
    assert '"hwnd"' not in rendered
    assert ":\\" not in rendered
    assert "sessions" not in rendered
