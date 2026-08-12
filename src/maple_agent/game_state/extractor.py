"""GameStateExtractor:ScreenObservation -> GameStateReference(确定性,无 LLM)。"""

from __future__ import annotations

from maple_agent.game_state.entity import EntityStateParser
from maple_agent.game_state.map import MapStateParser
from maple_agent.game_state.models import GameStateReference
from maple_agent.game_state.player import PlayerStateParser
from maple_agent.game_state.quest import QuestStateParser
from maple_agent.logging_setup import new_id
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.vision_runtime.models import ScreenObservation


class GameStateExtractor:
    """把结构化屏幕观察转为结构化 Maple 游戏状态。"""

    def __init__(
        self,
        graph: MapleKnowledgeGraph | None = None,
        *,
        player_parser: PlayerStateParser | None = None,
        map_parser: MapStateParser | None = None,
        entity_parser: EntityStateParser | None = None,
        quest_parser: QuestStateParser | None = None,
    ) -> None:
        self.graph = graph
        self.player_parser = player_parser or PlayerStateParser()
        self.map_parser = map_parser or MapStateParser(graph)
        self.entity_parser = entity_parser or EntityStateParser(graph)
        self.quest_parser = quest_parser or QuestStateParser(graph)
        self.last_reference: GameStateReference | None = None

    def extract(
        self,
        observation: ScreenObservation,
    ) -> GameStateReference:
        player = self.player_parser.parse(observation)
        current_map = self.map_parser.parse(observation)
        entities = self.entity_parser.parse(observation)
        quest_state = self.quest_parser.parse(observation)
        combat_state = self._combat_state(observation, entities)
        reasoning = [
            f"地图: {current_map.map_name or '未知'}",
            f"实体数量: {len(entities)}",
            f"任务: {', '.join(quest_state.active_quests) or '无'}",
            f"战斗状态: {combat_state}",
        ]
        reference = GameStateReference(
            state_id=new_id(),
            player_state=player,
            current_map=current_map,
            visible_entities=entities,
            quest_state=quest_state,
            combat_state=combat_state,
            confidence=observation.confidence,
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _combat_state(
        observation: ScreenObservation,
        entities: list,
    ) -> str:
        ui_text = " ".join(observation.ui_elements).lower()
        if "战斗" in ui_text or "combat" in ui_text:
            return "IN_COMBAT"
        if any(entity.type == "MONSTER" for entity in entities):
            return "ENCOUNTER"
        return "NORMAL"
