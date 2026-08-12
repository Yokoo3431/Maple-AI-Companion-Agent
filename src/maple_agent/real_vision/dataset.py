"""VisionValidationDataset:真实视觉验证数据集 manifest(不进仓库截图)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.real_vision.models import VisionValidationSample


class VisionValidationDataset:
    """样本集合 + manifest 读写。"""

    def __init__(
        self,
        samples: list[VisionValidationSample] | None = None,
        *,
        manifest: dict | None = None,
    ) -> None:
        self.samples: list[VisionValidationSample] = list(samples or [])
        self.manifest: dict = dict(manifest or {})

    @classmethod
    def from_manifest(cls, path: str | Path) -> VisionValidationDataset:
        manifest_path = Path(path)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        samples = [
            VisionValidationSample(**item)
            for item in data.get("samples", [])
        ]
        return cls(samples, manifest=data)

    def add_sample(self, sample: VisionValidationSample) -> None:
        self.samples.append(sample)

    def count(self) -> int:
        return len(self.samples)

    def save_manifest(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": "1.0",
            "manifest": self.manifest,
            "samples": [
                sample.model_dump(mode="json") for sample in self.samples
            ],
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
