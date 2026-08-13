"""HpMpGeometryExtractor:HP/MP 几何提取(主路径,不依赖数字 OCR)。"""

from __future__ import annotations

import os
import re
import shutil
import time

from maple_agent.hybrid_vision.bar_model import BarFillModel
from maple_agent.hybrid_vision.models import HpMpGeometryResult

try:
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


def _load_rgb(image):
    if isinstance(image, os.PathLike):
        image = str(image)
    if _CV2_AVAILABLE:
        if isinstance(image, str):
            return cv2.imread(image)
        if hasattr(image, "convert"):
            return cv2.cvtColor(
                np.asarray(image.convert("RGB")), cv2.COLOR_RGB2BGR
            )
        return image
    from PIL import Image

    if not hasattr(image, "convert"):
        image = Image.open(image)
    return image.convert("RGB")


def _color_mask_cv2(rgb, kind: str):
    hsv = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV)
    if kind == "hp":  # 红/橙/黄
        lower1 = np.array([0, 80, 80])
        upper1 = np.array([25, 255, 255])
        lower2 = np.array([170, 80, 80])
        upper2 = np.array([180, 255, 255])
        mask = cv2.inRange(hsv, lower1, upper1) | cv2.inRange(
            hsv, lower2, upper2
        )
    elif kind == "mp":  # 蓝
        lower = np.array([90, 60, 60])
        upper = np.array([135, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
    elif kind in ("green", "hp_green", "mp_green"):  # 该 Unity 客户端的绿色条
        lower = np.array([70, 60, 60])
        upper = np.array([130, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
    else:
        mask = np.zeros(rgb.shape[:2], dtype=np.uint8)
    return mask


def _color_mask_pil(pixels, width: int, height: int, kind: str):
    """PIL 降级模式(CI 无 cv2),RGB 近似。"""
    mask = bytearray(width * height)
    for index, (r, g, b) in enumerate(pixels):
        if kind == "hp":
            red_like = r > 140 and g < 130 and b < 130
            yellow_like = r > 160 and g > 130 and b < 120
            mask[index] = 255 if (red_like or yellow_like) else 0
        else:
            blue_like = b > 140 and r < 130 and g < 160
            mask[index] = 255 if blue_like else 0
    return bytes(mask), width, height


def _row_longest_extents(mask) -> list[int]:
    """每行最长连续彩色段长度;抗左侧/右侧单列边框污染。"""
    extents: list[int] = []
    for row in mask:
        longest = 0
        current = 0
        for value in row:
            if value:
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0
        if longest:
            extents.append(longest)
    return extents


def _confidence_from_mask(
    *,
    width: int,
    height: int,
    colored: int,
    extents: list[int],
    mask,
) -> float:
    """几何检测可信度(与 ratio 分离,不代表 ratio 精确度)。

    考虑:掩码密度、彩色行连续性、边缘一致性、边框污染惩罚。
    """
    if not extents:
        return 0.0
    density = colored / max(1, width * height)
    continuity = len(extents) / max(1, height)
    edge_consistency = 1.0 - min(
        1.0,
        abs(max(extents) - min(extents)) / max(1, width),
    )
    # 边框污染惩罚:左右边缘列若全部彩色,说明可能包含装饰/边框
    left_column = int(mask[:, 0].sum() // 255) if mask.shape[1] > 0 else 0
    right_column = (
        int(mask[:, -1].sum() // 255) if mask.shape[1] > 0 else 0
    )
    border_penalty = (
        min(1.0, left_column / max(1, height))
        + min(1.0, right_column / max(1, height))
    ) * 0.25
    confidence = (
        density * 3.0
        + continuity * 0.3
        + edge_consistency * 0.4
        - border_penalty
    )
    return round(min(1.0, max(0.0, confidence)), 4)


def _extract_ratio_cv2(mask, width: int, height: int) -> tuple[float, float]:
    """返回 (fill_ratio, confidence)。

    fill_ratio = 彩色行最长连续段长度的中位数 / 宽度(抗边框)。
    confidence = 几何检测可信度(与 ratio 分离)。
    """
    colored = int(mask.sum() // 255)
    extents = _row_longest_extents(mask)
    if not extents:
        return 0.0, 0.0
    median_extent = sorted(extents)[len(extents) // 2] / max(1, width)
    ratio = round(min(1.0, max(0.0, median_extent)), 4)
    confidence = _confidence_from_mask(
        width=width,
        height=height,
        colored=colored,
        extents=extents,
        mask=mask,
    )
    return ratio, confidence


def _extract_ratio_pil(
    mask_bytes: bytes, width: int, height: int
) -> tuple[float, float]:
    """PIL 降级:逐行最长连续彩色段中位数(与 cv2 语义一致)。"""
    extents: list[int] = []
    colored = 0
    for y in range(height):
        base = y * width
        longest = 0
        current = 0
        for x in range(width):
            if mask_bytes[base + x]:
                colored += 1
                current += 1
                if current > longest:
                    longest = current
            else:
                current = 0
        if longest:
            extents.append(longest)
    if not extents:
        return 0.0, 0.0
    median_extent = sorted(extents)[len(extents) // 2] / max(1, width)
    ratio = round(min(1.0, max(0.0, median_extent)), 4)
    density = colored / max(1, width * height)
    continuity = len(extents) / max(1, height)
    edge_consistency = 1.0 - min(
        1.0,
        abs(max(extents) - min(extents)) / max(1, width),
    )
    confidence = density * 3.0 + continuity * 0.3 + edge_consistency * 0.4
    return ratio, round(min(1.0, max(0.0, confidence)), 4)


class HpMpGeometryExtractor:
    """基于颜色几何的 HP/MP 条填充率提取。

    输出 hp_ratio / mp_ratio(0..1)与 confidence。数字 OCR 只是可选 secondary。
    """

    def __init__(self) -> None:
        self.backend = "cv2" if _CV2_AVAILABLE else "pil"

    def extract_ratio(
        self,
        image,
        roi: dict,
        *,
        kind: str = "hp",
        color_mode: str | None = None,
        strategy: str = "AUTO",
    ) -> tuple[float | None, float]:
        rgb = _load_rgb(image)
        x = int(roi.get("x", 0))
        y = int(roi.get("y", 0))
        width = max(1, int(roi.get("width", 0)))
        height = max(1, int(roi.get("height", 0)))
        if _CV2_AVAILABLE:
            crop = rgb[y : y + height, x : x + width]
            if crop.size == 0:
                return None, 0.0
            mask = _color_mask_cv2(crop, color_mode or kind)
            model = BarFillModel(strategy=strategy)
            result = model.analyze(
                mask, width=crop.shape[1], height=crop.shape[0]
            )
            ratio, confidence = result.ratio, result.confidence
        else:

            crop = rgb.crop((x, y, x + width, y + height))
            mask_bytes, w, h = _color_mask_pil(
                crop.getdata(), width, height, kind
            )
            model = BarFillModel(strategy=strategy)
            result = model.analyze(
                (mask_bytes, w, h), width=w, height=h
            )
            ratio, confidence = result.ratio, result.confidence
        if ratio == 0.0 and confidence < 0.3:
            return None, 0.0
        return ratio, confidence

    def extract(
        self,
        image,
        *,
        hp_roi: dict,
        mp_roi: dict,
        color_mode: str | None = None,
        strategy: str = "AUTO",
    ) -> HpMpGeometryResult:
        start = time.perf_counter()
        hp_result = self._analyze_roi(image, hp_roi, "hp", color_mode or "hp", strategy)
        mp_result = self._analyze_roi(image, mp_roi, "mp", color_mode or "mp", strategy)
        hp_ratio = (
            hp_result.ratio
            if not (hp_result.ratio == 0.0 and hp_result.confidence < 0.3)
            else None
        )
        mp_ratio = (
            mp_result.ratio
            if not (mp_result.ratio == 0.0 and mp_result.confidence < 0.3)
            else None
        )
        hp_confidence = hp_result.confidence
        mp_confidence = mp_result.confidence
        reasons: list[str] = []
        if hp_ratio is None:
            reasons.append("hp bar not found in ROI")
        if mp_ratio is None:
            reasons.append("mp bar not found in ROI")
        latency = round((time.perf_counter() - start) * 1000, 3)
        return HpMpGeometryResult(
            hp_ratio=hp_ratio,
            mp_ratio=mp_ratio,
            hp_confidence=round(hp_confidence, 4),
            mp_confidence=round(mp_confidence, 4),
            method=f"color_geometry/{self.backend}",
            latency_ms=latency,
            reasons=reasons,
            hp_strategy=hp_result.strategy,
            mp_strategy=mp_result.strategy,
            hp_segment_count=hp_result.segment_count,
            mp_segment_count=mp_result.segment_count,
            hp_active_segments=hp_result.active_segments,
            mp_active_segments=mp_result.active_segments,
            hp_partial_fraction=hp_result.partial_segment_fraction,
            mp_partial_fraction=mp_result.partial_segment_fraction,
            hp_failure=hp_result.failure,
            mp_failure=mp_result.failure,
        )

    def _analyze_roi(self, image, roi, kind, color_mode, strategy):
        rgb = _load_rgb(image)
        x = int(roi.get("x", 0))
        y = int(roi.get("y", 0))
        width = max(1, int(roi.get("width", 0)))
        height = max(1, int(roi.get("height", 0)))
        if _CV2_AVAILABLE:
            crop = rgb[y : y + height, x : x + width]
            mask = _color_mask_cv2(crop, color_mode)
            return BarFillModel(strategy=strategy).analyze(
                mask, width=crop.shape[1], height=crop.shape[0]
            )
        crop = rgb.crop((x, y, x + width, y + height))
        mask_bytes, w, h = _color_mask_pil(
            crop.getdata(), width, height, kind
        )
        return BarFillModel(strategy=strategy).analyze(
            (mask_bytes, w, h), width=w, height=h
        )


class HpMpNumericExtractor:
    """HP/MP cur/max 数字 OCR 提取(该 Unity 客户端真实显示为数字)。

    使用多尺度 + 多数投票 + `cur/max` 模式解析;ratio = cur/max。
    confidence = 投票一致度(与 ratio 分离)。依赖 pytesseract;不可用时诚实失败。
    """

    _FRACTION_RE = re.compile(r"(\d{1,5})\s*/\s*(\d{1,5})")

    def __init__(self) -> None:
        self.backend = "numeric_ocr"
        self._pytesseract = None
        try:
            import pytesseract  # type: ignore[import-not-found]

            self._pytesseract = pytesseract
            command = (
                os.environ.get("TESSERACT_CMD", "").strip()
                or shutil.which("tesseract")
                or r"C:\Program Files\Tesseract-OCR\tesseract.exe"
            )
            if command and os.path.isfile(command):
                pytesseract.pytesseract.tesseract_cmd = command
            self.available = True
        except ImportError:
            self.available = False

    def _read_candidates(self, image, box: dict) -> list[tuple[int, int]]:
        """多尺度 OCR 数字,收集 (cur, max) 候选。"""
        from PIL import Image

        crop = image.crop(
            (
                int(box["x"]),
                int(box["y"]),
                int(box["x"]) + int(box["width"]),
                int(box["y"]) + int(box["height"]),
            )
        ).convert("L")
        candidates: list[tuple[int, int]] = []
        for scale in (3, 5, 7):
            big = crop.resize(
                (crop.width * scale, crop.height * scale), Image.LANCZOS
            )
            for psm in (7, 13):
                text = self._pytesseract.image_to_string(
                    big,
                    lang="eng",
                    config=f"--psm {psm} -c tessedit_char_whitelist=0123456789/",
                )
                match = self._FRACTION_RE.search(text)
                if match:
                    cur = int(match.group(1))
                    maximum = int(match.group(2))
                    if maximum > 0 and cur <= maximum * 2:
                        candidates.append((cur, maximum))
        return candidates

    def _read_ratio(
        self,
        image,
        box: dict,
    ) -> tuple[float | None, float, str]:
        if not self.available:
            return None, 0.0, "ocr-unavailable"
        try:
            candidates = self._read_candidates(image, box)
        except Exception:
            return None, 0.0, "ocr-error"
        if not candidates:
            return None, 0.0, "no-digits"
        # 按 max 分组(条容量恒定);取支持最多的 max 组,组内取最大 cur
        # (OCR 截断使误读 cur 偏小,最大 cur 最接近真值;非后验补偿)
        groups: dict[int, list[int]] = {}
        for cur, maximum in candidates:
            groups.setdefault(maximum, []).append(cur)
        best_max = max(groups, key=lambda m: (len(groups[m]), m))
        cur_guess = max(groups[best_max])
        ratio = round(min(1.0, max(0.0, cur_guess / best_max)), 4)
        confidence = round(
            len(groups[best_max]) / max(1, len(candidates)), 4
        )
        return ratio, confidence, ""

    def extract(
        self,
        image,
        *,
        hp_box: dict,
        mp_box: dict,
    ) -> HpMpGeometryResult:
        start = time.perf_counter()
        hp_ratio, hp_conf, hp_failure = self._read_ratio(image, hp_box)
        mp_ratio, mp_conf, mp_failure = self._read_ratio(image, mp_box)
        reasons: list[str] = []
        if hp_failure:
            reasons.append(f"hp numeric: {hp_failure}")
        if mp_failure:
            reasons.append(f"mp numeric: {mp_failure}")
        return HpMpGeometryResult(
            hp_ratio=hp_ratio,
            mp_ratio=mp_ratio,
            hp_confidence=hp_conf,
            mp_confidence=mp_conf,
            method=f"numeric_ocr/{self.backend}",
            latency_ms=round((time.perf_counter() - start) * 1000, 3),
            reasons=reasons,
            hp_strategy="NUMERIC_OCR",
            mp_strategy="NUMERIC_OCR",
            hp_failure=hp_failure,
            mp_failure=mp_failure,
        )
