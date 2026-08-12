"""Project Handoff Preflight:判断 GIT/SNAPSHOT、读取状态、输出 handoff 摘要。

无 .git 时正常运行(不 crash),禁止伪报 commit/push/CI。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml


def detect_mode(root: Path) -> str:
    return "GIT" if (root / ".git").exists() else "SNAPSHOT"


def load_current_state(root: Path) -> dict:
    path = root / ".project" / "CURRENT_STATE.yaml"
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def load_baseline(root: Path) -> dict:
    path = root / ".project" / "BASELINE.json"
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def git_working_tree(root: Path) -> str:
    if detect_mode(root) != "GIT":
        return "unavailable"
    try:
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0:
            return "unavailable"
        return "clean" if not result.stdout.strip() else "dirty"
    except Exception:
        return "unavailable"


def remote_status(root: Path) -> str:
    if detect_mode(root) != "GIT":
        return "unavailable"
    try:
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        remote = subprocess.run(
            ["git", "ls-remote", "origin", "main"],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if local.returncode != 0 or remote.returncode != 0:
            return "unavailable"
        remote_head = remote.stdout.split()[0] if remote.stdout.strip() else ""
        local_head = local.stdout.strip()
        if remote_head == local_head:
            return "synced"
        return "behind"
    except Exception:
        return "unavailable"


def compute_handoff(
    *,
    mode: str,
    working_tree: str,
    remote: str,
    blockers: list[str] | None = None,
) -> str:
    blockers = blockers or []
    if blockers:
        return "BLOCKED"
    if mode == "SNAPSHOT":
        return "READY"
    if working_tree == "dirty":
        return "SYNC_REQUIRED"
    if remote in ("behind", "unavailable"):
        return "SYNC_REQUIRED"
    return "READY"


def preflight(root: Path) -> dict:
    state = load_current_state(root)
    baseline = load_baseline(root)
    mode = detect_mode(root)
    working_tree = git_working_tree(root)
    remote = remote_status(root)
    project = (state.get("project") or {}).get("name", "unknown")
    source_baseline = (
        baseline.get("source_commit")
        or (state.get("baseline") or {}).get("source_commit")
        or "UNKNOWN"
    )
    phase = (state.get("phase") or {}).get("current", "UNKNOWN")
    last_completed = (state.get("phase") or {}).get(
        "last_completed",
        "UNKNOWN",
    )
    safety_mode = (state.get("runtime") or {}).get(
        "safety_mode",
        "MOCK_ONLY",
    )
    readiness = state.get("readiness") or {}
    blockers = list((state.get("handoff") or {}).get("blockers") or [])
    handoff = compute_handoff(
        mode=mode,
        working_tree=working_tree,
        remote=remote,
        blockers=blockers,
    )
    return {
        "repository_mode": mode,
        "project": project,
        "source_baseline": source_baseline,
        "current_phase": phase,
        "last_completed": last_completed,
        "safety_mode": safety_mode,
        "real_vision": readiness.get("real_vision", "UNKNOWN"),
        "knowledge": readiness.get("knowledge", "UNKNOWN"),
        "controlled_execution": readiness.get(
            "controlled_execution",
            "UNKNOWN",
        ),
        "working_tree": working_tree,
        "remote": remote,
        "handoff": handoff,
    }


def main() -> int:
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    info = preflight(root)
    print(f"Repository Mode: {info['repository_mode']}")
    print(f"Project: {info['project']}")
    print(f"Source Baseline: {info['source_baseline']}")
    print(f"Current Phase: {info['current_phase']}")
    print(f"Last Completed: {info['last_completed']}")
    print(f"Safety Mode: {info['safety_mode']}")
    print(f"Real Vision: {info['real_vision']}")
    print(f"Knowledge: {info['knowledge']}")
    print(f"Working Tree: {info['working_tree']}")
    print(f"Remote: {info['remote']}")
    print(f"Handoff: {info['handoff']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
