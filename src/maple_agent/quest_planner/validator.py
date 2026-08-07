"""QuestPlanValidator:步骤完整性 / 数据一致性 / 安全检查。"""

from __future__ import annotations

from maple_agent.quest.models import Quest
from maple_agent.quest_planner.models import QuestPlan

_PHYSICAL_KEYWORDS = ("click", "press", "key", "mouse", "input", "execute")


class QuestPlanValidationError(ValueError):
    """任务计划校验失败。"""


class QuestPlanValidator:
    def validate(self, plan: QuestPlan, quest: Quest | None = None) -> None:
        if not plan.steps:
            raise QuestPlanValidationError("计划为空(无步骤)")
        for step in plan.steps:
            text = f"{step.action.value} {step.description} {step.target}".lower()
            if any(keyword in text for keyword in _PHYSICAL_KEYWORDS):
                raise QuestPlanValidationError(
                    f"发现物理动作关键字: {step.description!r}"
                )
        if quest is None:
            return
        monster_ids = {str(item) for item in quest.monster_ids}
        for step in plan.steps:
            if (
                step.related_monster is not None
                and monster_ids
                and str(step.related_monster) not in monster_ids
            ):
                raise QuestPlanValidationError(
                    f"怪物不一致: 计划 {step.related_monster} != 任务 {sorted(monster_ids)}"
                )
            if (
                step.related_npc is not None
                and quest.npc_id is not None
                and str(step.related_npc) != str(quest.npc_id)
            ):
                raise QuestPlanValidationError(
                    f"NPC 不一致: 计划 {step.related_npc} != 任务 {quest.npc_id}"
                )
            if (
                step.related_map is not None
                and quest.map_id is not None
                and str(step.related_map) != str(quest.map_id)
            ):
                raise QuestPlanValidationError(
                    f"地图不一致: 计划 {step.related_map} != 任务 {quest.map_id}"
                )
