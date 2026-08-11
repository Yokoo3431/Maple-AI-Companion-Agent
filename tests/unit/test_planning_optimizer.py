"""Adaptive Planning Optimization 单测。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.planning_optimizer import (
    AdaptivePlannerOptimizer,
    OptimizedPlanningReference,
    PlanningOptimizationValidator,
    PlanningScorer,
    TaskGraphAnalyzer,
    save_planning_optimization_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import (
    LongHorizonGoal,
    Milestone,
    TaskDecomposer,
    TaskGraph,
)
from maple_agent.webui.app import create_app


def _goal() -> LongHorizonGoal:
    return LongHorizonGoal(
        goal_id="goal-1",
        description="完成新手任务链",
        priority=10,
        success_condition="提交任务并验证完成",
        milestones=[
            Milestone(
                milestone_id="ms-1",
                title="找到 NPC",
                order=0,
                task_ids=["task-1"],
            ),
            Milestone(
                milestone_id="ms-2",
                title="接受任务",
                order=1,
                task_ids=["task-2"],
            ),
            Milestone(
                milestone_id="ms-3",
                title="收集材料",
                order=2,
                task_ids=["task-3", "task-4"],
            ),
        ],
    )


def _graph():
    return TaskDecomposer().decompose(_goal())


def _experience() -> GoalExperienceRecord:
    return GoalExperienceRecord(
        experience_id="gxp-1",
        goal_type="QUEST",
        goal_description="完成新手任务链",
        successful_path=["task-1", "task-2", "task-3", "task-4"],
        failed_points=[],
        task_pattern=["task-1", "task-2", "task-3", "task-4"],
        duration_estimate=600,
        success=True,
        confidence=0.9,
    )


def test_graph_analysis():
    analysis = TaskGraphAnalyzer().analyze(_graph())
    assert analysis.goal_id == "goal-1"
    assert analysis.dag_complete is True
    assert analysis.task_count == 4
    assert analysis.redundant_tasks == []
    assert len(analysis.risk_nodes) == 4
    assert analysis.failure_probability == 0.5
    assert analysis.issues == []


def test_quality_scoring_formula():
    analysis = TaskGraphAnalyzer().analyze(_graph())
    score = PlanningScorer().score(
        analysis=analysis,
        experience=_experience(),
    )
    # 0.3*1.0 + 0.25*0 + 0.25*0.5 + 0.2*1.0 = 0.625
    assert score.planning_score == 0.625
    assert score.dependency_score == 1.0
    assert score.risk_score == 0.5
    assert score.experience_alignment == 0.0
    assert score.estimated_success_probability == 0.5


def test_optimization_generation():
    optimizer = AdaptivePlannerOptimizer()
    reference, score = optimizer.optimize(
        graph=_graph(),
        experience=_experience(),
    )
    assert reference.optimized_order == [
        "task-1",
        "task-2",
        "task-3",
        "task-4",
    ]
    assert reference.removed_tasks == []
    assert len(reference.added_recovery_points) == 4
    assert "recovery:task-1" in reference.added_recovery_points
    assert reference.risk_adjustments
    assert any(
        "按历史成功路径" in reason for reason in reference.reasoning
    )
    assert score.planning_score > 0


def test_risk_detection():
    analysis = TaskGraphAnalyzer().analyze(_graph())
    assert analysis.risk_nodes
    assert analysis.failure_probability >= 0.5
    # 无任务图 -> 失败概率与空图问题
    empty = TaskGraphAnalyzer().analyze(
        TaskGraph(goal_id="empty", milestones=[], tasks=[])
    )
    assert empty.dag_complete is False
    assert any("任务图为空" in issue for issue in empty.issues)


def test_experience_alignment():
    optimizer = AdaptivePlannerOptimizer()
    optimizer.optimize(
        graph=_graph(),
        experience=_experience(),
    )
    assert optimizer.last_analysis is not None
    assert optimizer.last_analysis.experience_match == 1.0


def test_removed_failed_tasks():
    optimizer = AdaptivePlannerOptimizer()
    failed_exp = _experience().model_copy(
        update={
            "experience_id": "gxp-2",
            "success": False,
            "failed_points": ["task-3"],
        }
    )
    reference, _ = optimizer.optimize(
        graph=_graph(),
        experience=failed_exp,
    )
    assert "task-3" in reference.removed_tasks
    assert "task-3" not in reference.optimized_order


def test_optimization_validator():
    validator = PlanningOptimizationValidator()
    valid_ref = OptimizedPlanningReference(
        goal_id="goal-1",
        optimized_order=["task-1", "task-2", "task-4"],
        removed_tasks=["task-3"],
    )
    assert validator.validate(reference=valid_ref, graph=_graph()).valid is True
    invalid_ref = OptimizedPlanningReference(
        goal_id="goal-1",
        optimized_order=["task-1", "task-2"],
        removed_tasks=["task-3"],
    )
    result = validator.validate(reference=invalid_ref, graph=_graph())
    assert result.valid is False
    assert any("不完整" in issue for issue in result.issues)


def test_replay_generation(tmp_path):
    optimizer = AdaptivePlannerOptimizer()
    graph = _graph()
    analysis = TaskGraphAnalyzer().analyze(graph)
    reference, score = optimizer.optimize(
        graph=graph,
        experience=_experience(),
        analysis=analysis,
    )
    save_planning_optimization_trace(
        tmp_path,
        "trace-replay",
        goal_id="goal-1",
        original_plan=graph.model_dump(mode="json"),
        analysis=optimizer.last_analysis,
        optimized_plan=reference,
        score=score,
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "planning_optimization_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["goal_id"] == "goal-1"
    assert replay["original_plan"]["goal_id"] == "goal-1"
    assert "analysis" in replay
    assert replay["optimized_plan"]["optimized_order"]
    assert replay["score"] == score.planning_score
    assert isinstance(replay["recommendations"], list)


def test_context_integration():
    optimizer = AdaptivePlannerOptimizer()
    reference, score = optimizer.optimize(
        graph=_graph(),
        experience=_experience(),
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        planning_quality=score,
        optimization_reference=reference,
    )
    assert context.planning_quality is not None
    assert context.planning_quality.planning_score > 0
    assert context.optimization_reference is not None
    assert context.optimization_reference.optimized_order


def test_webui_planning_optimizer_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    optimizer = AdaptivePlannerOptimizer()
    graph = _graph()
    analysis = TaskGraphAnalyzer().analyze(graph)
    reference, score = optimizer.optimize(
        graph=graph,
        experience=_experience(),
        analysis=analysis,
    )
    payload = {
        "goal_id": "goal-1",
        "analysis": optimizer.last_analysis.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
        "optimized": reference.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, planning_optimizer=payload)
    with TestClient(app) as client:
        resp = client.get("/api/planning-optimizer/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal_id"] == "goal-1"
    assert data["score"]["planning_score"] > 0
    assert data["optimized"]["optimized_order"]


def test_webui_planning_optimizer_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/planning-optimizer/state")
    assert resp.json()["enabled"] is False
