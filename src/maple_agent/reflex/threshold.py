"""ReflexThresholds:数据驱动的阈值配置(禁止代码散落硬编码)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReflexThresholds(BaseModel):
    """L1 Reflex 阈值与事件严重度配置。"""

    low_hp_threshold: float = Field(default=0.3, ge=0, le=1)
    low_mp_threshold: float = Field(default=0.2, ge=0, le=1)
    default_max_hp: int = Field(default=1000, ge=1)
    default_max_mp: int = Field(default=1000, ge=1)
    event_severity: dict[str, float] = Field(
        default_factory=lambda: {
            "HP_LOW": 0.6,
            "MP_LOW": 0.5,
            "DEATH": 1.0,
            "STATUS_ABNORMAL": 0.7,
            "UI_ALERT": 0.6,
        }
    )

    @classmethod
    def from_dict(cls, data: dict | None) -> ReflexThresholds:
        """从外部配置(如 JSON)构建,忽略未知字段。"""
        if not data:
            return cls()
        fields = set(cls.model_fields)
        return cls(**{key: value for key, value in data.items() if key in fields})

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
