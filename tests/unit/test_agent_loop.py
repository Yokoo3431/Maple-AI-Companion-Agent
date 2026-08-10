"""Agent Loop 单测:完整闭环 / 失败 / 阻断 / 沙箱 / 反思 / 评估 / Replay / 校验。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.action_plan.planner import ActionPlanner
from maple_agent.agent_loop import (
    AgentLoopContext,
    AgentLoopOrchestrator,
    AgentLoopStage,
    AgentLoopStatus,
    AgentLoopTrace,
    AgentLoopValidator,
)
from maple_agent.confirmation.gate import HumanConfirmationGate
from maple_agent.confirmation.manager import ConfirmationManager
from maple_agent.decision.engine import DecisionEngine
from maple_agent.evaluation.benchmark import EvaluationBenchmark
from maple_agent.events import EventBus
from maple_agent.executor_sandbox.models import SandboxExecutionResult, SandboxExecutionStatus
from maple_agent.executor_sandbox.sandbox import LimitedExecutorSandbox
from maple_agent.observation import ObservationAdapter, ObservationCollector
from maple_agent.providers import MockKnowledgeProvider, MockOCRProvider
from maple_agent.reflection.engine import ReflectionEngine
from maple_agent.runtime import RuntimeManager
from maple_agent.vision_eval import RiskLevel, VisionEvaluationResult, VisionEvaluator
from maple_agent.webui.app import create_app


class HighRiskVision:
    """返回 HIGH 风险的视觉评估(用于阻断测试)。"""

    def evaluate(self, **kwargs) -> VisionEvaluationResult:
        return VisionEvaluationResult(
            evaluation_id="e-high",
            frame_id="f-high",
            overall_score=0.2,
            ocr_score=0.1,
            entity_score=0.1,
            consistency_score=0.3,
            confidence_score=0.1,
            risk_level=RiskLevel.HIGH,
        )


def _knowledge() -> MockKnowledgeProvider:
    provider = MockKnowledgeProvider()
    provider.initialize()
    provider.load_dataset()
    return provider


def _build_orchestrator(
    tmp_path,
    *,
    vision=None,
    ocr_raise: bool = False,
) -> AgentLoopOrchestrator:
    ocr = MockOCRProvider(
        text="射手村",
        confidence=0.95,
        raise_on_call=ocr_raise,
    )
    ocr.initialize()
    adapter = ObservationAdapter(ocr=ocr, sessions_dir=tmp_path)
    knowledge = _knowledge()
    collector = ObservationCollector(
        adapter,
        knowledge=knowledge,
        sessions_dir=tmp_path,
    )
    vision_evaluator = vision or VisionEvaluator(
        knowledge=knowledge,
        sessions_dir=tmp_path,
    )
    return AgentLoopOrchestrator(
        observation_collector=collector,
        vision_evaluator=vision_evaluator,
        decision_engine=DecisionEngine(sessions_dir=tmp_path),
        action_planner=ActionPlanner(sessions_dir=tmp_path),
        confirmation_manager=ConfirmationManager(sessions_dir=tmp_path),
        confirmation_gate=HumanConfirmationGate(),
        sandbox=LimitedExecutorSandbox(sessions_dir=tmp_path),
        reflection_engine=ReflectionEngine(sessions_dir=tmp_path),
        evaluation_benchmark=EvaluationBenchmark(sessions_dir=tmp_path),
        sessions_dir=tmp_path,
        knowledge=knowledge,
    )


def test_full_successful_loop(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-full",
    )
    assert context.status is AgentLoopStatus.COMPLETED
    assert context.observation_state is not None
    assert context.observation_state.map_name == "射手村"
    assert context.vision_result is not None
    assert context.decision_result is not None
    assert context.decision_result.selected_option is not None
    assert context.action_plan is not None
    assert context.confirmation_result is not None
    assert context.confirmation_result.status.value == "APPROVED"
    assert context.permission_token is not None
    assert context.permission_token.approved is True
    assert context.sandbox_result is not None
    assert context.sandbox_result.status is SandboxExecutionStatus.COMPLETED
    assert context.sandbox_result.mode == "MOCK_ONLY"
    assert context.reflection_result is not None
    assert context.evaluation_result is not None
    assert orchestrator.last_validation is not None
    assert orchestrator.last_validation.valid is True


def test_observation_failure(tmp_path):
    orchestrator = _build_orchestrator(tmp_path, ocr_raise=True)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-obs-fail",
    )
    assert context.status is AgentLoopStatus.FAILED
    assert any(
        stage.stage == "error" for stage in orchestrator.last_trace.stages
    )


def test_vision_high_risk_blocked(tmp_path):
    orchestrator = _build_orchestrator(tmp_path, vision=HighRiskVision())
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-high-risk",
    )
    assert context.status is AgentLoopStatus.BLOCKED
    assert context.sandbox_result is None
    assert context.confirmation_result is None


def test_confirmation_reject_blocked(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=False,
        trace_id="trace-reject",
    )
    assert context.status is AgentLoopStatus.BLOCKED
    assert context.permission_token is None
    assert context.sandbox_result is None


def test_missing_token_blocked(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=False,
        trace_id="trace-no-token",
    )
    assert context.status is AgentLoopStatus.BLOCKED
    assert context.permission_token is None


def test_sandbox_completion(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-sandbox",
    )
    assert context.sandbox_result is not None
    assert context.sandbox_result.success is True
    assert context.sandbox_result.mode == "MOCK_ONLY"
    assert context.sandbox_result.audit["permission"] == "verified"


def test_reflection_output(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-reflect",
    )
    assert context.reflection_result is not None
    assert context.reflection_result.success is True
    assert context.reflection_result.next_action == "continue"


def test_evaluation_output(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-eval",
    )
    assert context.evaluation_result is not None
    assert context.evaluation_result.trace_id == "trace-eval"
    assert context.evaluation_result.overall_score > 0


def test_replay_generation(tmp_path):
    orchestrator = _build_orchestrator(tmp_path)
    orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "agent_loop_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["trace_id"] == "trace-replay"
    stage_names = [stage["stage"] for stage in replay["stages"]]
    assert "observation" in stage_names
    assert "decision" in stage_names
    assert "confirmation" in stage_names
    assert "sandbox" in stage_names
    assert "reflection" in stage_names
    assert "evaluation" in stage_names
    assert replay["final_status"] == "COMPLETED"


def test_invalid_stage_transition():
    trace = AgentLoopTrace(
        trace_id="trace-invalid",
        stages=[
            AgentLoopStage(stage="sandbox", status="MOCK_ONLY"),
            AgentLoopStage(stage="observation", status="completed"),
        ],
        final_status="COMPLETED",
    )
    context = AgentLoopContext(
        trace_id="trace-invalid",
        status=AgentLoopStatus.COMPLETED,
        sandbox_result=SandboxExecutionResult(
            execution_id="e",
            status=SandboxExecutionStatus.COMPLETED,
            success=True,
            mode="MOCK_ONLY",
        ),
    )
    result = AgentLoopValidator().validate(context, trace)
    assert result.valid is False
    assert any("阶段顺序非法" in issue for issue in result.issues)
    assert any("禁止跳过 Human Confirmation" in issue for issue in result.issues)


def test_validator_skipped_confirmation():
    context = AgentLoopContext(
        trace_id="trace-skip",
        status=AgentLoopStatus.COMPLETED,
        sandbox_result=SandboxExecutionResult(
            execution_id="e",
            status=SandboxExecutionStatus.COMPLETED,
            success=True,
            mode="MOCK_ONLY",
        ),
    )
    result = AgentLoopValidator().validate(context)
    assert result.valid is False
    assert any("禁止跳过 Human Confirmation" in issue for issue in result.issues)
    assert any("Sandbox 缺少 PermissionToken" in issue for issue in result.issues)


def test_webui_agent_loop_endpoint(tmp_path):
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    orchestrator = _build_orchestrator(tmp_path)
    context = orchestrator.run(
        image_bytes=b"mock-image",
        auto_approve=True,
        trace_id="trace-webui",
    )
    payload = {
        "context": context.model_dump(mode="json"),
        "trace": orchestrator.last_trace.model_dump(mode="json"),
        "validation": orchestrator.last_validation.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, cognitive_loop=payload)
    with TestClient(app) as client:
        resp = client.get("/api/agent-loop/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["context"]["status"] == "COMPLETED"
    assert data["trace"]["final_status"] == "COMPLETED"
    assert data["validation"]["valid"] is True


def test_webui_agent_loop_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/agent-loop/state")
    assert resp.json()["enabled"] is False
