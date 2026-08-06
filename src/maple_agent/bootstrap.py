"""应用装配:Config -> Logging -> EventBus -> Providers -> Runtime -> WebUI。"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from maple_agent.config import Settings, build_settings
from maple_agent.events import EventBus
from maple_agent.game.window import GameWindowDetector, MockGameWindowDetector
from maple_agent.logging_setup import setup_logging
from maple_agent.providers import (
    BaseProvider,
    JsonKnowledgeProvider,
    MockLLMProvider,
    MockOCRProvider,
    MockStorageProvider,
    MockVisionProvider,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app

logger = logging.getLogger("maple_agent")


@dataclass
class BootstrapResult:
    """应用装配产物。"""

    settings: Settings
    bus: EventBus
    runtime: RuntimeManager
    providers: dict[str, BaseProvider]
    detector: GameWindowDetector
    app: Any  # FastAPI 应用


def _build_providers(game_profile: str) -> dict[str, BaseProvider]:
    providers: dict[str, BaseProvider] = {
        "llm": MockLLMProvider(),
        "vision": MockVisionProvider(),
        "ocr": MockOCRProvider(),
        "storage": MockStorageProvider(),
        "knowledge": JsonKnowledgeProvider(game_profile=game_profile),
    }
    return providers


def bootstrap(
    *,
    env_file: Path | None = None,
    logs_dir: str | Path = "logs",
) -> BootstrapResult:
    """按 Phase 0 启动流程装配应用。"""
    settings = build_settings(env_file=env_file)
    setup_logging(logs_dir=logs_dir, level=settings.app.log_level, console=True)

    logger.info("startup 1/6: config loaded (log_level=%s)", settings.app.log_level)
    logger.info("startup 2/6: logging ready (dir=%s)", logs_dir)

    bus = EventBus()
    logger.info("startup 3/6: event bus ready")

    providers = _build_providers(settings.knowledge.game_profile)
    for provider in providers.values():
        provider.initialize()
    logger.info("startup 4/6: providers initialized (Mock + Knowledge)")

    runtime = RuntimeManager(bus=bus)
    detector = MockGameWindowDetector(None)
    logger.warning("startup 5/6: runtime ready; 窗口检测为 Mock(未接入真实 win32)")

    app = create_app(
        runtime=runtime,
        bus=bus,
        providers=providers,
        detector=detector,
        knowledge=providers.get("knowledge"),
    )
    logger.info("startup 6/6: webui built")
    return BootstrapResult(
        settings=settings,
        bus=bus,
        runtime=runtime,
        providers=providers,
        detector=detector,
        app=app,
    )
