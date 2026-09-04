"""Phase 13-U.1i: thin agy compatibility launcher tests."""

from __future__ import annotations

import io
import json
import sys
from subprocess import CompletedProcess

from scripts import antigravity_visual_bridge as bridge


def _invoke(monkeypatch, tmp_path, outer: dict[str, object]) -> dict[str, object]:
    image = tmp_path / "synthetic.png"
    image.write_bytes(b"sanitized synthetic image")
    calls: list[list[str]] = []

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs["shell"] is False
        assert kwargs["cwd"] == tmp_path
        return CompletedProcess(command, 0, json.dumps(outer), "")

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)
    monkeypatch.setattr(bridge.shutil, "which", lambda name: "agy.exe")
    monkeypatch.setenv("MAPLE_AGY_EXECUTABLE", "")
    monkeypatch.setattr(
        sys,
        "argv",
        ["antigravity_visual_bridge.py", str(image), "gemini-3.7-flash-low"],
    )
    monkeypatch.setattr(
        sys,
        "stdin",
        io.StringIO(
            json.dumps(
                {
                    "request": {
                        "frame_reference": "synthetic_token",
                        "model_profile": "gemini-3.7-flash-low",
                    }
                }
            )
        ),
    )
    output: list[str] = []
    monkeypatch.setattr(bridge, "print", output.append, raising=False)
    assert bridge.main() == 0
    assert len(calls) == 1
    assert str(image) not in output[0]
    return json.loads(output[0])


def test_bridge_returns_only_existing_structured_contract(monkeypatch, tmp_path):
    result = _invoke(
        monkeypatch,
        tmp_path,
        {
            "structured_output": {
                "status": "UNKNOWN",
                "candidates": [],
                "validation_status": "VALIDATED",
                "structured_output_failure_count": 0,
            },
            "response": "contains ignored tool metadata",
        },
    )
    assert result["status"] == "UNKNOWN"
    assert "response" not in result


def test_bridge_rejects_free_form_response_without_structured_output(
    monkeypatch, tmp_path
):
    result = _invoke(
        monkeypatch,
        tmp_path,
        {"response": "{\"status\": \"VALID\"}"},
    )
    assert result["status"] == "VLM_OUTPUT_INVALID"
    assert result["validation_status"] == "SCHEMA_OUTPUT_MISSING"


def test_bridge_missing_image_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "argv", ["antigravity_visual_bridge.py", str(tmp_path / "gone.png")])
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"request": {"frame_reference": "token"}}'))
    output: list[str] = []
    monkeypatch.setattr(bridge, "print", output.append, raising=False)

    assert bridge.main() == 0
    result = json.loads(output[0])
    assert result["validation_status"] == "IMAGE_TRANSPORT_FAILED"
