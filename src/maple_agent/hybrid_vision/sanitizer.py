"""BenchmarkPrivacySanitizer:本地原始报告 -> repository-safe 摘要。"""

from __future__ import annotations

import re
from pathlib import Path

PRIVATE_KEYS = {
    "pid",
    "hwnd",
    "window_rect",
    "client_rect",
    "screen_rect",
    "image_reference",
    "image_path",
    "local_path",
    "process_name",
    "process_exe",
    "window_title",
    "requested_title",
    "raw_value",
    "raw_text",
    "ocr_text",
    "chat",
    "username",
    "dataset_dir",
    "manifest",
    "suggested_labels",
    "ground_truth_file",
    "tesseract_cmd",
    "tessdata_dir",
}

PRIVATE_PATTERNS = [
    re.compile(r"[A-Za-z]:[\\/]"),  # Windows 绝对路径
    re.compile(r"sessions[\\/]", re.IGNORECASE),
    re.compile(r"\bpid\s*[:=]?\s*\d+", re.IGNORECASE),
    re.compile(r"\bhwnd\s*[:=]?\s*\d+", re.IGNORECASE),
    re.compile(r"\.(png|jpg|jpeg|bmp|webp)\b", re.IGNORECASE),
    re.compile(r"Users[\\/][^\\/]+", re.IGNORECASE),
]

SAFE_KEYS = {
    "schema_version",
    "sample_count",
    "sha256",
    "hash",
    "dimensions",
    "resolution",
    "dpi_scale",
    "latency",
    "mean_ms",
    "p50_ms",
    "p95_ms",
    "max_ms",
    "accuracy",
    "precision",
    "recall",
    "mae",
    "success_rate",
    "status",
    "readiness",
    "validation_status",
    "failure_taxonomy",
    "provider",
    "backend",
    "method",
    "confidence",
    "reasons",
    "count",
    "template_id",
    "kind",
    "version",
    "registered_at",
    "privacy",
}


class BenchmarkPrivacySanitizer:
    """递归清理报告中的绝对路径 / PID / HWND / 原始截图 / 聊天文本。"""

    REDACTED = "<redacted>"

    def __init__(self, *, whitelist_keys: set[str] | None = None) -> None:
        self.whitelist_keys = SAFE_KEYS | set(whitelist_keys or set())

    def sanitize_value(self, key: str, value) -> object:
        if key in PRIVATE_KEYS:
            return self.REDACTED
        if isinstance(value, str):
            if key in self.whitelist_keys and not any(
                pattern.search(value)
                for pattern in (
                    re.compile(r"[A-Za-z]:[\\/]"),
                    re.compile(r"\.(png|jpg|jpeg|bmp|webp)\b", re.I),
                    re.compile(r"Users[\\/]", re.I),
                )
            ):
                return value
            if any(pattern.search(value) for pattern in PRIVATE_PATTERNS):
                return self.REDACTED
            return value
        return value

    def sanitize_report(self, report) -> object:
        """返回 deep-copied 的 repository-safe 报告。"""
        if isinstance(report, dict):
            result: dict = {}
            for key, value in report.items():
                if key in PRIVATE_KEYS:
                    result[key] = self.REDACTED
                else:
                    result[key] = self.sanitize_value(
                        key, self.sanitize_report(value)
                    )
            return result
        if isinstance(report, list):
            return [self.sanitize_report(item) for item in report]
        return self.sanitize_value("", report)

    def assert_safe(
        self,
        report,
        *,
        private_markers: tuple[str, ...] = (
            ":\\",
            "sessions\\",
            ".png",
            "users\\",
        ),
    ) -> None:
        """断言私有键已脱敏且字符串值无路径/图片/用户名标记。"""
        if isinstance(report, dict):
            for key, value in report.items():
                if key in PRIVATE_KEYS and value != self.REDACTED:
                    raise AssertionError(
                        f"private key {key!r} not redacted: {value!r}"
                    )
                self.assert_safe(
                    value, private_markers=private_markers
                )
            return
        if isinstance(report, list):
            for item in report:
                self.assert_safe(item, private_markers=private_markers)
            return
        if isinstance(report, str):
            lowered = report.lower()
            for marker in private_markers:
                if marker.lower() in lowered:
                    raise AssertionError(
                        "repository-safe report contains private marker: "
                        f"{marker}"
                    )

    @staticmethod
    def write_local_raw(
        path: str | Path,
        report,
    ) -> Path:
        """写入 LOCAL RAW 报告(仅本地,不 commit)。"""
        import json

        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return target
