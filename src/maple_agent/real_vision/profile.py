"""VisionROIProfile:只读 ROI 配置(数据驱动,禁止散落坐标)。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class VisionROIProfile(BaseModel):
    """视觉 ROI 布局配置。"""

    profile_id: str
    game_profile: str
    server_profile: str = ""
    resolution: str
    window_mode: str
    dpi_scale: float = Field(default=1.0, ge=0)
    map_label_roi: dict = Field(default_factory=dict)
    hp_roi: dict = Field(default_factory=dict)
    mp_roi: dict = Field(default_factory=dict)
    quest_roi: dict = Field(default_factory=dict)
    dialog_roi: dict = Field(default_factory=dict)


DEFAULT_PROFILES_DIR = (
    Path(__file__).resolve().parents[3] / "configs" / "vision_profiles"
)


def load_vision_profiles(
    profiles_dir: str | Path | None = None,
) -> dict[str, VisionROIProfile]:
    """加载全部 ROI profile;缺失时返回空 dict。"""
    directory = Path(profiles_dir) if profiles_dir else DEFAULT_PROFILES_DIR
    profiles: dict[str, VisionROIProfile] = {}
    if not directory.is_dir():
        return profiles
    for path in sorted(directory.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        profile = VisionROIProfile(**data)
        profiles[profile.profile_id] = profile
    return profiles
