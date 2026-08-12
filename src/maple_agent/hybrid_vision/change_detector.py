"""FrameChangeDetector:轻量帧/ROI 变化检测(无变化 -> 禁止重复昂贵 OCR)。"""

from __future__ import annotations

import hashlib
import os
import statistics

from maple_agent.hybrid_vision.models import ChangeResult

try:  # cv2/numpy 可选:Home PC 有,CI 无 -> 自动降级 PIL 直方图模式
    import cv2  # type: ignore[import-not-found]
    import numpy as np  # type: ignore[import-not-found]

    _CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None
    _CV2_AVAILABLE = False


def _load_gray(image) -> object:
    """加载图像为灰度数组;支持路径 / PIL Image / ndarray。"""
    if isinstance(image, os.PathLike):
        image = str(image)
    if _CV2_AVAILABLE:
        if isinstance(image, str):
            array = cv2.imread(image, cv2.IMREAD_GRAYSCALE)
            if array is None:
                raise ValueError(f"cannot read image: {image}")
            return array
        if hasattr(image, "convert"):  # PIL Image
            import numpy as np2

            return np2.asarray(image.convert("L"), dtype=np2.uint8)
        return image
    from PIL import Image

    if not hasattr(image, "convert"):
        image = Image.open(image)
    return image.convert("L")


def _dhash(array, size: int = 8) -> str:
    """感知哈希(灰度差分),用于稳定区域判断。"""
    if _CV2_AVAILABLE:
        resized = cv2.resize(
            array, (size + 1, size), interpolation=cv2.INTER_AREA
        )
        diff = resized[:, 1:] > resized[:, :-1]
        return hashlib.md5(diff.tobytes()).hexdigest()
    resized = array.resize((size + 1, size))
    pixels = list(resized.getdata())
    bits: list[str] = []
    for row in range(size):
        for col in range(size):
            bits.append(
                "1"
                if pixels[row * (size + 1) + col + 1]
                > pixels[row * (size + 1) + col]
                else "0"
            )
    return hashlib.md5("".join(bits).encode()).hexdigest()


class FrameChangeDetector:
    """整帧 + ROI 级变化检测。

    score = 0..1(1 = 完全变化)。全帧使用灰度差 + 直方图差 + dhash;
    ROI 使用 ROI 内灰度差。cv2 缺失时自动降级 PIL 直方图模式。
    """

    def __init__(self, *, threshold: float = 0.05) -> None:
        self.threshold = threshold
        self._previous_frame: object | None = None
        self._previous_hash = ""
        self._previous_roi: dict[str, object] = {}
        self.backend = "cv2" if _CV2_AVAILABLE else "pil"

    def reset(self) -> None:
        self._previous_frame = None
        self._previous_hash = ""
        self._previous_roi = {}

    @staticmethod
    def _mean_abs_diff(previous, current) -> float:
        if _CV2_AVAILABLE:
            if previous.shape != current.shape:
                current = cv2.resize(
                    current,
                    (previous.shape[1], previous.shape[0]),
                )
            return float(cv2.absdiff(previous, current).mean() / 255.0)
        prev_hist = previous.histogram()
        curr_hist = current.histogram()
        total = sum(max(a, b) for a, b in zip(prev_hist, curr_hist)) or 1
        diff = sum(abs(a - b) for a, b in zip(prev_hist, curr_hist))
        return min(1.0, diff / total)

    def _crop(self, image, roi: dict):
        if _CV2_AVAILABLE:
            x = int(roi.get("x", 0))
            y = int(roi.get("y", 0))
            width = int(roi.get("width", 0))
            height = int(roi.get("height", 0))
            return image[y : y + height, x : x + width]
        box = (
            int(roi.get("x", 0)),
            int(roi.get("y", 0)),
            int(roi.get("x", 0)) + int(roi.get("width", 0)),
            int(roi.get("y", 0)) + int(roi.get("height", 0)),
        )
        return image.crop(box)

    def detect(
        self,
        image,
        *,
        frame_id: str = "",
        rois: dict[str, dict] | None = None,
    ) -> ChangeResult:
        """检测相对上一帧的变化;第一帧总是 changed=True。"""
        current = _load_gray(image)
        roi_scores: dict[str, float] = {}
        if self._previous_frame is None:
            self._previous_frame = current
            self._previous_hash = _dhash(current)
            if rois:
                self._previous_roi = {
                    name: self._crop(current, roi)
                    for name, roi in rois.items()
                }
                roi_scores = {name: 1.0 for name in rois}
            return ChangeResult(
                frame_id=frame_id,
                changed=True,
                score=1.0,
                roi_scores=roi_scores,
                method=self.backend,
            )
        current_hash = _dhash(current)
        frame_score = self._mean_abs_diff(
            self._previous_frame, current
        )
        if current_hash != self._previous_hash:
            frame_score = max(frame_score, 0.5)
        if rois:
            for name, roi in rois.items():
                previous_roi = self._previous_roi.get(name)
                current_roi = self._crop(current, roi)
                score = (
                    self._mean_abs_diff(previous_roi, current_roi)
                    if previous_roi is not None
                    else 1.0
                )
                roi_scores[name] = round(score, 4)
                self._previous_roi[name] = current_roi
        self._previous_frame = current
        self._previous_hash = current_hash
        return ChangeResult(
            frame_id=frame_id,
            changed=frame_score >= self.threshold,
            score=round(frame_score, 4),
            roi_scores={
                name: round(score, 4)
                for name, score in roi_scores.items()
            },
            method=self.backend,
        )


class ChangeDetectorBenchmark:
    """变化检测 benchmark:false change / missed change / latency。"""

    @staticmethod
    def evaluate(
        frames: list,
        *,
        expected_changes: list[bool] | None = None,
        rois: dict[str, dict] | None = None,
        detector: FrameChangeDetector | None = None,
    ) -> dict:
        detector = detector or FrameChangeDetector()
        results: list[ChangeResult] = []
        latencies: list[float] = []
        for frame in frames:
            start = __import__("time").perf_counter()
            result = detector.detect(frame, rois=rois)
            latencies.append(
                (__import__("time").perf_counter() - start) * 1000
            )
            results.append(result)
        predicted = [result.changed for result in results]
        if expected_changes is not None:
            false_change = sum(
                1
                for expected, actual in zip(expected_changes, predicted)
                if not expected and actual
            )
            missed_change = sum(
                1
                for expected, actual in zip(expected_changes, predicted)
                if expected and not actual
            )
        else:
            false_change = 0
            missed_change = 0
        return {
            "backend": detector.backend,
            "frames": len(frames),
            "false_change": false_change,
            "missed_change": missed_change,
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 4)
                if latencies
                else None,
                "p50": round(statistics.median(latencies), 4)
                if latencies
                else None,
                "p95": round(
                    sorted(latencies)[
                        max(0, int(0.95 * len(latencies)) - 1)
                    ],
                    4,
                )
                if latencies
                else None,
                "max": round(max(latencies), 4) if latencies else None,
            },
        }
