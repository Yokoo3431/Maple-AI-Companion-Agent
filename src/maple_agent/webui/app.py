"""FastAPI 应用:Dashboard 页面、Runtime 控制 API、WebSocket 推送。"""

from __future__ import annotations

import platform
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, WebSocket
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from maple_agent import __version__
from maple_agent.events import EventBus
from maple_agent.game.window import GameWindowDetector, MockGameWindowDetector
from maple_agent.providers import BaseProvider
from maple_agent.runtime import IllegalTransitionError, RuntimeManager, RuntimeState
from maple_agent.webui.ws import WebSocketManager

BASE_DIR = Path(__file__).parent
TEMPLATES = Jinja2Templates(directory=BASE_DIR / "templates")


def _window_snapshot(detector: GameWindowDetector | None) -> dict[str, Any]:
    if detector is None:
        return {"detected": False, "info": None}
    info = detector.find_window()
    return {
        "detected": info is not None,
        "info": asdict(info) if info is not None else None,
    }


def create_app(
    *,
    runtime: RuntimeManager,
    bus: EventBus,
    providers: dict[str, BaseProvider] | None = None,
    detector: GameWindowDetector | None = None,
) -> FastAPI:
    """构建 Phase 0 WebUI 控制台应用。"""
    providers = providers or {}
    ws_manager = WebSocketManager(bus=bus)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime.attach()
        ws_manager.attach()
        await bus.start()
        yield
        await bus.stop()
        ws_manager.detach()

    app = FastAPI(
        title="Maple AI Companion Agent",
        version=__version__,
        lifespan=lifespan,
    )
    app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
    app.state.ws_manager = ws_manager
    app.state.runtime = runtime

    def runtime_command(action: Callable[[], None]):
        try:
            action()
            return {"ok": True, "state": runtime.state.value}
        except IllegalTransitionError as exc:
            return JSONResponse(status_code=409, content={"ok": False, "error": str(exc)})

    @app.get("/", response_class=HTMLResponse)
    async def dashboard(request: Request):
        return TEMPLATES.TemplateResponse(request, "index.html", {"version": __version__})

    @app.get("/api/state")
    async def api_state():
        return {
            "version": __version__,
            "runtime": {"state": runtime.state.value},
            "providers": {name: provider.status.value for name, provider in providers.items()},
            "window": _window_snapshot(detector),
            "events": [event.model_dump(mode="json") for event in ws_manager.recent_events],
            "logs": list(ws_manager.recent_logs),
        }

    @app.get("/api/health")
    async def api_health():
        detector_kind = "none"
        if detector is not None:
            detector_kind = "mock" if isinstance(detector, MockGameWindowDetector) else "real"
        return {
            "status": "ok" if runtime.state is not RuntimeState.ERROR else "degraded",
            "runtime": {"state": runtime.state.value},
            "providers": {name: provider.status.value for name, provider in providers.items()},
            "system": {
                "status": "ok",
                "version": __version__,
                "python": platform.python_version(),
                "platform": platform.platform(),
                "detector": detector_kind,
            },
        }

    @app.post("/api/runtime/start")
    async def api_runtime_start():
        return runtime_command(runtime.start)

    @app.post("/api/runtime/pause")
    async def api_runtime_pause():
        return runtime_command(runtime.pause)

    @app.post("/api/runtime/stop")
    async def api_runtime_stop():
        return runtime_command(runtime.stop)

    @app.websocket("/ws")
    async def ws_endpoint(websocket: WebSocket):
        await ws_manager.connect(websocket)

    return app
