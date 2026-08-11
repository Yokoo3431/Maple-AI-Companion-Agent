"""EnvironmentOpportunityDetector:环境机会识别(只读)。"""

from __future__ import annotations

from maple_agent.context.models import KnowledgeState
from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_reasoning.models import (
    OpportunityReference,
    OpportunityType,
)
from maple_agent.world_model.models import EnvironmentHistory


class EnvironmentOpportunityDetector:
    """识别 NPC 交互 / 资源 / 任务进度 / 安全区 / 新发现。"""

    def detect(
        self,
        *,
        environment_state: EnvironmentState,
        history: EnvironmentHistory | None = None,
        knowledge_state: KnowledgeState | None = None,
    ) -> list[OpportunityReference]:
        opportunities: list[OpportunityReference] = []
        npcs = self._known_npcs(environment_state, knowledge_state)
        if npcs:
            opportunities.append(
                OpportunityReference(
                    opportunity_type=OpportunityType.NPC_INTERACTION,
                    detail=f"可与 NPC 交互: {', '.join(npcs)}",
                    confidence=environment_state.confidence,
                    related_entities=npcs,
                )
            )
        if environment_state.resources:
            opportunities.append(
                OpportunityReference(
                    opportunity_type=OpportunityType.RESOURCE_AVAILABLE,
                    detail=(
                        "资源可用: "
                        + ", ".join(environment_state.resources)
                    ),
                    confidence=environment_state.confidence,
                    related_entities=environment_state.resources,
                )
            )
        if (
            environment_state.visible_entities
            and environment_state.confidence >= 0.7
        ):
            opportunities.append(
                OpportunityReference(
                    opportunity_type=OpportunityType.TASK_PROGRESS,
                    detail="环境稳定,可推进任务",
                    confidence=environment_state.confidence,
                )
            )
        monsters = self._known_monsters(
            environment_state,
            knowledge_state,
        )
        if not monsters and environment_state.confidence >= 0.7:
            opportunities.append(
                OpportunityReference(
                    opportunity_type=OpportunityType.SAFE_AREA,
                    detail="未检测到威胁,安全区域",
                    confidence=environment_state.confidence,
                )
            )
        if self._is_new_location(environment_state, history):
            opportunities.append(
                OpportunityReference(
                    opportunity_type=OpportunityType.NEW_DISCOVERY,
                    detail=f"新区域发现: {environment_state.location}",
                    confidence=environment_state.confidence,
                )
            )
        return opportunities

    @staticmethod
    def _known_npcs(
        environment_state: EnvironmentState,
        knowledge_state: KnowledgeState | None,
    ) -> list[str]:
        if knowledge_state is not None:
            return [
                entity.name
                for entity in knowledge_state.matched_entities
                if entity.entity_type == "npc"
            ]
        return []

    @staticmethod
    def _known_monsters(
        environment_state: EnvironmentState,
        knowledge_state: KnowledgeState | None,
    ) -> list[str]:
        if knowledge_state is not None:
            return [
                entity.name
                for entity in knowledge_state.matched_entities
                if entity.entity_type == "monster"
            ]
        return []

    @staticmethod
    def _is_new_location(
        environment_state: EnvironmentState,
        history: EnvironmentHistory | None,
    ) -> bool:
        if history is None or not history.snapshots:
            return False
        known = {
            snapshot.location
            for snapshot in history.snapshots[:-1]
            if snapshot.location
        }
        return (
            bool(environment_state.location)
            and environment_state.location not in known
        )
