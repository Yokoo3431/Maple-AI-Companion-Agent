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
from maple_agent.confirmation.manager import (
    ConfirmationError,
    ConfirmationManager,
)
from maple_agent.context.builder import ContextBuilder
from maple_agent.events import EventBus
from maple_agent.game.window import GameWindowDetector, MockGameWindowDetector
from maple_agent.goal.provider import GoalProvider
from maple_agent.planner.provider import PlannerProvider
from maple_agent.providers import BaseProvider
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.runtime import IllegalTransitionError, RuntimeManager, RuntimeState
from maple_agent.validation.pipeline import VisionPipelineValidator
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
    pipeline_validator: VisionPipelineValidator | None = None,
    knowledge_eval: dict | None = None,
    knowledge_import: dict | None = None,
    decision: dict | None = None,
    action_plan: dict | None = None,
    execution_orchestration: dict | None = None,
    reflection: dict | None = None,
    experience: dict | None = None,
    evaluation: dict | None = None,
    observation: dict | None = None,
    vision_evaluation: dict | None = None,
    confirmation_manager: ConfirmationManager | None = None,
    confirmation: dict | None = None,
    executor_sandbox: dict | None = None,
    cognitive_loop: dict | None = None,
    architecture: dict | None = None,
    long_horizon: dict | None = None,
    goal_memory: dict | None = None,
    planning_optimizer: dict | None = None,
    failure_intelligence: dict | None = None,
    goal_scheduler: dict | None = None,
    environment: dict | None = None,
    world_model: dict | None = None,
    environment_reasoning: dict | None = None,
    environment_planning: dict | None = None,
    decision_reference: dict | None = None,
    human_alignment: dict | None = None,
    memory_graph: dict | None = None,
    semantic_memory: dict | None = None,
    maple_context: dict | None = None,
    maple_knowledge: dict | None = None,
    perception: dict | None = None,
    quest_reasoning: dict | None = None,
    perception_fusion: dict | None = None,
    reflex: dict | None = None,
    vision_runtime: dict | None = None,
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
        knowledge_state = None
        if vision_worker is not None and vision_worker.latest_world is not None:
            built = ContextBuilder(knowledge).build(
                vision_state=vision_worker.latest_vision,
                world_state=vision_worker.latest_world,
                runtime_state=runtime.state.value,
            )
            if built.knowledge_state is not None:
                knowledge_state = built.knowledge_state.model_dump(mode="json")
        dataset = knowledge.dataset
        retrieval = None
        if vision_worker is not None and vision_worker.latest_ocr:
            query = vision_worker.latest_ocr[0].text
            if knowledge_state is not None and knowledge_state.get("matched_entities"):
                top = knowledge_state["matched_entities"][0]
                retrieval = {
                    "query": query,
                    "top_candidate": top["name"],
                    "score": knowledge_state.get("confidence", 0),
                    "reason": knowledge_state.get("selection_reason", ""),
                }
            else:
                retrieval = {
                    "query": query,
                    "top_candidate": None,
                    "score": 0,
                    "reason": "no match",
                }
        return {
            "enabled": True,
            "status": knowledge.profile_status,
            "game_profile": knowledge.game_profile,
            "version": knowledge.version,
            "counts": knowledge.counts,
            "knowledge": knowledge_state,
            "dataset": {
                "version": knowledge.dataset_version(),
                "maps": len(dataset.maps) if dataset is not None else 0,
                "npcs": len(dataset.npcs) if dataset is not None else 0,
                "monsters": len(dataset.monsters) if dataset is not None else 0,
            },
            "retrieval": retrieval,
            "evaluation": knowledge_eval,
        }

    @app.get("/api/knowledge/import")
    async def api_knowledge_import():
        if knowledge_import is None:
            return {"enabled": False}
        return {"enabled": True, **knowledge_import}

    @app.get("/api/decision/state")
    async def api_decision_state():
        if decision is None:
            return {"enabled": False}
        return {"enabled": True, **decision}

    @app.get("/api/action-plan/state")
    async def api_action_plan_state():
        if action_plan is None:
            return {"enabled": False}
        return {"enabled": True, **action_plan}

    @app.get("/api/execution/orchestration/state")
    async def api_execution_orchestration_state():
        if execution_orchestration is None:
            return {"enabled": False}
        return {"enabled": True, **execution_orchestration}

    @app.get("/api/reflection/state")
    async def api_reflection_state():
        if reflection is None:
            return {"enabled": False}
        return {"enabled": True, **reflection}

    @app.get("/api/experience/state")
    async def api_experience_state():
        if experience is None:
            return {"enabled": False}
        return {"enabled": True, **experience}

    @app.get("/api/evaluation/state")
    async def api_evaluation_state():
        if evaluation is None:
            return {"enabled": False}
        return {"enabled": True, **evaluation}

    @app.get("/api/observation/state")
    async def api_observation_state():
        if observation is None:
            return {"enabled": False}
        return {"enabled": True, **observation}

    @app.get("/api/vision-evaluation/state")
    async def api_vision_evaluation_state():
        if vision_evaluation is None:
            return {"enabled": False}
        return {"enabled": True, **vision_evaluation}

    @app.get("/api/confirmation/state")
    async def api_confirmation_state():
        if confirmation is None:
            return {"enabled": False}
        return {"enabled": True, **confirmation}

    @app.post("/api/confirmation/approve")
    async def api_confirmation_approve(payload: dict):
        if confirmation_manager is None:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "confirmation manager 未接入"},
            )
        try:
            token = confirmation_manager.approve(
                payload.get("confirmation_id", "")
            )
            return {"ok": True, "token": token.model_dump(mode="json")}
        except ConfirmationError as exc:
            return JSONResponse(
                status_code=409,
                content={"ok": False, "error": str(exc)},
            )

    @app.post("/api/confirmation/reject")
    async def api_confirmation_reject(payload: dict):
        if confirmation_manager is None:
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "confirmation manager 未接入"},
            )
        try:
            request = confirmation_manager.reject(
                payload.get("confirmation_id", "")
            )
            return {"ok": True, "request": request.model_dump(mode="json")}
        except ConfirmationError as exc:
            return JSONResponse(
                status_code=409,
                content={"ok": False, "error": str(exc)},
            )

    @app.get("/api/executor-sandbox/state")
    async def api_executor_sandbox_state():
        if executor_sandbox is None:
            return {"enabled": False}
        return {"enabled": True, **executor_sandbox}

    @app.get("/api/agent-loop/state")
    async def api_agent_loop_state():
        if cognitive_loop is None:
            return {"enabled": False}
        return {"enabled": True, **cognitive_loop}

    @app.get("/api/architecture/state")
    async def api_architecture_state():
        if architecture is None:
            return {"enabled": False}
        return {"enabled": True, **architecture}

    @app.get("/api/long-horizon/state")
    async def api_long_horizon_state():
        if long_horizon is None:
            return {"enabled": False}
        return {"enabled": True, **long_horizon}

    @app.get("/api/goal-memory/state")
    async def api_goal_memory_state():
        if goal_memory is None:
            return {"enabled": False}
        return {"enabled": True, **goal_memory}

    @app.get("/api/planning-optimizer/state")
    async def api_planning_optimizer_state():
        if planning_optimizer is None:
            return {"enabled": False}
        return {"enabled": True, **planning_optimizer}

    @app.get("/api/failure-intelligence/state")
    async def api_failure_intelligence_state():
        if failure_intelligence is None:
            return {"enabled": False}
        return {"enabled": True, **failure_intelligence}

    @app.get("/api/goal-scheduler/state")
    async def api_goal_scheduler_state():
        if goal_scheduler is None:
            return {"enabled": False}
        return {"enabled": True, **goal_scheduler}

    @app.get("/api/environment/state")
    async def api_environment_state():
        if environment is None:
            return {"enabled": False}
        return {"enabled": True, **environment}

    @app.get("/api/world-model/state")
    async def api_world_model_state():
        if world_model is None:
            return {"enabled": False}
        return {"enabled": True, **world_model}

    @app.get("/api/environment-reasoning/state")
    async def api_environment_reasoning_state():
        if environment_reasoning is None:
            return {"enabled": False}
        return {"enabled": True, **environment_reasoning}

    @app.get("/api/environment-planning/state")
    async def api_environment_planning_state():
        if environment_planning is None:
            return {"enabled": False}
        return {"enabled": True, **environment_planning}

    @app.get("/api/decision-reference/state")
    async def api_decision_reference_state():
        if decision_reference is None:
            return {"enabled": False}
        return {"enabled": True, **decision_reference}

    @app.get("/api/human-alignment/state")
    async def api_human_alignment_state():
        if human_alignment is None:
            return {"enabled": False}
        return {"enabled": True, **human_alignment}

    @app.get("/api/memory-graph/state")
    async def api_memory_graph_state():
        if memory_graph is None:
            return {"enabled": False}
        return {"enabled": True, **memory_graph}

    @app.get("/api/semantic-memory/state")
    async def api_semantic_memory_state():
        if semantic_memory is None:
            return {"enabled": False}
        return {"enabled": True, **semantic_memory}

    @app.get("/api/maple-context/state")
    async def api_maple_context_state():
        if maple_context is None:
            return {"enabled": False}
        return {"enabled": True, **maple_context}

    @app.get("/api/maple-knowledge/state")
    async def api_maple_knowledge_state():
        if maple_knowledge is None:
            return {"enabled": False}
        return {"enabled": True, **maple_knowledge}

    @app.get("/api/perception/state")
    async def api_perception_state():
        if perception is None:
            return {"enabled": False}
        return {"enabled": True, **perception}

    @app.get("/api/quest-reasoning/state")
    async def api_quest_reasoning_state():
        if quest_reasoning is None:
            return {"enabled": False}
        return {"enabled": True, **quest_reasoning}

    @app.get("/api/perception-fusion/state")
    async def api_perception_fusion_state():
        if perception_fusion is None:
            return {"enabled": False}
        return {"enabled": True, **perception_fusion}

    @app.get("/api/reflex/state")
    async def api_reflex_state():
        if reflex is None:
            return {"enabled": False}
        return {"enabled": True, **reflex}

    @app.get("/api/vision-runtime/state")
    async def api_vision_runtime_state():
        if vision_runtime is None:
            return {"enabled": False}
        return {"enabled": True, **vision_runtime}

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

    @app.get("/api/quest-plan/state")
    async def api_quest_plan_state():
        if agent_loop is None:
            return {"enabled": False}
        plan = agent_loop.last_quest_plan
        return {
            "enabled": True,
            "plan": plan.model_dump(mode="json") if plan is not None else None,
            "validation": agent_loop.quest_plan_validation,
            "error": agent_loop.last_quest_plan_error or "",
        }

    @app.get("/api/execution/state")
    async def api_execution_state():
        if agent_loop is None:
            return {"enabled": False}
        last = agent_loop.last_execution
        return {
            "enabled": True,
            "mode": "MOCK ONLY",
            "status": last.status.value if last is not None else "IDLE",
            "message": last.message if last is not None else "",
            "history_count": len(agent_loop.execution_history),
        }

    @app.get("/api/window/state")
    async def api_window_state():
        info = runtime.last_window_info
        return {
            "enabled": True,
            "status": runtime.binding_status.value,
            "window": info.model_dump(mode="json") if info is not None else None,
            "mode": "READ ONLY",
        }

    @app.get("/api/vision-coordinate/state")
    async def api_vision_coordinate_state():
        if vision_worker is None or vision_worker.coordinate_mapper is None:
            return {"enabled": False}
        coordinate = vision_worker.coordinate_mapper.coordinate
        frame = vision_worker.latest_frame
        return {
            "enabled": True,
            "frame": (
                f"{frame.width}x{frame.height}"
                if frame is not None
                else f"{coordinate.frame_width}x{coordinate.frame_height}"
            ),
            "space": coordinate.target_space.value,
            "dpi": coordinate.dpi_scale,
            "offset": {"x": coordinate.offset_x, "y": coordinate.offset_y},
        }

    @app.get("/api/capture/state")
    async def api_capture_state():
        if vision_worker is None:
            return {"enabled": False}
        method = getattr(vision_worker.capture, "last_capture_method", None) or "-"
        frame = vision_worker.latest_frame
        if vision_worker.coordinate_mapper is not None:
            dpi = vision_worker.coordinate_mapper.coordinate.dpi_scale
        elif frame is not None:
            dpi = frame.dpi_scale
        else:
            dpi = 1.0
        return {
            "enabled": True,
            "mode": vision_worker.capture_mode,
            "method": method,
            "size": f"{frame.width}x{frame.height}" if frame is not None else "-",
            "dpi": dpi,
        }

    @app.get("/api/pipeline/state")
    async def api_pipeline_state():
        if pipeline_validator is None or pipeline_validator.last_result is None:
            return {"enabled": False}
        result = pipeline_validator.last_result
        return {
            "enabled": True,
            **result.status.model_dump(),
            "trace_id": result.trace_id,
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
