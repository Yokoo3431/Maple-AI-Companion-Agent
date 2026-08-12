"""GoalReasoner:任务状态 -> 目标参考(只读,不执行)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.quest_reasoning.models import (
    GoalReference,
    GoalType,
    QuestProgressReference,
    QuestStateType,
)


class GoalReasoner:
    """把任务进度转换为可能的目标参考。"""

    def reason(
        self,
        progress: list[QuestProgressReference],
    ) -> tuple[list[GoalReference], list[GoalReference]]:
        recommended: list[GoalReference] = []
        blocked: list[GoalReference] = []
        for item in progress:
            if item.state is QuestStateType.AVAILABLE:
                target = (
                    item.completed_requirements[0]
                    if item.completed_requirements
                    else item.quest_name
                )
                recommended.append(
                    GoalReference(
                        goal_id=new_id(),
                        goal_type=GoalType.NPC_INTERACTION_REFERENCE,
                        description=f"与{target}交互",
                        priority=item.progress_confidence,
                        related_quest=item.quest_name,
                        confidence=item.progress_confidence,
                        reasoning=(
                            f"任务 {item.quest_name} 处于 AVAILABLE,"
                            f"建议与 {target} 交互"
                        ),
                    )
                )
            elif item.state in (
                QuestStateType.ACCEPTED,
                QuestStateType.IN_PROGRESS,
            ):
                recommended.append(
                    GoalReference(
                        goal_id=new_id(),
                        goal_type=GoalType.QUEST_PROGRESS,
                        description=f"完成进行中任务: {item.quest_name}",
                        priority=item.progress_confidence,
                        related_quest=item.quest_name,
                        confidence=item.progress_confidence,
                        reasoning=(
                            f"任务 {item.quest_name} 已接受/进行中,"
                            "建议推进任务进度"
                        ),
                    )
                )
            elif item.state is QuestStateType.REQUIREMENT_PENDING:
                recommended.append(
                    GoalReference(
                        goal_id=new_id(),
                        goal_type=GoalType.QUEST_PROGRESS,
                        description=(
                            f"推进任务: {item.quest_name}; 待完成: "
                            + ", ".join(item.pending_requirements)
                        ),
                        priority=item.progress_confidence,
                        related_quest=item.quest_name,
                        confidence=item.progress_confidence,
                        reasoning="存在未满足条件,建议推进需求收集",
                    )
                )
            elif item.state is QuestStateType.BLOCKED:
                blocked.append(
                    GoalReference(
                        goal_id=new_id(),
                        goal_type=GoalType.EXPLORATION_REFERENCE,
                        description=f"前往任务地点处理: {item.quest_name}",
                        priority=item.progress_confidence,
                        related_quest=item.quest_name,
                        confidence=item.progress_confidence,
                        reasoning="任务所需地点与当前环境不一致,先确认位置",
                    )
                )
            elif item.state is QuestStateType.UNKNOWN:
                recommended.append(
                    GoalReference(
                        goal_id=new_id(),
                        goal_type=GoalType.KNOWLEDGE_QUERY,
                        description=f"查询任务知识: {item.quest_name}",
                        priority=item.progress_confidence,
                        related_quest=item.quest_name,
                        confidence=item.progress_confidence,
                        reasoning="任务状态信息不足,建议补充知识查询",
                    )
                )
        return recommended, blocked
