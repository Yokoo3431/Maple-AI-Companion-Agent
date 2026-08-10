"""ExperienceEvaluator:历史经验与当前情境的相关性评分。"""

from __future__ import annotations

from pydantic import BaseModel

from maple_agent.experience.models import ExperienceRecord


class ExperienceScore(BaseModel):
    """单条经验的匹配评分。"""

    experience_id: str
    score: float
    reason: str


class ExperienceEvaluator:
    """评估历史经验与当前情境的相似度(只读)。"""

    def evaluate(
        self,
        record: ExperienceRecord,
        *,
        map_name: str = "",
        goal: str = "",
        action: str = "",
    ) -> ExperienceScore:
        score = 0.0
        reasons: list[str] = []
        if map_name and record.context_snapshot.get("map_name") == map_name:
            score += 0.4
            reasons.append("地图匹配")
        if goal and record.goal == goal:
            score += 0.3
            reasons.append("目标匹配")
        if action and record.action.upper() == action.upper():
            score += 0.2
            reasons.append("动作匹配")
        if record.success:
            score += 0.1
            reasons.append("成功经验")
        return ExperienceScore(
            experience_id=record.experience_id,
            score=round(min(score, 1.0), 4),
            reason=",".join(reasons) or "无匹配",
        )
