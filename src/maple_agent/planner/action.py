"""Planner 允许的动作枚举(仅感知/分析类,禁止物理动作)。"""

from __future__ import annotations

from enum import StrEnum


class PlannerAction(StrEnum):
    """计划步骤允许的动作(Phase 1.8-A:不含 Executor/Input/键盘/鼠标/游戏控制)。"""

    OBSERVE = "observe"
    ANALYZE = "analyze"
    QUERY_KNOWLEDGE = "query_knowledge"
    WAIT = "wait"
    PAUSE = "pause"


ALLOWED_ACTIONS = frozenset(action.value for action in PlannerAction)
