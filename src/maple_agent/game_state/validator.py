"""GameStateValidator:游戏状态参考校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.game_state.models import GameStateReference


class GameStateVerdict(StrEnum):
    """游戏状态校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class GameStateValidationResult(BaseModel):
    """游戏状态校验结果。"""

    verdict: GameStateVerdict
    issues: list[str] = Field(default_factory=list)


class GameStateValidator:
    """检查状态完整性 / 数值范围 / 数据可信度。"""

    def validate(
        self,
        reference: GameStateReference,
    ) -> GameStateValidationResult:
        if not reference.state_id:
            return GameStateValidationResult(
                verdict=GameStateVerdict.BLOCKED,
                issues=["missing state id"],
            )
        if not (0 <= reference.confidence <= 1):
            return GameStateValidationResult(
                verdict=GameStateVerdict.BLOCKED,
                issues=["confidence out of range"],
            )
        if reference.player_state is not None:
            for value in (
                reference.player_state.hp,
                reference.player_state.mp,
            ):
                if value is not None and not (0 <= value <= 1):
                    return GameStateValidationResult(
                        verdict=GameStateVerdict.BLOCKED,
                        issues=["hp/mp out of range"],
                    )
        issues: list[str] = []
        if (
            reference.current_map is None
            or not reference.current_map.map_name
        ):
            issues.append("missing map")
        elif not reference.current_map.known_map:
            issues.append("unknown map")
        if not reference.visible_entities:
            issues.append("missing entities")
        if (
            reference.player_state is None
            or reference.player_state.hp is None
            or reference.player_state.mp is None
        ):
            issues.append("missing hp/mp")
        if reference.confidence < 0.5:
            issues.append("low confidence")
        verdict = (
            GameStateVerdict.VALID
            if not issues
            else GameStateVerdict.WARNING
        )
        return GameStateValidationResult(verdict=verdict, issues=issues)
