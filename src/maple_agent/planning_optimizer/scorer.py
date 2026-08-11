"""PlanningScorer:规划质量评分(0-1)。"""

from __future__ import annotations

from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.planning_optimizer.models import (
    OptimizedPlanningReference,
    PlanningAnalysis,
    PlanningQualityScore,
)


class PlanningScorer:
    """PlanningScore = 0.3*Dependency + 0.25*Experience + 0.25*Risk + 0.2*Success。"""

    def score(
        self,
        *,
        analysis: PlanningAnalysis,
        experience: GoalExperienceRecord | None = None,
        optimized: OptimizedPlanningReference | None = None,
    ) -> PlanningQualityScore:
        dependency_score = 1.0 if analysis.dag_complete else 0.4
        experience_alignment = analysis.experience_match
        risk_score = round(1.0 - analysis.failure_probability, 4)
        if experience is None:
            historical_success = 0.3
        else:
            historical_success = 1.0 if experience.success else 0.4
        planning_score = round(
            0.3 * dependency_score
            + 0.25 * experience_alignment
            + 0.25 * risk_score
            + 0.2 * historical_success,
            4,
        )
        estimated_success_probability = round(
            1.0 - analysis.failure_probability,
            4,
        )
        recommendations: list[str] = []
        if optimized is not None and optimized.removed_tasks:
            recommendations.append(
                "已移除冗余/失败任务: " + ", ".join(optimized.removed_tasks)
            )
        if optimized is not None and optimized.added_recovery_points:
            recommendations.append(
                "已增加恢复点: " + ", ".join(optimized.added_recovery_points)
            )
        if experience_alignment < 0.5:
            recommendations.append("经验匹配度低,建议补充目标级经验")
        if not analysis.dag_complete:
            recommendations.append("修复任务图依赖关系")
        return PlanningQualityScore(
            planning_score=planning_score,
            dependency_score=round(dependency_score, 4),
            risk_score=risk_score,
            experience_alignment=experience_alignment,
            estimated_success_probability=estimated_success_probability,
            issues=list(analysis.issues),
            recommendations=recommendations,
        )
