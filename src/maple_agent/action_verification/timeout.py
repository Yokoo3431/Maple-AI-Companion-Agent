"""OutcomeTimeoutPolicy:数据驱动的验证超时参考(无 Timer / 后台线程)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class OutcomeTimeoutPolicy(BaseModel):
    """各动作类型的参考超时(秒),全部数据驱动。"""

    NAVIGATE_LOCAL: float = Field(default=20.0, ge=0)
    NAVIGATE_PORTAL: float = Field(default=60.0, ge=0)
    INTERACT: float = Field(default=15.0, ge=0)
    COMBAT: float = Field(default=30.0, ge=0)
    COLLECT: float = Field(default=30.0, ge=0)
    VERIFY: float = Field(default=10.0, ge=0)
    WAIT: float = Field(default=15.0, ge=0)
    OBSERVE: float = Field(default=10.0, ge=0)
    DEFAULT: float = Field(default=30.0, ge=0)

    @classmethod
    def from_dict(cls, data: dict | None) -> OutcomeTimeoutPolicy:
        if not data:
            return cls()
        fields = set(cls.model_fields)
        return cls(
            **{
                key: value
                for key, value in data.items()
                if key in fields
            }
        )

    def timeout_for(
        self,
        action_type: str,
        *,
        cross_map: bool = False,
    ) -> float:
        mapping = {
            "NAVIGATE": (
                self.NAVIGATE_PORTAL
                if cross_map
                else self.NAVIGATE_LOCAL
            ),
            "INTERACT": self.INTERACT,
            "COMBAT": self.COMBAT,
            "COLLECT": self.COLLECT,
            "VERIFY": self.VERIFY,
            "WAIT": self.WAIT,
            "OBSERVE": self.OBSERVE,
        }
        return float(mapping.get(action_type, self.DEFAULT))

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
