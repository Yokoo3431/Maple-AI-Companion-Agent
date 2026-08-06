"""日志系统单测:文件创建 / 等级过滤 / trace_id 跨文件关联 / 轮转。"""

import logging

import pytest

from maple_agent.logging_setup import (
    TraceContext,
    category_for,
    level_number,
    setup_logging,
)


def test_setup_creates_all_log_files(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    expected = [
        "startup.log",
        "runtime.log",
        "agent.log",
        "vision.log",
        "input.log",
        "task.log",
        "error.log",
    ]
    for name in expected:
        assert (tmp_path / name).exists(), f"缺少日志文件: {name}"


@pytest.mark.parametrize("level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
def test_standard_levels_accepted(level):
    assert level_number(level) >= logging.DEBUG


def test_unsupported_level_rejected(tmp_path):
    with pytest.raises(ValueError, match="固定等级"):
        setup_logging(tmp_path, level="TRACE", console=False)


def test_levels_written_and_filtered(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    logger = logging.getLogger("maple_agent.agent.controller")
    logger.debug("debug line")
    logger.info("info line")
    logger.warning("warning line")
    logger.error("error line")
    logger.critical("critical line")

    agent_log = (tmp_path / "agent.log").read_text(encoding="utf-8")
    assert "info line" in agent_log
    assert "warning line" in agent_log
    assert "error line" in agent_log
    assert "critical line" in agent_log
    assert "debug line" not in agent_log  # INFO 级别下 DEBUG 被过滤


def test_error_log_only_error_and_above(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    logger = logging.getLogger("maple_agent.runtime.manager")
    logger.info("normal info")
    logger.error("boom")
    error_log = (tmp_path / "error.log").read_text(encoding="utf-8")
    assert "boom" in error_log
    assert "normal info" not in error_log


def test_category_mapping():
    assert category_for("maple_agent.runtime.manager") == "runtime"
    assert category_for("maple_agent.agent.controller") == "agent"
    assert category_for("maple_agent.vision.capture") == "vision"
    assert category_for("maple_agent.task.runner") == "task"
    assert category_for("maple_agent.input.mock") == "input"
    assert category_for("maple_agent.main") == "startup"


def test_trace_spans_cross_file(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    with TraceContext.new() as trace:
        logging.getLogger("maple_agent.runtime.manager").info("runtime step")
        logging.getLogger("maple_agent.agent.controller").info("agent step")
        logging.getLogger("maple_agent.vision.capture").info("vision step")
        logging.getLogger("maple_agent.task.runner").info("task step")

    for name in ("runtime", "agent", "vision", "task"):
        content = (tmp_path / f"{name}.log").read_text(encoding="utf-8")
        assert f"trace={trace.trace_id}" in content, f"{name}.log 缺少 trace_id"
        assert f"corr={trace.correlation_id}" in content


def test_trace_ids_unique_across_contexts():
    with TraceContext.new() as first:
        first_id = first.trace_id
    with TraceContext.new() as second:
        second_id = second.trace_id
    assert first_id != second_id


def test_rotation(tmp_path):
    setup_logging(
        tmp_path,
        level="DEBUG",
        console=False,
        max_bytes=1024,
        backup_count=2,
    )
    logger = logging.getLogger("maple_agent.runtime.manager")
    payload = "x" * 900
    for _ in range(4):
        logger.info(payload)
    names = {p.name for p in tmp_path.glob("runtime.log*")}
    assert "runtime.log" in names
    assert "runtime.log.1" in names
