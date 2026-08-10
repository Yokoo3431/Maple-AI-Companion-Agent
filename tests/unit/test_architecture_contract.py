"""Architecture Contract 测试:Schema 版本 / Trace 兼容 / 依赖规则 / 安全边界 / WebUI。"""

from __future__ import annotations

import re
from pathlib import Path

from fastapi.testclient import TestClient

from maple_agent import __version__
from maple_agent.agent_loop.trace import AgentLoopStage, AgentLoopTrace
from maple_agent.architecture import (
    AGENT_VERSION,
    ARCHITECTURE_VERSION,
    CORE_MODULES,
    FORBIDDEN_DEPENDENCIES,
    SAFETY_BOUNDARY,
    SAFETY_MODE,
    TRACE_CONTRACT,
    TRACE_SCHEMA_VERSION,
)
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app

SRC_ROOT = Path(__file__).resolve().parents[2] / "src" / "maple_agent"
DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "architecture"


def test_schema_version_exists():
    assert ARCHITECTURE_VERSION == "1.0"
    assert TRACE_SCHEMA_VERSION == "1.0"
    assert TRACE_CONTRACT["schema_version"] == TRACE_SCHEMA_VERSION


def test_trace_schema_compatible():
    trace = AgentLoopTrace(
        trace_id="trace-schema",
        stages=[
            AgentLoopStage(stage="observation", status="completed"),
            AgentLoopStage(stage="sandbox", status="MOCK_ONLY"),
        ],
        final_status="COMPLETED",
    )
    payload = trace.model_dump(mode="json")
    # 新增字段
    assert payload["schema_version"] == TRACE_SCHEMA_VERSION
    assert payload["agent_version"] == AGENT_VERSION
    # 既有字段保留(兼容)
    assert payload["trace_id"] == "trace-schema"
    assert payload["stages"][0]["stage"] == "observation"
    assert payload["stages"][1]["status"] == "MOCK_ONLY"
    assert payload["final_status"] == "COMPLETED"


def test_trace_required_fields_contract():
    for field in TRACE_CONTRACT["required_fields"]:
        assert field in AgentLoopTrace.model_fields, f"缺少字段 {field}"
    assert "schema_version" in AgentLoopTrace.model_fields
    assert "agent_version" in AgentLoopTrace.model_fields


def test_agent_version_matches_package():
    assert AGENT_VERSION == __version__


def test_dependency_rules():
    violations: list[str] = []
    for source, targets in FORBIDDEN_DEPENDENCIES.items():
        source_dir = SRC_ROOT / source
        if not source_dir.is_dir():
            continue
        for py_file in source_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            for target in targets:
                pattern = (
                    rf"^\s*(from maple_agent\.{re.escape(target)}"
                    rf"|import maple_agent\.{re.escape(target)})"
                )
                if re.search(pattern, text, re.MULTILINE):
                    violations.append(f"{source}/{py_file.name} -> {target}")
    assert violations == [], f"存在禁止依赖: {violations}"


def test_safety_boundary_markers():
    assert SAFETY_MODE == "MOCK_ONLY"
    allowed = set(SAFETY_BOUNDARY["allowed"])
    forbidden = set(SAFETY_BOUNDARY["forbidden"])
    assert {
        "observation",
        "planning",
        "confirmation",
        "mock_execution",
        "replay",
    } <= allowed
    assert {
        "physical_input",
        "automation_control",
        "client_modification",
    } <= forbidden
    assert not (allowed & forbidden)


def test_core_modules_registered():
    assert len(CORE_MODULES) >= 10
    for module in (
        "observation",
        "vision_eval",
        "decision",
        "action_plan",
        "confirmation",
        "executor_sandbox",
        "reflection",
        "evaluation",
        "agent_loop",
    ):
        assert module in CORE_MODULES
        assert (SRC_ROOT / module).is_dir(), f"模块目录缺失: {module}"


def test_architecture_docs_exist():
    for name in (
        "architecture_overview.md",
        "module_contract.md",
        "data_schema.md",
        "trace_schema.md",
        "safety_boundary.md",
        "extension_guideline.md",
    ):
        assert (DOCS_ROOT / name).exists(), f"文档缺失: {name}"


def test_webui_architecture_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    payload = {
        "version": ARCHITECTURE_VERSION,
        "module_count": len(CORE_MODULES),
        "trace_version": TRACE_SCHEMA_VERSION,
        "safety_mode": SAFETY_MODE,
    }
    app = create_app(runtime=runtime, bus=bus, architecture=payload)
    with TestClient(app) as client:
        resp = client.get("/api/architecture/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["version"] == "1.0"
    assert data["module_count"] == len(CORE_MODULES)
    assert data["trace_version"] == "1.0"
    assert data["safety_mode"] == "MOCK_ONLY"


def test_webui_architecture_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/architecture/state")
    assert resp.json()["enabled"] is False
