"""Long Horizon Task Planning 数据模型(Phase 7-B,只读规划)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Milestone(BaseModel):
    """目标里程碑。"""

    milestone_id: str
    title: str = ""
    order: int = 0
    task_ids: list[str] = Field(default_factory=list)


class LongHorizonGoal(BaseModel):
    """长程目标(多阶段)。"""

    goal_id: str
    description: str = ""
    priority: int = Field(default=1, ge=1, le=100)
    constraints: list[str] = Field(default_factory=list)
    success_condition: str = ""
    milestones: list[Milestone] = Field(default_factory=list)
    current_stage: int = 0


class TaskNode(BaseModel):
    """任务节点(拆解后的最小执行单元)。"""

    task_id: str
    milestone_index: int = 0
    objective: str = ""
    prerequisite: str = ""
    expected_result: str = ""
    failure_condition: str = ""
    action: str = ""
    target: str = ""


class TaskGraph(BaseModel):
    """任务图(Goal -> Milestone[] -> TaskNode[])。"""

    goal_id: str = ""
    milestones: list[Milestone] = Field(default_factory=list)
    tasks: list[TaskNode] = Field(default_factory=list)


class TaskExecutionState(BaseModel):
    """长程执行状态(支持中断恢复)。"""

    goal_id: str = ""
    current_goal: str = ""
    completed_tasks: list[str] = Field(default_factory=list)
    pending_tasks: list[str] = Field(default_factory=list)
    failed_tasks: list[str] = Field(default_factory=list)
    retry_count: int = 0
    next_action: str = ""
