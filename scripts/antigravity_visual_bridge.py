"""Thin read-only launcher for the existing Antigravity visual contract.

This is a compatibility launcher, not a second provider or vision pipeline.  It
keeps the existing ``AntigravityVisualSemanticProvider`` command shape while
using agy's ``--add-dir`` plus strict ``--json-schema`` interface.  Only
``structured_output`` is accepted from agy; its human-facing response and tool
metadata are deliberately ignored.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from maple_agent.vision_runtime.visual_semantics import VisualSemanticResponse


def _invalid(reason: str) -> dict[str, object]:
    """Return the existing contract's sanitized fail-closed response."""
    return {
        "status": "VLM_OUTPUT_INVALID",
        "candidates": [],
        "validation_status": reason,
        "structured_output_failure_count": 1,
    }


def _agy_executable() -> str | None:
    configured = os.environ.get("MAPLE_AGY_EXECUTABLE", "").strip()
    if configured:
        path = Path(configured)
        return str(path) if path.is_file() else None
    return shutil.which("agy")


def _request_metadata() -> tuple[str, str]:
    try:
        payload = json.load(sys.stdin)
        request = payload["request"]
        frame_reference = str(request["frame_reference"])
        model = str(request.get("model_profile") or "UNBOUND")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError):
        return "", "UNBOUND"
    return frame_reference, model


def _extract_structured_output(stdout: str) -> object | None:
    """Accept only agy's schema-constrained result, never free-form response."""
    try:
        outer = json.loads(stdout)
    except json.JSONDecodeError:
        return None
    if not isinstance(outer, dict):
        return None
    return outer.get("structured_output")


def main() -> int:
    if len(sys.argv) < 2:
        print(json.dumps(_invalid("IMAGE_PATH_REQUIRED")))
        return 0
    image_path = Path(sys.argv[1])
    frame_reference, model = _request_metadata()
    if not frame_reference or not image_path.is_file():
        print(json.dumps(_invalid("IMAGE_TRANSPORT_FAILED")))
        return 0
    executable = _agy_executable()
    if executable is None:
        print(json.dumps(_invalid("PROVIDER_NOT_FOUND")))
        return 0

    model = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] else model
    prompt = (
        "Inspect only the supplied image file in the allowed directory. "
        "Return only the existing VisualSemanticResponse JSON schema. "
        f"Use frame_reference={frame_reference!r}. "
        "Report only clearly visible MAP, HP, MP, or UI_TEXT facts. "
        "For HP/MP, candidate_value must be a normalized ratio and observed "
        "current/max must be paired when present. Unknown facts must remain "
        "unknown. Do not infer hidden state, use history or knowledge, or "
        "output actions, commands, recommendations, or prose."
    )

    schema_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".json",
            dir=image_path.parent,
            delete=False,
        ) as schema_file:
            schema_path = Path(schema_file.name)
            json.dump(VisualSemanticResponse.model_json_schema(), schema_file)
        command = [
            executable,
            f"--print={prompt}",
            "--output-format",
            "json",
            f"--json-schema={schema_path}",
            "--model",
            model,
            "--sandbox",
            "--mode",
            "plan",
            "--disable-slash-commands",
            "--add-dir",
            str(image_path.parent),
            "--print-timeout",
            "90s",
        ]
        completed = subprocess.run(
            command,
            cwd=image_path.parent,
            input="",
            capture_output=True,
            text=True,
            timeout=95,
            check=False,
            shell=False,
        )
        if completed.returncode != 0:
            print(json.dumps(_invalid("PROVIDER_NONZERO_EXIT")))
            return 0
        structured = _extract_structured_output(completed.stdout)
        if structured is None:
            print(json.dumps(_invalid("SCHEMA_OUTPUT_MISSING")))
            return 0
        response = VisualSemanticResponse.from_payload(structured)
        if response.candidates:
            response = response.model_copy(
                update={
                    "candidates": [
                        candidate.model_copy(
                            update={
                                "provider": "antigravity_cli",
                                "model": model,
                                "frame_reference": frame_reference,
                            }
                        )
                        for candidate in response.candidates
                    ]
                }
            )
        print(json.dumps(response.model_dump(mode="json"), ensure_ascii=False))
        return 0
    except subprocess.TimeoutExpired:
        print(json.dumps(_invalid("PROVIDER_TIMEOUT")))
        return 0
    except OSError:
        print(json.dumps(_invalid("IMAGE_TRANSPORT_FAILED")))
        return 0
    finally:
        try:
            if schema_path is not None:
                schema_path.unlink(missing_ok=True)
        except (NameError, OSError):
            pass


if __name__ == "__main__":
    raise SystemExit(main())
