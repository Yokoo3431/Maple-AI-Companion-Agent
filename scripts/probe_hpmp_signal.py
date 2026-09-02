"""Bounded local-only HP/MP signal probe (Phase 13-U.1g).

Reads an already captured local frame, applies the existing profile ROI and a
small deterministic preprocessing matrix, then prints aggregate diagnostics.
It never writes frames, OCR text, credentials, or session data.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.hybrid_vision import (  # noqa: E402
    VisionProfileRegistry,
    resolve_pixel_rois_for,
)
from maple_agent.real_vision.ocr import TesseractOCRAdapter  # noqa: E402

_FRACTION_RE = re.compile(r"\d{1,5}\s*/\s*\d{1,5}")


def _variants(crop):
    from PIL import Image

    return (
        ("original", crop),
        (
            "scale2",
            crop.resize(
                (crop.width * 2, crop.height * 2),
                Image.Resampling.LANCZOS,
            ),
        ),
        (
            "scale3",
            crop.resize(
                (crop.width * 3, crop.height * 3),
                Image.Resampling.LANCZOS,
            ),
        ),
        ("threshold", crop.point(lambda value: 255 if value > 160 else 0)),
    )


def _probe_crop(adapter, crop) -> list[dict]:
    from PIL import ImageStat

    stats = ImageStat.Stat(crop)
    rows: list[dict] = []
    for variant, image in _variants(crop):
        candidate_hits = 0
        for psm in (7, 13):
            try:
                text = adapter._pytesseract.image_to_string(  # noqa: SLF001
                    image,
                    lang="eng",
                    config=(
                        f"--psm {psm} -c "
                        "tessedit_char_whitelist=0123456789/"
                    ),
                    timeout=3,
                )
                candidate_hits += int(bool(_FRACTION_RE.search(text)))
            except Exception:
                pass
        rows.append(
            {
                "variant": variant,
                "width": image.width,
                "height": image.height,
                "source_stddev": round(stats.stddev[0], 2),
                "candidate_hits": candidate_hits,
            }
        )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="脱敏 HP/MP ROI 信号探针")
    parser.add_argument("--frame", required=True)
    parser.add_argument("--profile", default="office_pc_1920x1080")
    args = parser.parse_args()

    frame_path = Path(args.frame)
    if not frame_path.is_file():
        print(json.dumps({"status": "FRAME_NOT_FOUND"}))
        return 1

    adapter = TesseractOCRAdapter(lang="eng")
    if not adapter.available:
        print(json.dumps({"status": "OCR_UNAVAILABLE"}))
        return 0

    from PIL import Image

    image = Image.open(frame_path).convert("RGB")
    registry = VisionProfileRegistry()
    try:
        rois = resolve_pixel_rois_for(
            registry,
            args.profile,
            client_width=image.width,
            client_height=image.height,
        )
    except (KeyError, ValueError):
        print(json.dumps({"status": "PROFILE_UNAVAILABLE"}))
        return 0

    output = {
        "status": "OK",
        "frame_size": [image.width, image.height],
        "profile": args.profile,
        "ocr_backend": "tesseract",
        "rois": {},
    }
    for name in ("hp_numeric", "mp_numeric", "hp", "mp"):
        roi = rois.get(name, {})
        if not roi:
            output["rois"][name] = {"status": "ROI_UNAVAILABLE"}
            continue
        box = (
            int(roi["x"]),
            int(roi["y"]),
            int(roi["x"]) + int(roi["width"]),
            int(roi["y"]) + int(roi["height"]),
        )
        crop = image.crop(box).convert("L")
        output["rois"][name] = {
            "status": "OK",
            "width": crop.width,
            "height": crop.height,
            "preprocessing": _probe_crop(adapter, crop),
        }
    print(json.dumps(output, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
