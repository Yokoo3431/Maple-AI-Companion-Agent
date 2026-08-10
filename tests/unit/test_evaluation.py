"""Agent Evaluation 单测:组件评分 / 缺陷识别 / Benchmark / Replay / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.evaluation import (
    DecisionEvaluator,
    EvaluationBenchmark,
    ExecutionEvaluator,
    MemoryEvaluator,
    PlanEvaluator,
    ReflectionEvaluator,
    overall_score,
)
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _decision_trace() -> dict:
    return {
        "trace_id": "trace-success",
        "candidate_decisions": [
            {
                "option": {"decision_id": "d1", "action": "TALK", "risk": 0.2},
                "score": 0.8,
            },
            {
                "option": {"decision_id": "d2", "action": "DEFEAT", "risk": 0.5},
                "score": 0.6,
            },
        ],
        "selected": {"decision_id": "d1", "action": "TALK", "risk": 0.2},
        "selected_score": 0.8,
        "experience": {
            "retrieved": [
                {"experience_id": "e1", "action": "TALK", "success": True}
            ]
        },
    }


def _plan_trace() -> dict:
    return {
        "validation_result": {"valid": True, "errors": []},
        "generated_steps": [
            {"step_id": "s1"},
            {"step_id": "s2"},
            {"step_id": "s3"},
        ],
        "prerequisites": ["地图: 射手村", "知识: best=射手村"],
    }


def _execution_trace(
    *,
    statuses: list[str] | None = None,
    invalid_transition: bool = False,
) -> dict:
    statuses = statuses or ["COMPLETED", "COMPLETED", "COMPLETED"]
    steps = []
    for index, status in enumerate(statuses):
        transitions = [
            {"from": "CREATED", "to": "VALIDATING"},
            {"from": "VALIDATING", "to": "READY"},
            {"from": "READY", "to": "RUNNING"},
            {"from": "RUNNING", "to": "WAITING_OBSERVATION"},
            {"from": "WAITING_OBSERVATION", "to": status},
        ]
        if invalid_transition:
            transitions.append({"from": "FAILED", "to": "RUNNING"})
        steps.append(
            {
                "status": status,
                "transitions": transitions,
                "task": {"retry_count": 0},
            }
        )
    final_state = (
        "COMPLETED"
        if all(status == "COMPLETED" for status in statuses)
        else "FAILED"
    )
    return {"steps": steps, "state": {"status": final_state}}


def _reflection_trace(
    *,
    success: bool = True,
    trigger: str = "NO_ACTION",
    next_plan: str = "continue",
) -> dict:
    return {
        "analysis": {
            "success": success,
            "failure_type": None if success else "EXECUTION_FAILED",
            "failure_reason": "" if success else "执行失败",
            "confidence": 0.875,
        },
        "trigger": trigger,
        "next_plan": next_plan,
    }


def test_success_trace_scores():
    decision = DecisionEvaluator().evaluate(_decision_trace())
    plan = PlanEvaluator().evaluate(_plan_trace())
    execution = ExecutionEvaluator().evaluate(_execution_trace())
    reflection = ReflectionEvaluator().evaluate(_reflection_trace())
    memory = MemoryEvaluator().evaluate(_decision_trace())
    assert decision.score >= 0.8
    assert plan.score >= 0.8
    assert execution.score >= 0.8
    assert reflection.score >= 0.8
    assert memory.score >= 0.7


def test_failure_trace_scores():
    execution = ExecutionEvaluator().evaluate(
        _execution_trace(statuses=["FAILED", "FAILED", "FAILED"])
    )
    reflection = ReflectionEvaluator().evaluate(
        _reflection_trace(
            success=False,
            trigger="REPLAN_REQUIRED",
            next_plan="replan",
        )
    )
    assert execution.score < 0.5
    assert any("失败/阻断步骤" in issue for issue in execution.issues)
    assert reflection.score >= 0.8  # 失败但反思反应合理


def test_decision_error_detection():
    trace = _decision_trace()
    trace["selected"] = {"decision_id": "d2", "action": "DEFEAT", "risk": 0.5}
    result = DecisionEvaluator().evaluate(trace)
    assert any("未选择最高评分候选" in issue for issue in result.issues)


def test_plan_defect_detection():
    trace = _plan_trace()
    trace["prerequisites"] = ["地图: 射手村", "缺失: 知识状态"]
    result = PlanEvaluator().evaluate(trace)
    assert any("不可满足前置" in issue for issue in result.issues)


def test_execution_invalid_transition_detection():
    result = ExecutionEvaluator().evaluate(
        _execution_trace(invalid_transition=True)
    )
    assert any("非法状态转换" in issue for issue in result.issues)


def test_reflection_mismatch_detection():
    result = ReflectionEvaluator().evaluate(
        _reflection_trace(success=True, trigger="REPLAN_REQUIRED")
    )
    assert any("反思判定不一致" in issue for issue in result.issues)


def test_experience_hit_evaluation():
    hit = MemoryEvaluator().evaluate(_decision_trace())
    assert hit.score >= 0.7
    no_hit = MemoryEvaluator().evaluate({"selected": {}})
    assert any("未命中历史经验" in issue for issue in no_hit.issues)


def test_overall_formula():
    score = overall_score(0.8, 0.9, 1.0, 0.85, 0.7)
    assert score == 0.855


def _write_trace_files(tmp_path, trace_id: str = "trace-bench") -> None:
    directory = tmp_path / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payloads = {
        "decision_trace.json": _decision_trace(),
        "action_plan_trace.json": _plan_trace(),
        "execution_orchestration.json": _execution_trace(),
        "reflection_trace.json": _reflection_trace(),
    }
    for name, payload in payloads.items():
        (directory / name).write_text(
            json.dumps(payload, ensure_ascii=False),
            encoding="utf-8",
        )


def test_benchmark_output_and_replay(tmp_path):
    _write_trace_files(tmp_path)
    benchmark = EvaluationBenchmark(sessions_dir=tmp_path)
    result = benchmark.run("trace-bench")
    assert result.trace_id == "trace-bench"
    assert result.overall_score > 0
    report = json.loads(
        (tmp_path / "trace-bench" / "evaluation_report.json").read_text(
            encoding="utf-8"
        )
    )
    assert report["trace_id"] == "trace-bench"
    assert report["metrics"]["decision"] == result.decision_score
    assert report["metrics"]["planning"] == result.planning_score
    assert report["metrics"]["execution"] == result.execution_score
    assert report["metrics"]["reflection"] == result.reflection_score
    assert report["metrics"]["experience"] == result.memory_score
    assert report["overall"] == result.overall_score
    assert isinstance(report["issues"], list)
    assert isinstance(report["recommendations"], list)


def test_benchmark_aggregates_metrics(tmp_path):
    _write_trace_files(tmp_path, "trace-1")
    _write_trace_files(tmp_path, "trace-2")
    benchmark = EvaluationBenchmark(sessions_dir=tmp_path)
    metrics = benchmark.benchmark()
    assert benchmark.last_trace_count == 2
    assert metrics.overall_score > 0
    assert metrics.decision_accuracy > 0
    assert metrics.execution_success_rate > 0


def test_webui_evaluation_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    benchmark = EvaluationBenchmark()
    metrics = benchmark.benchmark()
    payload = {
        "trace_count": benchmark.last_trace_count,
        "metrics": metrics.model_dump(mode="json"),
        "last_result": (
            benchmark.last_result.model_dump(mode="json")
            if benchmark.last_result is not None
            else None
        ),
        "report": "",
    }
    app = create_app(runtime=runtime, bus=bus, evaluation=payload)
    with TestClient(app) as client:
        resp = client.get("/api/evaluation/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert "trace_count" in data
    assert "metrics" in data


def test_webui_evaluation_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/evaluation/state")
    assert resp.json()["enabled"] is False
