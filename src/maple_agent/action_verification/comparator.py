"""GameStateComparator:Before/After 状态比较 -> 结构化证据(确定性)。"""

from __future__ import annotations

from maple_agent.action_verification.models import OutcomeEvidence
from maple_agent.game_state.models import GameStateReference
from maple_agent.reflex.models import ReflexReference


class GameStateComparator:
    """比较前后游戏状态并生成结果证据。"""

    @staticmethod
    def _change(
        evidence_type: str,
        before_value: str,
        after_value: str,
        confidence: float = 0.8,
    ) -> OutcomeEvidence:
        return OutcomeEvidence(
            evidence_type=evidence_type,
            before_value=str(before_value),
            after_value=str(after_value),
            matched=str(before_value) != str(after_value),
            confidence=confidence,
            reason=f"{evidence_type}: {before_value} -> {after_value}",
        )

    def compare(
        self,
        before: GameStateReference,
        after: GameStateReference,
        *,
        target: str = "",
        reflex_before: ReflexReference | None = None,
        reflex_after: ReflexReference | None = None,
    ) -> list[OutcomeEvidence]:
        evidence: list[OutcomeEvidence] = []
        before_map = (
            before.current_map.map_name
            if before.current_map is not None
            else ""
        )
        after_map = (
            after.current_map.map_name
            if after.current_map is not None
            else ""
        )
        evidence.append(
            self._change("MAP_CHANGED", before_map, after_map)
        )
        before_entities = {
            entity.name: entity for entity in before.visible_entities
        }
        after_entities = {
            entity.name: entity for entity in after.visible_entities
        }
        if target:
            before_visible = target in before_entities
            after_visible = target in after_entities
            evidence.append(
                OutcomeEvidence(
                    evidence_type="TARGET_VISIBLE",
                    before_value=str(before_visible),
                    after_value=str(after_visible),
                    matched=after_visible,
                    confidence=0.85,
                    reason=f"目标 {target} 可见性",
                )
            )
            evidence.append(
                OutcomeEvidence(
                    evidence_type="TARGET_DISAPPEARED",
                    before_value=str(before_visible),
                    after_value=str(after_visible),
                    matched=before_visible and not after_visible,
                    confidence=0.85,
                    reason=f"目标 {target} 消失",
                )
            )
        before_monsters = sum(
            1
            for entity in before_entities.values()
            if entity.type == "MONSTER"
        )
        after_monsters = sum(
            1
            for entity in after_entities.values()
            if entity.type == "MONSTER"
        )
        evidence.append(
            self._change(
                "MONSTER_COUNT_CHANGED",
                before_monsters,
                after_monsters,
            )
        )
        before_npcs = sum(
            1
            for entity in before_entities.values()
            if entity.type == "NPC"
        )
        after_npcs = sum(
            1
            for entity in after_entities.values()
            if entity.type == "NPC"
        )
        evidence.append(
            self._change("NPC_PRESENT", before_npcs, after_npcs)
        )
        before_hp = (
            before.player_state.hp
            if before.player_state is not None
            else None
        )
        after_hp = (
            after.player_state.hp
            if after.player_state is not None
            else None
        )
        evidence.append(self._change("HP_CHANGED", before_hp, after_hp))
        before_mp = (
            before.player_state.mp
            if before.player_state is not None
            else None
        )
        after_mp = (
            after.player_state.mp
            if after.player_state is not None
            else None
        )
        evidence.append(self._change("MP_CHANGED", before_mp, after_mp))
        before_active = (
            list(before.quest_state.active_quests)
            if before.quest_state is not None
            else []
        )
        after_active = (
            list(after.quest_state.active_quests)
            if after.quest_state is not None
            else []
        )
        evidence.append(
            self._change(
                "QUEST_PROGRESS_CHANGED",
                before_active,
                after_active,
                confidence=0.9,
            )
        )
        before_completed = (
            list(before.quest_state.completed_reference)
            if before.quest_state is not None
            else []
        )
        after_completed = (
            list(after.quest_state.completed_reference)
            if after.quest_state is not None
            else []
        )
        evidence.append(
            self._change(
                "QUEST_COMPLETED",
                before_completed,
                after_completed,
            )
        )
        evidence.append(
            self._change(
                "COMBAT_STATE_CHANGED",
                before.combat_state,
                after.combat_state,
            )
        )
        evidence.append(
            self._change(
                "CONFIDENCE_CHANGED",
                before.confidence,
                after.confidence,
            )
        )
        before_reflex = (
            reflex_before.state.value if reflex_before is not None else ""
        )
        after_reflex = (
            reflex_after.state.value if reflex_after is not None else ""
        )
        evidence.append(
            self._change(
                "REFLEX_CHANGED",
                before_reflex,
                after_reflex,
            )
        )
        return evidence
