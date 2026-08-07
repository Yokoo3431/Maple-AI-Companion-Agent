"""启动 Phase 0 WebUI 控制台演示(纯本地,不触碰游戏)。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn

from maple_agent.agent import AgentLoop
from maple_agent.context import ContextBuilder
from maple_agent.decision import (
    DecisionContext,
    DecisionEngine,
    DecisionOption,
)
from maple_agent.events import EventBus
from maple_agent.executor import MockExecutorProvider
from maple_agent.fusion import FusionService
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.goal import Goal, MockGoalProvider, RuleBasedGoalSelector
from maple_agent.knowledge.evaluation import (
    EvaluationRunner,
    RetrievalBenchmark,
    load_retrieval_cases,
)
from maple_agent.knowledge.importer import ImportSource, run_import
from maple_agent.knowledge.retrieval import AliasIndex
from maple_agent.knowledge_graph import build_graph
from maple_agent.logging_setup import new_id, setup_logging
from maple_agent.planner import LLMPlannerProvider
from maple_agent.providers import (
    MockKnowledgeProvider,
    MockLLMProvider,
    MockOCRProvider,
    MockStorageProvider,
    MockVisionProvider,
)
from maple_agent.quest_planner import (
    QuestPlanner,
    QuestPlanValidator,
    QuestResolver,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.validation import VisionPipelineValidator
from maple_agent.vision import (
    MockCaptureProvider,
    ScreenshotPolicy,
    VisionWorker,
)
from maple_agent.vision.coordinate import (
    VisionAlignmentService,
    VisionCoordinateMapper,
)
from maple_agent.webui.app import create_app
from maple_agent.window import MockWindowDetector, WindowBindingService
from maple_agent.window.models import WindowInfo as BoundWindowInfo
from maple_agent.window.models import WindowRect as BoundWindowRect


def main() -> None:
    setup_logging("logs")
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    bound_window = BoundWindowInfo(
        title="MapleStory",
        process_name="MapleStory.exe",
        hwnd=12345,
        screen_rect=BoundWindowRect(left=100, top=100, width=1024, height=768),
        client_rect=BoundWindowRect(left=105, top=135, width=1016, height=735),
        dpi_scale=1.25,
    )
    detector = MockGameWindowDetector(
        WindowInfo(
            handle=1,
            title="MapleStory",
            process_name="MapleStory.exe",
            rect=WindowRect(left=0, top=0, width=800, height=600),
        )
    )
    providers = {
        "llm": MockLLMProvider(),
        "vision": MockVisionProvider(),
        "ocr": MockOCRProvider(),
        "storage": MockStorageProvider(),
        "knowledge": MockKnowledgeProvider(),
    }
    for provider in providers.values():
        provider.initialize()
    providers["knowledge"].load_dataset()
    eval_cases = load_retrieval_cases()
    graph = build_graph(providers["knowledge"])
    eval_result = EvaluationRunner.from_graph(graph).run(eval_cases)
    benchmark = RetrievalBenchmark(AliasIndex.from_graph(graph)).run(
        [case.query_text for case in eval_cases]
    )
    knowledge_eval = {
        "dataset_version": providers["knowledge"].dataset_version(),
        "entity_count": len(graph.maps) + len(graph.npcs) + len(graph.monsters) + len(graph.items),
        "benchmark_cases": eval_result.total_cases,
        "top1": eval_result.top1_accuracy,
        "top3": eval_result.top3_recall,
        "avg_ms": benchmark["avg_ms"],
    }
    import_bundle = run_import(
        {
            "maps": [
                {"map_id": 1, "name": "射手村", "aliases": ["Henesys"], "region": "维多利亚岛"},
                {"map_id": 2, "name": "魔法密林", "aliases": ["Ellinia"]},
            ],
            "npcs": [
                {"npc_id": 101, "name": "赫丽娜", "aliases": ["弓箭手教官"], "map_id": 1},
            ],
            "monsters": [
                {"monster_id": 100, "name": "绿水灵", "map_id": 1, "level": 4},
            ],
            "items": [
                {"item_id": 1, "name": "树液", "aliases": ["树液"]},
            ],
            "relations": [
                {
                    "source": "map",
                    "source_id": 1,
                    "target": "npc",
                    "target_id": 101,
                    "relation_type": "CONTAINS",
                },
                {
                    "source": "map",
                    "source_id": 1,
                    "target": "monster",
                    "target_id": 100,
                    "relation_type": "SPAWNS",
                },
            ],
        },
        source=ImportSource(source_id="external-demo", version="v1.0"),
        sessions_dir="sessions",
    )
    knowledge_import = {
        "source": import_bundle.result.source,
        "version": import_bundle.result.version,
        "maps": import_bundle.result.imported_maps,
        "npcs": import_bundle.result.imported_npcs,
        "monsters": import_bundle.result.imported_monsters,
        "items": import_bundle.result.imported_items,
        "warnings": import_bundle.result.warnings,
        "valid": import_bundle.validation.valid,
    }
    vision_capture = MockCaptureProvider(
        bus=bus,
        policy=ScreenshotPolicy(save_enabled=True, max_images=20),
        sessions_dir="sessions",
        window=WindowInfo(
            handle=1,
            title="MapleStory",
            process_name="MapleStory.exe",
            rect=WindowRect(left=0, top=0, width=800, height=600),
        ),
    )
    fusion = FusionService(
        knowledge=providers["knowledge"],
        graph=build_graph(providers["knowledge"]),
        sessions_dir="sessions",
    )
    vision_worker = VisionWorker(
        vision_capture,
        bus,
        interval=0.5,
        ocr=MockOCRProvider(bus=bus, text="射手村"),
        fusion=fusion,
        context_builder=ContextBuilder(knowledge=providers["knowledge"]),
        runtime_state_fn=lambda: runtime.state.value,
    )
    llm = MockLLMProvider(
        reply='{"plan_id":"p1","summary":"观察并分析当前状态","confidence":0.9,'
        '"steps":[{"step_id":"s1","action":"observe","target":"window",'
        '"expected_outcome":"screen frame"},{"step_id":"s2","action":"analyze",'
        '"target":"context","expected_outcome":"world state"}]}'
    )
    llm.initialize()
    planner = LLMPlannerProvider(llm=llm, sessions_dir="sessions")
    goal_provider = MockGoalProvider(
        goals=[
            Goal(
                goal_id="goal-quest-1",
                goal_type="QUEST",
                title="新手教学",
                priority=10,
                source="quest:1",
            ),
            Goal(
                goal_id="goal-level-1",
                goal_type="LEVELING",
                title="提升到 5 级",
                priority=5,
                source="user",
            ),
        ]
    )
    agent_loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge=providers["knowledge"]),
        planner=planner,
        sessions_dir="sessions",
        goal_provider=goal_provider,
        goal_selector=RuleBasedGoalSelector(),
        quest_resolver=QuestResolver(providers["knowledge"]),
        quest_planner=QuestPlanner(providers["knowledge"]),
        quest_plan_validator=QuestPlanValidator(),
        executor=MockExecutorProvider(),
    )
    pipeline_validator = VisionPipelineValidator(
        detector=MockWindowDetector(bound_window),
        capture=MockCaptureProvider(width=1016, height=735),
        knowledge=providers["knowledge"],
        ocr=MockOCRProvider(text="射手村"),
    )
    pipeline_validator.capture.initialize()
    pipeline_validator.ocr.initialize()
    pipeline_validator.validate_once(trace_id=new_id())
    agent_loop.run_once(
        vision_state=None,
        world_state=None,
        runtime_state=runtime.state.value,
        trace_id=new_id(),
    )  # 演示:执行一轮只读循环(仅 Mock LLM,不执行动作)
    goal = goal_provider.get_active_goal()
    quest_plan = agent_loop.last_quest_plan
    last_context = agent_loop.last_context
    decision_options: list[DecisionOption] = []
    if quest_plan is not None:
        for index, step in enumerate(quest_plan.steps):
            decision_options.append(
                DecisionOption(
                    decision_id=f"decision-{index + 1}",
                    action=step.action.value,
                    target=step.target or step.description,
                    expected_result=step.expected_result,
                    confidence=(
                        0.9 if index == 0 else max(0.5, 0.9 - index * 0.15)
                    ),
                    risk=(
                        0.2
                        if step.action.value in ("TALK", "ANALYZE", "MOVE_HINT")
                        else 0.4
                    ),
                    reason=f"来自任务计划步骤 {index + 1}: {step.description}",
                )
            )
    decision_engine = DecisionEngine(sessions_dir="sessions")
    decision_result = decision_engine.decide(
        DecisionContext(
            world_state=last_context.world_state if last_context else None,
            knowledge_state=(
                last_context.knowledge_state if last_context else None
            ),
            goal=goal,
            quest_plan=quest_plan,
            options=decision_options,
        ),
        trace_id=new_id(),
    )
    decision = {
        "goal": goal.model_dump(mode="json") if goal is not None else None,
        "result": decision_result.model_dump(mode="json"),
    }
    app = create_app(
        runtime=runtime,
        bus=bus,
        providers=providers,
        detector=detector,
        vision_worker=vision_worker,
        knowledge=providers.get("knowledge"),
        context_builder=ContextBuilder(knowledge=providers["knowledge"]),
        planner=planner,
        agent_loop=agent_loop,
        goal_provider=goal_provider,
        pipeline_validator=pipeline_validator,
        knowledge_eval=knowledge_eval,
        knowledge_import=knowledge_import,
        decision=decision,
    )
    runtime.start()  # 启动后默认 READY,禁止自动进入 RUNNING
    runtime.bind_window(bound_window, trace_id=new_id())
    bound = WindowBindingService().bind(bound_window, trace_id=new_id())
    coordinate = VisionAlignmentService().align(
        frame_width=1280,
        frame_height=720,
        bound=bound,
    )
    vision_worker.coordinate_mapper = VisionCoordinateMapper(coordinate, bound)
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


if __name__ == "__main__":
    main()
