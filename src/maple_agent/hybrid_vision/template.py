"""MapleVisualTemplateLibrary:可扩展最小模板库(GitHub 只存元数据/哈希)。"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import time
from pathlib import Path

from maple_agent.hybrid_vision.models import TemplateMatch

try:
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


DEFAULT_LOCAL_TEMPLATE_DIR = (
    Path(__file__).resolve().parents[3] / "sessions" / "vision_templates"
)
DEFAULT_MANIFEST_PATH = (
    Path(__file__).resolve().parents[3]
    / "configs"
    / "vision_templates"
    / "manifest.json"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MapleVisualTemplateLibrary:
    """模板注册表 + OpenCV 匹配。

    真实模板图片默认 local-only(sessions/vision_templates/,已 gitignore);
    GitHub 只提交 manifest(模板 ID / kind / hash / version / schema)。
    """

    def __init__(
        self,
        *,
        manifest_path: str | Path | None = None,
        local_dir: str | Path | None = None,
    ) -> None:
        self.manifest_path = Path(manifest_path or DEFAULT_MANIFEST_PATH)
        self.local_dir = Path(local_dir or DEFAULT_LOCAL_TEMPLATE_DIR)
        self.templates: dict[str, dict] = {}
        if self.manifest_path.is_file():
            data = json.loads(
                self.manifest_path.read_text(encoding="utf-8")
            )
            self.templates = data.get("templates", {})
        self.backend = "cv2" if _CV2_AVAILABLE else "unavailable"

    def add_template(
        self,
        *,
        template_id: str,
        kind: str,
        image_path: str | Path,
        version: str = "1.0",
        notes: str = "",
    ) -> dict:
        """注册本地模板:复制图片到 local dir,计算哈希,保存 sanitized manifest。"""
        source = Path(image_path)
        if not source.is_file():
            raise FileNotFoundError(source)
        self.local_dir.mkdir(parents=True, exist_ok=True)
        target = self.local_dir / f"{template_id}.png"
        shutil.copyfile(source, target)
        entry = {
            "template_id": template_id,
            "kind": kind,
            "version": version,
            "sha256": _sha256(target),
            "notes": notes,
            "registered_at": __import__(
                "datetime"
            ).datetime.now(__import__("datetime").timezone.utc).isoformat(),
        }
        self.templates[template_id] = entry
        self.save_manifest()
        return entry

    def save_manifest(self) -> None:
        """保存无路径/无图片字节的 GitHub-safe manifest。"""
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "privacy": "metadata-only; template images are local-private",
            "templates": self.templates,
        }
        self.manifest_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _load_template_image(self, template_id: str):
        if template_id not in self.templates:
            raise KeyError(template_id)
        path = self.local_dir / f"{template_id}.png"
        if not path.is_file():
            raise FileNotFoundError(path)
        return cv2.imread(str(path), cv2.IMREAD_COLOR)

    def match(
        self,
        image,
        template_id: str,
        *,
        threshold: float = 0.75,
    ) -> TemplateMatch:
        """OpenCV 模板匹配;cv2 缺失时诚实返回 unavailable。"""
        if not _CV2_AVAILABLE:
            return TemplateMatch(
                template_id=template_id,
                score=0.0,
                matched=False,
                latency_ms=None,
            )
        start = time.perf_counter()
        template = self._load_template_image(template_id)
        if isinstance(image, (str, os.PathLike)):
            image = str(image)
        if isinstance(image, str):
            scene = cv2.imread(image)
        elif hasattr(image, "convert"):
            scene = cv2.cvtColor(
                np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR
            )
        else:
            scene = image
        result = cv2.matchTemplate(scene, template, cv2.TM_CCOEFF_NORMED)
        _, max_value, _, max_location = cv2.minMaxLoc(result)
        latency = round((time.perf_counter() - start) * 1000, 3)
        return TemplateMatch(
            template_id=template_id,
            score=round(float(max_value), 4),
            location={
                "x": int(max_location[0]),
                "y": int(max_location[1]),
            },
            latency_ms=latency,
            matched=bool(max_value >= threshold),
        )

    def match_all(
        self,
        image,
        *,
        kind: str | None = None,
        threshold: float = 0.75,
    ) -> list[TemplateMatch]:
        results: list[TemplateMatch] = []
        for template_id, entry in self.templates.items():
            if kind and entry.get("kind") != kind:
                continue
            results.append(
                self.match(image, template_id, threshold=threshold)
            )
        return sorted(results, key=lambda item: item.score, reverse=True)
