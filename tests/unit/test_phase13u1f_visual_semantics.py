"""Phase 13-U.1f: provider contract, gating and existing evidence compatibility."""

from datetime import UTC, datetime, timedelta

import pytest

from maple_agent.companion_runtime.observation_adapter import (
    ExistingVisionObservationAdapter,
)
from maple_agent.hybrid_vision.models import ChangeResult, PerceptionMethod
from maple_agent.vision_runtime.visual_semantics import (
    MockVisualSemanticProvider,
    StrategyMetrics,
    VisualCandidateType,
    VisualSemanticCandidate,
    VisualSemanticGate,
    VisualSemanticRequest,
    VisualSemanticResponse,
    VisualSemanticStatus,
    VisualSemanticTrigger,
)

BASE = datetime(2026, 8, 29, tzinfo=UTC)


def _request(**overrides):
    values = {
        "provider_profile": "test-profile",
        "model_profile": "configured-test-model",
        "frame_reference": "frame-001",
        "roi": "map_label",
        "trigger": VisualSemanticTrigger.MANUAL_PROBE,
    }
    values.update(overrides)
    return VisualSemanticRequest(**values)


def _candidate(kind=VisualCandidateType.MAP, value="map:henesys"):
    return VisualSemanticCandidate(
        provider="mock",
        model="test-model",
        frame_reference="frame-001",
        candidate_type=kind,
        candidate_value=value,
        confidence=0.6,
        uncertainties=["当前仅依据可见区域"],
    )


def test_schema_rejects_private_reference_and_extra_action_field():
    with pytest.raises(ValueError):
        _request(frame_reference=r"C:\private\frame.png")
    invalid = {
        "status": "VALID",
        "candidates": [
            {
                **_candidate().model_dump(),
                "action": "click",
            }
        ],
    }
    response = VisualSemanticResponse.from_payload(invalid)
    assert response.status is VisualSemanticStatus.INVALID
    assert response.structured_output_failure_count == 1


def test_unknown_and_unavailable_are_fail_closed():
    provider = MockVisualSemanticProvider(available=False)
    response = provider.observe(_request())
    assert response.status is VisualSemanticStatus.UNAVAILABLE
    assert response.candidates == []
    assert provider.call_count == 1


def test_valid_candidate_enters_existing_evidence_contract():
    current = ExistingVisionObservationAdapter.from_visual_semantic_candidates(
        observation_id="obs-1",
        timestamp=BASE,
        candidates=[_candidate()],
    )
    assert len(current.evidence) == 1
    assert current.evidence[0].evidence_type == "map"
    assert current.evidence[0].method is PerceptionMethod.VLM_VISUAL_OBSERVATION
    assert current.evidence[0].source == "VLM_VISUAL_OBSERVATION"


def test_hp_mp_candidates_remain_player_state_not_entities():
    current = ExistingVisionObservationAdapter.from_visual_semantic_candidates(
        observation_id="obs-2",
        timestamp=BASE,
        candidates=[
            _candidate(VisualCandidateType.HP, "0.8"),
            _candidate(VisualCandidateType.MP, "0.5"),
        ],
    )
    assert current.evidence == []
    assert current.player_status is not None
    assert current.player_status.hp == 0.8
    assert current.player_status.mp == 0.5


def test_gate_skips_per_frame_calls_and_opens_after_cooldown():
    gate = VisualSemanticGate(cooldown_seconds=30)
    first = gate.evaluate(now=BASE, previous_unknown=True)
    assert first.call_allowed is True
    assert first.trigger is VisualSemanticTrigger.INITIAL_UNKNOWN
    gate.record_call(at=BASE, response=VisualSemanticResponse())
    blocked = gate.evaluate(now=BASE + timedelta(seconds=1), previous_unknown=True)
    assert blocked.call_allowed is False
    assert blocked.trigger is VisualSemanticTrigger.COOLDOWN_ACTIVE
    reopened = gate.evaluate(now=BASE + timedelta(seconds=31), previous_unknown=True)
    assert reopened.call_allowed is True
    assert reopened.trigger is VisualSemanticTrigger.COOLDOWN_EXPIRED


def test_gate_prefers_local_evidence_and_change_triggers():
    gate = VisualSemanticGate(cooldown_seconds=0)
    local = gate.evaluate(now=BASE, local_candidate_available=True)
    assert local.call_allowed is False
    changed = gate.evaluate(
        now=BASE,
        change=ChangeResult(
            changed=True,
            score=0.5,
            roi_scores={"map_label": 0.8},
        ),
        previous_unknown=False,
    )
    assert changed.call_allowed is True
    assert changed.trigger is VisualSemanticTrigger.MAP_REGION_CHANGE


def test_action_free_candidate_text_is_enforced():
    with pytest.raises(ValueError):
        _candidate(value="点击 NPC")


def test_metrics_keep_honest_denominators():
    empty = StrategyMetrics.from_samples(strategy="vlm", invocations=0)
    assert empty.useful_yield is None
    assert empty.estimated_calls_per_minute is None
    assert empty.p95_latency_ms is None
    measured = StrategyMetrics.from_samples(
        strategy="vlm",
        invocations=4,
        valid_candidates=1,
        latencies_ms=[10, 20, 30, 40],
        duration_seconds=120,
    )
    assert measured.useful_yield == 0.25
    assert measured.estimated_calls_per_minute == 2.0
    assert measured.p95_latency_ms == 30.0
