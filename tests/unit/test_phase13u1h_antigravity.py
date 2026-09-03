"""Phase 13-U.1h: isolated read-only visual provider tests."""

from __future__ import annotations

import json
import sys

from maple_agent.vision_runtime import (
    AntigravityVisualSemanticProvider,
    EphemeralFrameStore,
    VisualCandidateType,
    VisualSemanticAgreementGate,
    VisualSemanticCandidate,
    VisualSemanticRequest,
    VisualSemanticResponse,
    VisualSemanticStatus,
    VisualSemanticTrigger,
)


def _request(token: str) -> VisualSemanticRequest:
    return VisualSemanticRequest(
        provider_profile="test-cli",
        frame_reference=token,
        roi="map_label",
        trigger=VisualSemanticTrigger.MANUAL_PROBE,
    )


def _write_cli(tmp_path, output: str, *, delay: float = 0) -> list[str]:
    script = tmp_path / "fake_visual_cli.py"
    script.write_text(
        "import json, pathlib, sys, time\n"
        f"time.sleep({delay})\n"
        "payload = json.load(sys.stdin)\n"
        "assert pathlib.Path(sys.argv[1]).is_file()\n"
        f"raw_output = {output!r}\n"
        "try:\n"
        "    result = json.loads(raw_output)\n"
        "except json.JSONDecodeError:\n"
        "    print(raw_output)\n"
        "else:\n"
        "    for candidate in result.get('candidates', []):\n"
        "        candidate['frame_reference'] = payload['request']['frame_reference']\n"
        "    print(json.dumps(result))\n",
        encoding="utf-8",
    )
    return [sys.executable, str(script), "{image_path}"]


def test_cli_provider_transports_temporary_image_and_cleans_it(tmp_path):
    output = json.dumps(
        {
            "status": "VALID",
            "candidates": [
                {
                    "provider": "fake-cli",
                    "model": "configured",
                    "frame_reference": "frame-token",
                    "candidate_type": "MAP",
                    "candidate_value": "map:fixture",
                    "confidence": 0.7,
                }
            ],
        }
    )
    command = _write_cli(tmp_path, output)
    with EphemeralFrameStore(tmp_path / "frames") as store:
        provider = AntigravityVisualSemanticProvider(
            command=command,
            frame_store=store,
        )
        token = store.put(b"sanitized image bytes")
        request = _request(token).model_copy(update={"frame_reference": token})
        response = provider.observe(request)

        assert response.status is VisualSemanticStatus.VALID
        assert len(response.candidates) == 1
        assert store.path_for(token) is None
        assert provider.last_call_metadata["image_sent"] is True
        assert str(tmp_path) not in json.dumps(provider.last_call_metadata)


def test_invalid_json_fails_closed_and_cleans_image(tmp_path):
    command = _write_cli(tmp_path, "not-json")
    with EphemeralFrameStore(tmp_path / "frames") as store:
        provider = AntigravityVisualSemanticProvider(command=command, frame_store=store)
        token = store.put(b"image")
        response = provider.observe(_request(token))

        assert response.status is VisualSemanticStatus.INVALID
        assert response.candidates == []
        assert store.path_for(token) is None


def test_extra_action_field_is_rejected_by_existing_schema(tmp_path):
    output = json.dumps(
        {
            "status": "VALID",
            "candidates": [
                {
                    "provider": "fake-cli",
                    "frame_reference": "frame-token",
                    "candidate_type": "MAP",
                    "candidate_value": "map:fixture",
                    "confidence": 0.7,
                    "action": "click",
                }
            ],
        }
    )
    with EphemeralFrameStore(tmp_path / "frames") as store:
        provider = AntigravityVisualSemanticProvider(
            command=_write_cli(tmp_path, output),
            frame_store=store,
        )
        token = store.put(b"image")
        response = provider.observe(_request(token))

        assert response.status is VisualSemanticStatus.INVALID
        assert response.structured_output_failure_count == 1


def test_provider_unavailable_fails_closed_and_cleans_image(tmp_path):
    with EphemeralFrameStore(tmp_path / "frames") as store:
        provider = AntigravityVisualSemanticProvider(frame_store=store)
        token = store.put(b"image")
        response = provider.observe(_request(token))

        assert response.status is VisualSemanticStatus.UNAVAILABLE
        assert response.validation_status == "CLI_IMAGE_INPUT_UNAVAILABLE"
        assert store.path_for(token) is None


def test_cli_timeout_fails_closed_and_cleans_image(tmp_path):
    command = _write_cli(tmp_path, "{}", delay=1)
    with EphemeralFrameStore(tmp_path / "frames") as store:
        provider = AntigravityVisualSemanticProvider(
            command=command,
            frame_store=store,
            timeout_seconds=0.01,
        )
        token = store.put(b"image")
        response = provider.observe(_request(token))

        assert response.status is VisualSemanticStatus.UNAVAILABLE
        assert response.validation_status == "CLI_TIMEOUT"
        assert store.path_for(token) is None


def test_hp_mp_candidate_preserves_current_max_and_ratio():
    candidate = VisualSemanticCandidate(
        provider="fake-cli",
        frame_reference="frame-token",
        candidate_type=VisualCandidateType.HP,
        candidate_value="0.8",
        observed_current=80,
        observed_max=100,
        normalized_ratio=0.8,
        confidence=0.6,
    )
    assert candidate.normalized_ratio == 0.8
    assert candidate.observed_current == 80
    assert candidate.observed_max == 100


def test_hp_mp_current_without_max_cannot_become_ratio():
    try:
        VisualSemanticCandidate(
            provider="fake-cli",
            frame_reference="frame-token",
            candidate_type=VisualCandidateType.HP,
            candidate_value="0.8",
            observed_current=80,
            confidence=0.6,
        )
    except ValueError:
        return
    raise AssertionError("current-only HP must not enter normalized-ratio evidence")


def test_multi_frame_agreement_preserves_weakest_confidence():
    responses = [
        VisualSemanticResponse(
            status=VisualSemanticStatus.VALID,
            candidates=[
                VisualSemanticCandidate(
                    provider="fake-cli",
                    frame_reference=f"frame-{index}",
                    candidate_type=VisualCandidateType.MAP,
                    candidate_value="map:fixture",
                    confidence=confidence,
                )
            ],
        )
        for index, confidence in enumerate((0.8, 0.5))
    ]
    result = VisualSemanticAgreementGate.evaluate(responses)
    assert result.confirmed is True
    assert result.status == "CONSISTENT"
    assert result.confidence_bound == 0.5


def test_multi_frame_conflict_is_not_promoted():
    responses = [
        VisualSemanticResponse(
            status=VisualSemanticStatus.VALID,
            candidates=[
                VisualSemanticCandidate(
                    provider="fake-cli",
                    frame_reference=f"frame-{value}",
                    candidate_type=VisualCandidateType.MAP,
                    candidate_value=value,
                    confidence=0.8,
                )
            ],
        )
        for value in ("map:a", "map:b")
    ]
    result = VisualSemanticAgreementGate.evaluate(responses)
    assert result.confirmed is False
    assert result.status == "CONFLICT"
    assert result.conflict_count == 2
