"""CLI 入口:start / doctor / test(Phase 0)。"""

from __future__ import annotations

import argparse
import platform
import subprocess
import sys
from pathlib import Path

from maple_agent import __version__
from maple_agent.bootstrap import BootstrapResult, bootstrap
from maple_agent.config import build_settings
from maple_agent.events import EventBus
from maple_agent.logging_setup import setup_logging
from maple_agent.providers import (
    MockLLMProvider,
    MockOCRProvider,
    MockStorageProvider,
    MockVisionProvider,
)
from maple_agent.runtime import RuntimeManager, RuntimeState
from maple_agent.webui.app import create_app

ROOT = Path(__file__).resolve().parents[2]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="maple_agent",
        description="Maple AI Companion Agent (Phase 0)",
    )
    sub = parser.add_subparsers(dest="command")

    start = sub.add_parser("start", help="启动 WebUI 控制台")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=8080)

    sub.add_parser("doctor", help="环境与模块自检")
    sub.add_parser("test", help="运行测试套件")
    return parser


def cmd_start(args: argparse.Namespace) -> int:
    import uvicorn

    result = bootstrap()
    prepare_for_start(result)
    print(
        f"Maple AI Companion Agent v{__version__} 控制台: "
        f"http://{args.host}:{args.port}"
    )
    uvicorn.run(result.app, host=args.host, port=args.port, log_level="info")
    return 0


def prepare_for_start(result: BootstrapResult) -> None:
    """启动流程收尾:Runtime 进入 READY;禁止自动进入 RUNNING。"""
    result.runtime.start()


def _check(
    results: list[tuple[str, str, str]],
    name: str,
    fn: object,
) -> None:
    try:
        fn()
        results.append((name, "PASS", ""))
    except Exception as exc:
        results.append((name, "FAIL", str(exc)))


def cmd_doctor(_args: argparse.Namespace) -> int:
    results: list[tuple[str, str, str]] = []

    def config_ok() -> None:
        build_settings()

    def logging_ok() -> None:
        setup_logging(ROOT / "logs", level="INFO", console=False)

    def providers_ok() -> None:
        for provider in (
            MockLLMProvider(),
            MockVisionProvider(),
            MockOCRProvider(),
            MockStorageProvider(),
        ):
            provider.initialize()
            provider.shutdown()

    def runtime_ok() -> None:
        bus = EventBus()
        runtime = RuntimeManager(bus=bus)
        runtime.start()
        if runtime.state is not RuntimeState.READY:
            raise RuntimeError("状态机未进入 READY")
        runtime.stop()

    def webui_ok() -> None:
        bus = EventBus()
        runtime = RuntimeManager(bus=bus)
        create_app(runtime=runtime, bus=bus, providers={})

    _check(results, "config loads", config_ok)
    _check(results, "logging writable", logging_ok)
    _check(results, "providers lifecycle", providers_ok)
    _check(results, "runtime state machine", runtime_ok)
    _check(results, "webui app builds", webui_ok)

    print(
        f"Maple AI Companion Agent doctor v{__version__} "
        f"({platform.python_version()})"
    )
    for name, status, detail in results:
        suffix = f" - {detail}" if detail else ""
        print(f"[{status}] {name}{suffix}")
    failed = [item for item in results if item[1] == "FAIL"]
    print(f"结果: {len(results) - len(failed)}/{len(results)} 通过")
    return 1 if failed else 0


def cmd_test(_args: argparse.Namespace) -> int:
    print("运行测试套件 (pytest)...")
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "-q"],
        cwd=ROOT,
    )
    return proc.returncode


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command in (None, "start"):
        return cmd_start(args)
    if args.command == "doctor":
        return cmd_doctor(args)
    if args.command == "test":
        return cmd_test(args)
    parser.print_help()
    return 2
