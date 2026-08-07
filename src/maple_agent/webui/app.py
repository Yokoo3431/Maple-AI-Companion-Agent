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
from maple_agent.agent.loop import AgentLoop
from maple_agent.context.builder import ContextBuilder
from maple_agent.events import EventBus
from maple_agent.game.window import GameWindowDetector, MockGameWindowDetector
from maple_agent.goal.provider import GoalProvider
from maple_agent.planner.provider import PlannerProvider
from maple_agent.providers import BaseProvider
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.runtime import IllegalTransitionError, RuntimeManager, RuntimeState
from maple_agent.vision.worker import VisionWorker
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
    vision_worker: VisionWorker | None = None,
    knowledge: KnowledgeProvider | None = None,
    context_builder: ContextBuilder | None = None,
    planner: PlannerProvider | None = None,
    agent_loop: AgentLoop | None = None,
    goal_provider: GoalProvider | None = None,
) -> FastAPI:
    """构建 Phase 0 WebUI 控制台应用。"""
    providers = providers or {}
    ws_manager = WebSocketManager(bus=bus)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime.attach()
        ws_manager.attach()
        await bus.start()
        if vision_worker is not None:
            vision_worker.capture.initialize()
            if vision_worker.ocr is not None:
                vision_worker.ocr.initialize()
            vision_worker.start()
        yield
        if vision_worker is not None:
            await vision_worker.stop()
            if vision_worker.ocr is not None:
                vision_worker.ocr.shutdown()
            vision_worker.capture.shutdown()
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

    @app.get("/api/vision/state")
    async def api_vision_state():
        if vision_worker is None:
            return {"enabled": False, "worker_state": None, "fps": None, "latest_frame": None}
        frame = vision_worker.latest_frame
        return {
            "enabled": True,
            "worker_state": vision_worker.state.value,
            "fps": vision_worker.fps,
            "latest_frame": frame.model_dump(mode="json") if frame is not None else None,
            "latest_ocr": [
                item.model_dump(mode="json") for item in vision_worker.latest_ocr
            ],
            "latest_vision": (
                vision_worker.latest_vision.model_dump(mode="json")
                if vision_worker.latest_vision is not None
                else None
            ),
            "latest_world": (
                vision_worker.latest_world.model_dump(mode="json")
                if vision_worker.latest_world is not None
                else None
            ),
        }

    @app.get("/api/knowledge/state")
    async def api_knowledge_state():
        if knowledge is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "status": knowledge.profile_status,
            "game_profile": knowledge.game_profile,
            "version": knowledge.version,
            "counts": knowledge.counts,
        }

    @app.get("/api/context/state")
    async def api_context_state():
        if context_builder is None or vision_worker is None:
            return {"enabled": False}
        context = context_builder.build(
            vision_state=vision_worker.latest_vision,
            world_state=vision_worker.latest_world,
            runtime_state=runtime.state.value,
        )
        return {"enabled": True, **context.model_dump(mode="json")}

    @app.get("/api/planner/state")
    async def api_planner_state():
        if planner is None:
            return {"enabled": False}
        last_result = getattr(planner, "last_result", None)
        last_error = getattr(planner, "last_error", None)
        status = "error" if last_error else ("ok" if last_result is not None else "idle")
        return {
            "enabled": True,
            "planner": type(planner).__name__,
            "status": status,
            "last_summary": last_result.summary if last_result else "",
            "steps": len(last_result.steps) if last_result else 0,
            "last_error": last_error or "",
            "message": "Phase 1.8-A:仅生成计划,不执行动作",
        }

    @app.get("/api/loop/state")
    async def api_loop_state():
        if agent_loop is None:
            return {"enabled": False}
        return {
            "enabled": True,
            "state": agent_loop.state.value,
            "last_summary": (
                agent_loop.last_plan.summary if agent_loop.last_plan is not None else ""
            ),
            "steps": len(agent_loop.last_plan.steps) if agent_loop.last_plan is not None else 0,
            "last_error": agent_loop.last_error or "",
        }

    @app.get("/api/quest/state")
    async def api_quest_state():
        if knowledge is None:
            return {"enabled": False}
        try:
            available = knowledge.get_available_quests()
        except Exception:
            available = []
        return {
            "enabled": True,
            "profile": knowledge.game_profile,
            "quest_total": len(knowledge.data.quests_domain),
            "available_total": len(available),
            "available_names": [quest.name for quest in available],
        }

    @app.get("/api/goal/state")
    async def api_goal_state():
        if goal_provider is None:
            return {"enabled": False}
        active = goal_provider.get_active_goal()
        candidates = goal_provider.get_candidate_goals()
        return {
            "enabled": True,
            "active_goal": active.model_dump(mode="json") if active is not None else None,
            "candidate_count": len(candidates),
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
