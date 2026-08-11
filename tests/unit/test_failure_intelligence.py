"""Failure Intelligence 单测:提取 / 匹配 / 根因 / 预防 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.failure_intelligence import (
    FailureAnalyzer,
    FailureExtractor,
    FailurePatternMatcher,
    FailurePatternRecord,
    FailurePredictor,
    save_failure_intelligence_trace,
)
from maple_agent.reflection.models import FailureType, ReflectionResult
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import (
    LongHorizonGoal,
    Milestone,
    TaskDecomposer,
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


def _reflection(
    *,
    success: bool = False,
    failure_type: FailureType = FailureType.EXECUTION_FAILED,
) -> ReflectionResult:
    return ReflectionResult(
        reflection_id="refl-1",
        execution_id="exec-1",
        success=success,
        failure_type=None if success else failure_type,
        failure_reason="" if success else "前置条件未满足",
        confidence=0.5,
        next_action="continue" if success else "replan",
        trace_id="trace-fail",
    )


def _pattern(
    pattern_id: str = "fp-1",
    *,
    failure_type: str = "EXECUTION_FAILED",
    affected: list[str] | None = None,
    success_rate: float = 0.3,
) -> FailurePatternRecord:
    return FailurePatternRecord(
        pattern_id=pattern_id,
        failure_type=failure_type,
        trigger_conditions=["confidence=0.5"],
        context_snapshot={
            "confidence": 0.5,
            "failed_task": "task-3",
        },
        affected_tasks=affected or ["task-3"],
        root_cause="前置条件未满足",
        resolution_strategy="重试并检查前置条件",
        success_rate=success_rate,
        confidence=0.7,
        trace_id="trace-fail",
    )


def test_failure_extraction():
    extractor = FailureExtractor()
    pattern = extractor.extract(
        reflection=_reflection(),
        execution_trace={
            "steps": [{"status": "FAILED", "task": {"step_id": "task-3"}}]
        },
        task_planning_trace={"current_task": "task-3", "progress": 0.4},
    )
    assert pattern is not None
    assert pattern.failure_type == "EXECUTION_FAILED"
    assert pattern.affected_tasks == ["task-3"]
    assert pattern.root_cause == "前置条件未满足"
    assert pattern.resolution_strategy == "重试并检查前置条件"
    assert pattern.trigger_conditions
    assert pattern.context_snapshot["failed_task"] == "task-3"


def test_success_no_extraction():
    pattern = FailureExtractor().extract(
        reflection=_reflection(success=True),
    )
    assert pattern is None


def test_pattern_matching_high_score():
    matcher = FailurePatternMatcher()
    result = matcher.score(
        pattern=_pattern(),
        current_task_graph=_graph(),
        current_context={"confidence": 0.5, "failed_task": "task-3"},
        failure_type="EXECUTION_FAILED",
    )
    assert result.score > 0.7
    assert "失败类型匹配" in result.reasons


def test_pattern_matching_low_score():
    matcher = FailurePatternMatcher()
    unrelated = FailurePatternRecord(
        pattern_id="fp-x",
        failure_type="KNOWLEDGE_ERROR",
        context_snapshot={"confidence": 0.9, "failed_task": "task-x"},
        affected_tasks=["task-x"],
        root_cause="知识错误",
        resolution_strategy="刷新知识库",
        success_rate=0.5,
        confidence=0.3,
    )
    result = matcher.score(
        pattern=unrelated,
        current_task_graph=_graph(),
        current_context={"confidence": 0.5, "failed_task": "task-3"},
        failure_type="EXECUTION_FAILED",
    )
    assert result.score < 0.5


def test_root_cause_analysis():
    analyzer = FailureAnalyzer()
    analysis = analyzer.analyze(
        pattern=_pattern(),
        match_score=0.8,
    )
    assert analysis.root_cause == "前置条件未满足"
    assert analysis.risk_level == "HIGH"
    assert analysis.prevention_strategy == "执行前验证前置条件并启用重试"
    assert "task-3" in analysis.recommended_adjustment


def test_prevention_generation():
    predictor = FailurePredictor()
    reference = predictor.build_prevention_reference(
        task_graph=_graph(),
        patterns=[_pattern()],
    )
    assert "task-3" in reference.avoid_tasks
    assert reference.risk_warnings
    assert any("失败概率" in warning for warning in reference.risk_warnings)
    assert reference.prevention_notes
    assert reference.summary


def test_failure_prediction():
    predictor = FailurePredictor()
    probabilities = predictor.predict(
        task_graph=_graph(),
        patterns=[_pattern()],
    )
    assert probabilities["task-3"] == 0.7
    assert probabilities["task-1"] == 0.1


def test_replay_generation(tmp_path):
    extractor = FailureExtractor()
    pattern = extractor.extract(
        reflection=_reflection(),
        task_planning_trace={"current_task": "task-3", "progress": 0.4},
    )
    analysis = FailureAnalyzer().analyze(pattern=pattern, match_score=0.8)
    reference = FailurePredictor().build_prevention_reference(
        task_graph=_graph(),
        patterns=[pattern],
        analysis=analysis,
    )
    save_failure_intelligence_trace(
        tmp_path,
        "trace-replay",
        source_trace="trace-fail",
        failure_pattern=pattern,
        analysis=analysis,
        prevention_reference=reference,
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "failure_intelligence_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["source_trace"] == "trace-fail"
    assert replay["failure_pattern"]["failure_type"] == "EXECUTION_FAILED"
    assert replay["analysis"]["risk_level"] == "HIGH"
    assert "prevention_reference" in replay
    assert "recovery:task-3" in replay["prevention_reference"][
        "recovery_points"
    ]


def test_context_integration():
    pattern = _pattern()
    reference = FailurePredictor().build_prevention_reference(
        task_graph=_graph(),
        patterns=[pattern],
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        failure_patterns=[pattern],
        failure_prevention_reference=reference,
    )
    assert len(context.failure_patterns) == 1
    assert context.failure_patterns[0].failure_type == "EXECUTION_FAILED"
    assert context.failure_prevention_reference is not None
    assert context.failure_prevention_reference.summary


def test_webui_failure_intelligence_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    pattern = _pattern()
    analysis = FailureAnalyzer().analyze(pattern=pattern, match_score=0.8)
    reference = FailurePredictor().build_prevention_reference(
        task_graph=_graph(),
        patterns=[pattern],
        analysis=analysis,
    )
    payload = {
        "failure_count": 1,
        "top_pattern": pattern.model_dump(mode="json"),
        "analysis": analysis.model_dump(mode="json"),
        "prevention": reference.model_dump(mode="json"),
    }
    app = create_app(
        runtime=runtime,
        bus=bus,
        failure_intelligence=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/failure-intelligence/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["failure_count"] == 1
    assert data["top_pattern"]["failure_type"] == "EXECUTION_FAILED"
    assert data["analysis"]["risk_level"] == "HIGH"
    assert data["prevention"]["avoid_tasks"] == ["task-3"]


def test_webui_failure_intelligence_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/failure-intelligence/state")
    assert resp.json()["enabled"] is False
