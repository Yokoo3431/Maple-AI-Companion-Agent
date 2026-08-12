"""Project Handoff Preflight 单测:Git/Snapshot/状态解析/缺失与损坏容错。"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from scripts.check_project_handoff import (  # noqa: E402
    compute_handoff,
    detect_mode,
    git_working_tree,
    load_baseline,
    load_current_state,
    preflight,
    remote_status,
)


def _write_project_files(root: Path) -> None:
    project_dir = root / ".project"
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "CURRENT_STATE.yaml").write_text(
        yaml.safe_dump(
            {
                "project": {"name": "Maple-AI-Companion-Agent"},
                "baseline": {
                    "source_commit": "abc123",
                    "commit": "PENDING",
                },
                "phase": {
                    "current": "13-H",
                    "last_completed": "13-G",
                },
                "runtime": {"safety_mode": "MOCK_ONLY"},
                "readiness": {
                    "real_vision": "NOT_READY",
                    "knowledge": "FOUNDATION_ONLY",
                    "controlled_execution": "NOT_READY",
                },
                "handoff": {"blockers": []},
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    (project_dir / "BASELINE.json").write_text(
        json.dumps({"source_commit": "abc123"}),
        encoding="utf-8",
    )


def test_git_mode_detection(tmp_path):
    (tmp_path / ".git").mkdir()
    assert detect_mode(tmp_path) == "GIT"


def test_snapshot_mode_no_crash(tmp_path):
    _write_project_files(tmp_path)
    info = preflight(tmp_path)
    assert info["repository_mode"] == "SNAPSHOT"
    assert info["source_baseline"] == "abc123"
    assert info["handoff"] == "READY"


def test_missing_baseline(tmp_path):
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)
    info = preflight(tmp_path)
    assert info["source_baseline"] == "UNKNOWN"
    assert info["repository_mode"] == "SNAPSHOT"


def test_malformed_current_state(tmp_path):
    (tmp_path / ".project").mkdir(parents=True, exist_ok=True)
    (tmp_path / ".project" / "CURRENT_STATE.yaml").write_text(
        "not: [valid: yaml:",
        encoding="utf-8",
    )
    state = load_current_state(tmp_path)
    assert state == {}
    info = preflight(tmp_path)
    assert info["safety_mode"] == "MOCK_ONLY"


def test_safety_mode_parsing(tmp_path):
    _write_project_files(tmp_path)
    info = preflight(tmp_path)
    assert info["safety_mode"] == "MOCK_ONLY"


def test_readiness_parsing(tmp_path):
    _write_project_files(tmp_path)
    info = preflight(tmp_path)
    assert info["real_vision"] == "NOT_READY"
    assert info["knowledge"] == "FOUNDATION_ONLY"
    assert info["controlled_execution"] == "NOT_READY"


def test_handoff_status_blocked():
    assert (
        compute_handoff(
            mode="GIT",
            working_tree="clean",
            remote="synced",
            blockers=["tests failing"],
        )
        == "BLOCKED"
    )


def test_handoff_status_sync_required():
    assert (
        compute_handoff(
            mode="GIT",
            working_tree="dirty",
            remote="synced",
        )
        == "SYNC_REQUIRED"
    )


def test_handoff_status_ready():
    assert (
        compute_handoff(
            mode="GIT",
            working_tree="clean",
            remote="synced",
        )
        == "READY"
    )


def test_no_git_no_crash(tmp_path):
    info = preflight(tmp_path)
    assert info["repository_mode"] == "SNAPSHOT"
    assert git_working_tree(tmp_path) == "unavailable"
    assert remote_status(tmp_path) == "unavailable"


def test_git_unavailable_commands(tmp_path):
    (tmp_path / ".git").mkdir()
    # 非真实 git repo:命令失败 -> unavailable,不 crash
    assert git_working_tree(tmp_path) == "unavailable"
    assert remote_status(tmp_path) == "unavailable"
    assert load_baseline(tmp_path) == {}
