"""Canonical read-only game window identity profiles."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class GameWindowProfile(BaseModel):
    """候选客户端身份;不执行窗口激活或控制。"""

    model_config = ConfigDict(frozen=True)

    profile_id: str
    process_candidates: tuple[str, ...] = Field(min_length=1)
    title_candidates: tuple[str, ...] = Field(min_length=1)

    @classmethod
    def maple_classic_cn(cls) -> GameWindowProfile:
        """当前国服怀旧服客户端与历史英文 fixture 的兼容 profile。"""
        return cls(
            profile_id="maple_classic_cn",
            process_candidates=("Maplestory_Classic", "MapleStory.exe"),
            title_candidates=("冒险岛怀旧服", "MapleStory"),
        )

    @property
    def primary_process(self) -> str:
        return self.process_candidates[0]

    @property
    def primary_title(self) -> str:
        return self.title_candidates[0]

    def with_title_candidates(
        self, title_candidates: tuple[str, ...]
    ) -> GameWindowProfile:
        """返回只替换标题候选的 profile,保留统一进程候选。"""
        return self.model_copy(update={"title_candidates": title_candidates})


def default_game_window_profile() -> GameWindowProfile:
    """项目唯一默认客户端身份来源。"""
    return GameWindowProfile.maple_classic_cn()
