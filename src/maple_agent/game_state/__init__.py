"""Game State Understanding 层(Phase 11-B,结构化 Maple 游戏状态,只读)。"""

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.game_state.entity import EntityStateParser
from maple_agent.game_state.extractor import GameStateExtractor
from maple_agent.game_state.map import MapStateParser
from maple_agent.game_state.models import (
    CurrentObservation,
    EntityLifecycle,
    EntityStateReference,
    GameStateReference,
    MapStateReference,
    PlayerStateReference,
    QuestStateSnapshot,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.game_state.player import PlayerStateParser
from maple_agent.game_state.quest import QuestStateParser
from maple_agent.game_state.semantic import (
    SemanticStateResolver,
    save_semantic_state_trace,
)
from maple_agent.game_state.temporal import (
    ObservationHistory,
    ObservationHistoryEntry,
    SemanticStateTransition,
    StateReducer,
    save_semantic_memory_trace,
)
from maple_agent.game_state.validator import (
    GameStateValidationResult,
    GameStateValidator,
    GameStateVerdict,
)


def save_game_state_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    player_state: PlayerStateReference | None,
    map_state: MapStateReference | None,
    entities: list[EntityStateReference],
    quest_state: QuestStateSnapshot | None,
    validation: str,
) -> None:
    """写入 game_state_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "player_state": (
            player_state.model_dump(mode="json")
            if player_state is not None
            else {}
        ),
        "map_state": (
            map_state.model_dump(mode="json")
            if map_state is not None
            else {}
        ),
        "entities": [
            entity.model_dump(mode="json") for entity in entities
        ],
        "quest_state": (
            quest_state.model_dump(mode="json")
            if quest_state is not None
            else {}
        ),
        "validation": validation,
    }
    (directory / "game_state_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


__all__ = [
    "EntityStateParser",
    "EntityStateReference",
    "CurrentObservation",
    "EntityLifecycle",
    "GameStateExtractor",
    "GameStateReference",
    "GameStateValidationResult",
    "GameStateValidator",
    "GameStateVerdict",
    "MapStateParser",
    "MapStateReference",
    "PlayerStateParser",
    "PlayerStateReference",
    "QuestStateParser",
    "QuestStateSnapshot",
    "SemanticEntityReference",
    "SemanticGameState",
    "SemanticStateResolver",
    "ObservationHistory",
    "ObservationHistoryEntry",
    "SemanticStateTransition",
    "StateReducer",
    "save_semantic_memory_trace",
    "save_semantic_state_trace",
    "save_game_state_trace",
]
