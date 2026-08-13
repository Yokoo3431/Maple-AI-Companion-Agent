"""Normalized ROI + VisionProfileTransformer + Profile 继承(Phase 13-I.2)。

目标:Base Profile(归一化布局)+ Resolution/DPI Transform + 可选机器校准 Overlay,
避免无限设备硬编码(home_pc_xxx / office_pc_xxx ...)。
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field


class NormalizedROI(BaseModel):
    """0..1 相对 client 尺寸的 ROI。"""

    x: float = Field(default=0.0, ge=0, le=1)
    y: float = Field(default=0.0, ge=0, le=1)
    width: float = Field(default=0.0, ge=0, le=1)
    height: float = Field(default=0.0, ge=0, le=1)


class VisionProfile(BaseModel):
    """视觉 profile(可继承 base,仅保存机器特异差异)。"""

    profile_id: str
    game_profile: str = ""
    server_profile: str = ""
    base_profile: str = ""
    # 明确区分 DISPLAY RESOLUTION 与 GAME CLIENT RESOLUTION:
    # resolution = game client(transform 目标);display_resolution = 显示器(仅元数据)
    resolution: str = ""
    display_resolution: str = ""
    window_mode: str = ""
    dpi_scale: float = Field(default=1.0, ge=0)
    normalized_rois: dict[str, NormalizedROI] = Field(
        default_factory=dict
    )
    calibration_overlay: dict = Field(default_factory=dict)
    # 向后兼容:旧 pixel ROI 格式(map_label_roi/hp_roi/...)
    legacy_pixel_rois: dict = Field(default_factory=dict)

    def resolved_rois(
        self,
        base: VisionProfile | None = None,
    ) -> dict[str, NormalizedROI]:
        """合并 base + 自身 normalized(自身优先)。"""
        merged: dict[str, NormalizedROI] = {}
        if base is not None:
            merged.update(base.normalized_rois)
        merged.update(self.normalized_rois)
        return merged


class VisionProfileTransformer:
    """Pixel <-> Normalized 确定性转换(含 rounding 与 DPI 元数据)。"""

    @staticmethod
    def to_normalized(
        pixel_roi: dict,
        *,
        client_width: int,
        client_height: int,
    ) -> NormalizedROI:
        width = max(1, int(pixel_roi.get("width", 0)))
        height = max(1, int(pixel_roi.get("height", 0)))
        return NormalizedROI(
            x=round(int(pixel_roi.get("x", 0)) / client_width, 6),
            y=round(int(pixel_roi.get("y", 0)) / client_height, 6),
            width=round(width / client_width, 6),
            height=round(height / client_height, 6),
        )

    @staticmethod
    def to_pixel(
        roi: NormalizedROI,
        *,
        client_width: int,
        client_height: int,
        dpi_scale: float = 1.0,
    ) -> dict:
        """像素 ROI 基于 client-local 坐标(与 desktop absolute 无关)。"""
        return {
            "x": int(round(roi.x * client_width * dpi_scale)),
            "y": int(round(roi.y * client_height * dpi_scale)),
            "width": int(round(roi.width * client_width * dpi_scale)),
            "height": int(round(roi.height * client_height * dpi_scale)),
        }

    @staticmethod
    def resolve_pixel_rois(
        profile: VisionProfile,
        *,
        base: VisionProfile | None = None,
        client_width: int,
        client_height: int,
        dpi_scale: float | None = None,
    ) -> dict[str, dict]:
        """base 归一化 ROI -> 目标分辨率像素 ROI(确定性)。"""
        scale = dpi_scale if dpi_scale is not None else profile.dpi_scale
        rois = profile.resolved_rois(base)
        return {
            name: VisionProfileTransformer.to_pixel(
                roi,
                client_width=client_width,
                client_height=client_height,
                dpi_scale=scale,
            )
            for name, roi in rois.items()
        }

    @staticmethod
    def migrate_legacy(
        profile: VisionProfile,
        *,
        client_width: int,
        client_height: int,
    ) -> VisionProfile:
        """旧 pixel ROI -> normalized(向后兼容迁移)。"""
        if profile.normalized_rois:
            return profile
        names = {
            "map_label_roi": "map_label",
            "hp_roi": "hp",
            "mp_roi": "mp",
            "quest_roi": "quest",
            "dialog_roi": "dialog",
        }
        normalized: dict[str, NormalizedROI] = {}
        for key, name in names.items():
            roi = profile.legacy_pixel_rois.get(key)
            if roi:
                normalized[name] = VisionProfileTransformer.to_normalized(
                    roi,
                    client_width=client_width,
                    client_height=client_height,
                )
        return profile.model_copy(
            update={
                "normalized_rois": normalized,
                "legacy_pixel_rois": profile.legacy_pixel_rois,
            }
        )


DEFAULT_PROFILES_DIR = (
    Path(__file__).resolve().parents[3] / "configs" / "vision_profiles"
)


class VisionProfileRegistry:
    """加载 base + machine profile,解析继承(不复制坐标)。"""

    def __init__(
        self,
        profiles_dir: str | Path | None = None,
    ) -> None:
        self.profiles_dir = Path(
            profiles_dir or DEFAULT_PROFILES_DIR
        )
        self.profiles: dict[str, VisionProfile] = {}
        self.load_all()

    def load_all(self) -> None:
        if not self.profiles_dir.is_dir():
            return
        for path in sorted(self.profiles_dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            profile = self._parse(data)
            self.profiles[profile.profile_id] = profile

    @staticmethod
    def _parse(data: dict) -> VisionProfile:
        normalized = {
            key: NormalizedROI(**value)
            for key, value in data.get("normalized_rois", {}).items()
        }
        legacy = {
            key: value
            for key, value in data.items()
            if key.endswith("_roi") and isinstance(value, dict)
        }
        return VisionProfile(
            profile_id=data.get("profile_id", ""),
            game_profile=data.get("game_profile", ""),
            server_profile=data.get("server_profile", ""),
            base_profile=data.get("base_profile", ""),
            resolution=data.get("resolution", ""),
            display_resolution=data.get("display_resolution", ""),
            window_mode=data.get("window_mode", ""),
            dpi_scale=float(data.get("dpi_scale", 1.0)),
            normalized_rois=normalized,
            calibration_overlay=data.get(
                "calibration_overlay",
                {},
            ),
            legacy_pixel_rois=legacy,
        )

    def get(
        self,
        profile_id: str,
    ) -> VisionProfile | None:
        return self.profiles.get(profile_id)

    def resolved(
        self,
        profile_id: str,
    ) -> VisionProfile:
        """返回继承 base 后的合并 profile(归一化 ROI 层)。"""
        profile = self.get(profile_id)
        if profile is None:
            raise KeyError(profile_id)
        base = (
            self.get(profile.base_profile)
            if profile.base_profile
            else None
        )
        return profile.model_copy(
            update={
                "normalized_rois": profile.resolved_rois(base),
                "legacy_pixel_rois": {},
            }
        )


def parse_resolution(value: str) -> tuple[int, int]:
    """解析 'WxH' -> (width, height);失败返回 (0, 0)。"""
    parts = (value or "").lower().split("x")
    if len(parts) == 2:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            pass
    return 0, 0


def resolve_pixel_rois_for(
    registry: VisionProfileRegistry,
    profile_id: str,
    *,
    client_width: int,
    client_height: int,
    dpi_scale: float | None = None,
) -> dict[str, dict]:
    """base 归一化/legacy pixel -> 目标 client 分辨率像素 ROI。

    兼容两类 profile:含 normalized_rois(含 base 继承)与旧 pixel 格式
    (home_pc_2560x1440,自动迁移)。transform 一律基于 GAME CLIENT 分辨率。
    """
    profile = registry.get(profile_id)
    if profile is None:
        raise KeyError(profile_id)
    scale = dpi_scale if dpi_scale is not None else profile.dpi_scale
    base = (
        registry.get(profile.base_profile)
        if profile.base_profile
        else None
    )
    normalized = profile.resolved_rois(base)
    if not normalized and profile.legacy_pixel_rois:
        own_width, own_height = parse_resolution(
            profile.resolution or f"{client_width}x{client_height}"
        )
        migrated = VisionProfileTransformer.migrate_legacy(
            profile,
            client_width=own_width or client_width,
            client_height=own_height or client_height,
        )
        normalized = migrated.normalized_rois
        if base:
            normalized = {**base.normalized_rois, **normalized}
    return {
        name: VisionProfileTransformer.to_pixel(
            roi,
            client_width=client_width,
            client_height=client_height,
            dpi_scale=scale,
        )
        for name, roi in normalized.items()
    }
