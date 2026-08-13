"""BarFillModel:HP/MP 条填充率感知(Phase 13-I.4,无 post-hoc 补偿)。

策略:
- CONTINUOUS:列密度 fill-front(满条绿色覆盖全宽,部分状态右侧密度下降)
- SEGMENTED:run-length 段检测 + 点亮段/容量(支持 partial segment)
- AUTO:依据 gap 规律性自动选择,禁止按机器名硬编码

confidence 与 ratio 分离:基于布局稳定性/段间距一致性/激活-未激活分离度。
"""

from __future__ import annotations

import statistics

try:
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


class BarFailure:
    SEGMENTS_NOT_FOUND = "SEGMENTS_NOT_FOUND"
    SEGMENT_COUNT_UNSTABLE = "SEGMENT_COUNT_UNSTABLE"
    ACTIVE_STATE_AMBIGUOUS = "ACTIVE_STATE_AMBIGUOUS"
    PARTIAL_SEGMENT_AMBIGUOUS = "PARTIAL_SEGMENT_AMBIGUOUS"
    ROI_MISMATCH = "ROI_MISMATCH"
    COLOR_MODEL_MISMATCH = "COLOR_MODEL_MISMATCH"
    INSUFFICIENT_GROUND_TRUTH = "INSUFFICIENT_GROUND_TRUTH"
    UNKNOWN = "UNKNOWN"


class BarFillResult:
    """BarFillModel 输出(内部结构,ratio 与 confidence 分离)。"""

    def __init__(
        self,
        *,
        strategy: str,
        ratio: float | None,
        confidence: float,
        segment_count: int = 0,
        active_segments: int = 0,
        partial_segment_fraction: float = 0.0,
        failure: str = "",
        latency_ms: float | None = None,
    ) -> None:
        self.strategy = strategy
        self.ratio = ratio
        self.confidence = confidence
        self.segment_count = segment_count
        self.active_segments = active_segments
        self.partial_segment_fraction = partial_segment_fraction
        self.failure = failure
        self.latency_ms = latency_ms

    def to_dict(self) -> dict:
        return {
            "strategy": self.strategy,
            "ratio": self.ratio,
            "confidence": self.confidence,
            "segment_count": self.segment_count,
            "active_segments": self.active_segments,
            "partial_segment_fraction": self.partial_segment_fraction,
            "failure": self.failure,
            "latency_ms": self.latency_ms,
        }


class BarFillModel:
    """条填充模型:列投影 + run-length,CONTINUOUS / SEGMENTED / AUTO。"""

    def __init__(
        self,
        *,
        strategy: str = "AUTO",
        expected_segments: int | None = None,
        low_density_ratio: float = 0.20,
        dense_density_ratio: float = 0.35,
        min_segment_width: int = 3,
        min_gap: int = 2,
        max_gap_ratio: float = 0.08,
        gap_regularity_tolerance: float = 0.60,
    ) -> None:
        self.strategy = strategy
        self.expected_segments = expected_segments
        self.low_density_ratio = low_density_ratio
        self.dense_density_ratio = dense_density_ratio
        self.min_segment_width = min_segment_width
        self.min_gap = min_gap
        self.max_gap_ratio = max_gap_ratio
        self.gap_regularity_tolerance = gap_regularity_tolerance
        self.backend = "cv2" if _CV2_AVAILABLE else "pil"

    def _column_profile(self, mask) -> tuple[list[int], int]:
        if isinstance(mask, tuple):  # PIL/bytes fallback 输入
            width = mask[1]
            height = mask[2]
            raw = mask[0]
            profile = [0] * width
            for y in range(height):
                base = y * width
                for x in range(width):
                    if raw[base + x]:
                        profile[x] += 1
            return profile, height
        if _CV2_AVAILABLE:
            col_sum = (mask.sum(axis=0) / 255).astype(int)
            return list(col_sum), mask.shape[0]
        # PIL 降级:mask 为 bytearray 行优先
        height = mask[1]
        width = mask[2]
        raw = mask[0]
        profile = [0] * width
        for y in range(height):
            base = y * width
            for x in range(width):
                if raw[base + x]:
                    profile[x] += 1
        return profile, height

    def _runs(self, active: list[bool]) -> list[tuple[int, int, int]]:
        runs: list[tuple[int, int, int]] = []
        start = None
        for index, is_active in enumerate(active):
            if is_active and start is None:
                start = index
            if not is_active and start is not None:
                runs.append((start, index - 1, index - start))
                start = None
        if start is not None:
            runs.append(
                (start, len(active) - 1, len(active) - start)
            )
        return runs

    def _is_segmented(self, runs, width: int) -> bool:
        """依据 gap 规律性判断分段,而非机器名。"""
        if len(runs) < 3:
            return False
        gaps = [
            runs[i + 1][0] - runs[i][1] - 1
            for i in range(len(runs) - 1)
        ]
        gaps = [gap for gap in gaps if gap >= self.min_gap]
        if len(gaps) < 2:
            return False
        if max(gaps) > width * self.max_gap_ratio:
            return False
        mean_gap = statistics.mean(gaps)
        if mean_gap <= 0:
            return False
        spread = statistics.pstdev(gaps) / mean_gap
        return spread <= self.gap_regularity_tolerance

    def _continuous_ratio(
        self,
        profile: list[int],
        height: int,
        roi_width: int,
    ) -> tuple[float | None, int, int]:
        """列密度 fill-front:dense 列数 / ROI 宽度(容量)。

        假设 ROI 覆盖整条(profile 契约);部分填充时右侧密度低 -> ratio 下降。
        """
        low = max(1, int(height * self.low_density_ratio))
        dense = max(1, int(height * self.dense_density_ratio))
        any_cols = [value >= low for value in profile]
        dense_cols = [value >= dense for value in profile]
        any_idx = [i for i, value in enumerate(any_cols) if value]
        if not any_idx:
            return None, 0, 0
        dense_count = sum(dense_cols)
        if dense_count == 0:
            return 0.0, 0, 0
        ratio = round(min(1.0, max(0.0, dense_count / roi_width)), 4)
        return ratio, dense_count, roi_width

    def _segmented_ratio(
        self,
        runs: list[tuple[int, int, int]],
        roi_width: int,
    ) -> tuple[float, int, int, float]:
        """点亮像素 / (段宽 x 总段数)。总段数优先 profile 元数据,否则按 ROI/周期推断。"""
        run_widths = [run[2] for run in runs]
        if not run_widths:
            return 0.0, 0, 0, 0.0
        seg_width = statistics.median(run_widths) or max(run_widths)
        gaps = [
            runs[i + 1][0] - runs[i][1] - 1
            for i in range(len(runs) - 1)
        ]
        median_gap = statistics.median(gaps) if gaps else 0
        period = seg_width + median_gap
        if self.expected_segments:
            total_segments = self.expected_segments
        elif period > 0:
            total_segments = max(
                len(runs), round(roi_width / period)
            )
        else:
            total_segments = len(runs)
        filled_pixels = sum(run_widths)
        total_pixels = total_segments * seg_width
        fraction = round(
            min(1.0, max(0.0, filled_pixels / max(1, total_pixels))), 4
        )
        partial_fraction = 0.0
        if run_widths[-1] < seg_width * 0.9:
            partial_fraction = round(run_widths[-1] / seg_width, 4)
        return fraction, len(runs), total_segments, partial_fraction

    def _confidence(
        self,
        *,
        strategy: str,
        runs: list[tuple[int, int, int]],
        width: int,
        dense_count: int,
        span: int,
    ) -> float:
        """confidence 基于布局稳定性/间距一致性/激活分离度(与 ratio 分离)。"""
        if not runs or span <= 0:
            return 0.0
        coverage = sum(run[2] for run in runs) / max(1, width)
        stability = 1.0
        if len(runs) >= 3:
            gaps = [
                runs[i + 1][0] - runs[i][1] - 1
                for i in range(len(runs) - 1)
            ]
            gaps = [g for g in gaps if g > 0]
            if gaps and statistics.mean(gaps) > 0:
                spread = statistics.pstdev(gaps) / statistics.mean(gaps)
                stability = max(0.0, 1.0 - spread)
        separation = dense_count / max(1, span)
        confidence = 0.35 * coverage + 0.35 * stability + 0.30 * separation
        return round(min(1.0, max(0.0, confidence)), 4)

    def analyze(
        self,
        mask,
        *,
        width: int,
        height: int,
    ) -> BarFillResult:
        """输入颜色掩码(与具体颜色模型解耦),输出填充率与置信度。"""
        if not _CV2_AVAILABLE:
            profile, h = self._column_profile(mask)
            height = h
        else:
            profile, h = self._column_profile(mask)
            height = h
        if not profile:
            return BarFillResult(
                strategy=self.strategy,
                ratio=None,
                confidence=0.0,
                failure=BarFailure.ROI_MISMATCH,
            )
        low = max(1, int(height * self.low_density_ratio))
        active = [value >= low for value in profile]
        runs = self._runs(active)
        if not runs:
            return BarFillResult(
                strategy=self.strategy,
                ratio=0.0,
                confidence=0.0,
                failure=BarFailure.SEGMENTS_NOT_FOUND,
            )
        any_idx = [i for i, value in enumerate(active) if value]
        span = any_idx[-1] - any_idx[0] + 1
        segmented = self._is_segmented(runs, width)
        if self.strategy == "SEGMENTED":
            segmented = True
        elif self.strategy == "CONTINUOUS":
            segmented = False
        if segmented:
            fraction, active_count, count, partial = self._segmented_ratio(
                runs, width
            )
            dense_count = sum(
                1
                for value in profile
                if value >= max(1, int(height * self.dense_density_ratio))
            )
            confidence = self._confidence(
                strategy="SEGMENTED",
                runs=runs,
                width=width,
                dense_count=dense_count,
                span=span,
            )
            failure = ""
            if count < 2:
                failure = BarFailure.SEGMENT_COUNT_UNSTABLE
            return BarFillResult(
                strategy="SEGMENTED",
                ratio=fraction,
                confidence=confidence,
                segment_count=count,
                active_segments=active_count,
                partial_segment_fraction=partial,
                failure=failure,
            )
        ratio, dense_count, span = self._continuous_ratio(
            profile, height, width
        )
        confidence = self._confidence(
            strategy="CONTINUOUS",
            runs=runs,
            width=width,
            dense_count=dense_count,
            span=span,
        )
        failure = ""
        if ratio is None:
            failure = BarFailure.COLOR_MODEL_MISMATCH
        return BarFillResult(
            strategy="CONTINUOUS",
            ratio=ratio,
            confidence=confidence,
            segment_count=len(runs),
            active_segments=len(runs),
            partial_segment_fraction=0.0,
            failure=failure,
        )
