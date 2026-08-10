"""Goal Memory 数据模型(Phase 7-C,目标级经验,非训练)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.task_planning.models import TaskGraph


class GoalExperienceRecord(BaseModel):
    """目标级经验记录。"""

    experience_id: str
    goal_type: str = ""
    goal_description: str = ""
    successful_path: list[str] = Field(default_factory=list)
    failed_points: list[str] = Field(default_factory=list)
    task_pattern: list[str] = Field(default_factory=list)
    duration_estimate: int = 0
    success: bool = False
    confidence: float = Field(default=0.0, ge=0, le=1)
    trace_id: str = ""


class GoalMatchResult(BaseModel):
    """目标匹配结果。"""

    experience_id: str
    score: float = Field(default=0.0, ge=0, le=1)
    reasons: list[str] = Field(default_factory=list)


class OptimizedTaskGraph(BaseModel):
    """优化后的任务图(规划参考,不触碰执行器)。"""

    graph: TaskGraph | None = None
    removed_tasks: list[str] = Field(default_factory=list)
    reordered: bool = False
    recovery_hints: list[str] = Field(default_factory=list)
    summary: str = ""
