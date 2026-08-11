"""Human Alignment 单测:偏好记忆 / 反馈处理 / 对齐评分 / replay / validator / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.decision_reference.models import (
    DecisionReference,
    ReferenceOption,
)
from maple_agent.events import EventBus
from maple_agent.human_alignment import (
    FeedbackAction,
    FeedbackProcessor,
    HumanAlignmentAligner,
    HumanAlignmentValidator,
    HumanFeedback,
    PreferenceMemory,
    save_human_alignment_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _decision_reference() -> DecisionReference:
    return DecisionReference(
        recommended_options=[
            ReferenceOption(
                option_id="opt-1",
                action="TALK",
                target="NPC",
                recommendation="recommended",
                confidence=0.9,
                reason="NPC 交互",
            ),
            ReferenceOption(
                option_id="opt-2",
                action="OBSERVE",
                target="window",
                recommendation="recommended",
                confidence=0.8,
                reason="观察",
            ),
        ],
        alternative_options=[],
        risk_level="LOW",
        confidence=0.9,
        reasoning=["test"],
        environment_alignment=0.9,
        planning_alignment=0.8,
    )


def _feedback(
    option_id: str = "opt-1",
    action: FeedbackAction = FeedbackAction.ACCEPT,
) -> HumanFeedback:
    return HumanFeedback(
        feedback_id="fb-1",
        option_id=option_id,
        action=action,
        comment="user feedback",
    )


def test_preference_memory():
    memory = PreferenceMemory()
    memory.record(option_id="opt-1", action="accept", reason="ok")
    memory.record(option_id="opt-2", action="reject", reason="no")
    assert memory.count() == 2
    assert memory.accepted_option_ids() == ["opt-1"]
    assert memory.rejected_option_ids() == ["opt-2"]
    assert memory.approval_rate() == 0.5


def test_feedback_processing():
    processor = FeedbackProcessor()
    update = processor.process(feedback=_feedback())
    assert update.applied is True
    assert update.updates == ["接受选项 opt-1"]
    assert processor.memory.count() == 1


def test_feedback_reject():
    processor = FeedbackProcessor()
    update = processor.process(
        feedback=_feedback(action=FeedbackAction.REJECT),
    )
    assert update.updates == ["拒绝选项 opt-1"]
    assert processor.memory.rejected_option_ids() == ["opt-1"]


def test_alignment_scoring():
    aligner = HumanAlignmentAligner()
    reference = aligner.align(
        decision_reference=_decision_reference(),
        feedback=_feedback(),
    )
    # 0.4*0.5 + 0.3*1.0 + 0.2*0.9 + 0.1*1.0 = 0.78
    assert reference.alignment_score == 0.78
    assert aligner.last_score is not None
    assert aligner.last_score.preference_match == 0.5
    assert aligner.last_score.historical_approval == 1.0
    assert reference.preferred_options


def test_alignment_reject_removes_option():
    aligner = HumanAlignmentAligner()
    reference = aligner.align(
        decision_reference=_decision_reference(),
        feedback=_feedback(action=FeedbackAction.REJECT),
    )
    assert "opt-1" in reference.rejected_options
    assert all(
        option.option_id != "opt-1"
        for option in reference.preferred_options
    )
    assert any("移除" in adjustment for adjustment in reference.adjustments)


def test_replay_generation(tmp_path):
    aligner = HumanAlignmentAligner()
    decision_reference = _decision_reference()
    feedback = _feedback()
    aligner.align(
        decision_reference=decision_reference,
        feedback=feedback,
    )
    save_human_alignment_trace(
        tmp_path,
        "trace-replay",
        decision_reference=decision_reference,
        feedback=feedback,
        alignment=aligner.last_score,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "human_alignment_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["decision_reference"]["recommended_options"]
    assert replay["feedback"]["option_id"] == "opt-1"
    assert replay["alignment"]["alignment_score"] == 0.78


def test_validator():
    aligner = HumanAlignmentAligner()
    aligned = aligner.align(
        decision_reference=_decision_reference(),
        feedback=_feedback(),
    )
    result = HumanAlignmentValidator().validate(
        reference=aligned,
        alignment=aligner.last_score,
    )
    assert result.valid is True


def test_context_integration():
    aligner = HumanAlignmentAligner()
    aligned = aligner.align(
        decision_reference=_decision_reference(),
        feedback=_feedback(),
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        human_alignment_reference=aligned,
    )
    assert context.human_alignment_reference is not None
    assert context.human_alignment_reference.alignment_score == 0.78
    assert context.human_alignment_reference.preferred_options


def test_webui_human_alignment_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    aligner = HumanAlignmentAligner()
    decision_reference = _decision_reference()
    feedback = _feedback()
    aligned = aligner.align(
        decision_reference=decision_reference,
        feedback=feedback,
    )
    payload = {
        "reference": aligned.model_dump(mode="json"),
        "alignment": aligner.last_score.model_dump(mode="json"),
        "feedback": feedback.model_dump(mode="json"),
        "validation": {"valid": True, "issues": []},
    }
    app = create_app(runtime=runtime, bus=bus, human_alignment=payload)
    with TestClient(app) as client:
        resp = client.get("/api/human-alignment/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["reference"]["alignment_score"] == 0.78
    assert data["reference"]["preferred_options"]
    assert data["feedback"]["option_id"] == "opt-1"


def test_webui_human_alignment_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/human-alignment/state")
    assert resp.json()["enabled"] is False
