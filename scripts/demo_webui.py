"""启动 Phase 0 WebUI 控制台演示(纯本地,不触碰游戏)。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn

from maple_agent.agent import AgentLoop
from maple_agent.context import ContextBuilder
from maple_agent.events import EventBus
from maple_agent.executor import MockExecutorProvider
from maple_agent.fusion import FusionService
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.goal import Goal, MockGoalProvider, RuleBasedGoalSelector
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
from maple_agent.window import WindowBindingService
from maple_agent.window.models import WindowInfo as BoundWindowInfo
from maple_agent.window.models import WindowRect as BoundWindowRect


def main() -> None:
    setup_logging("logs")
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
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
    fusion = FusionService(knowledge=providers["knowledge"])
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
    )
    runtime.start()  # 启动后默认 READY,禁止自动进入 RUNNING
    bound_window = BoundWindowInfo(
        title="MapleStory",
        process_name="MapleStory.exe",
        hwnd=12345,
        screen_rect=BoundWindowRect(left=100, top=100, width=1024, height=768),
        client_rect=BoundWindowRect(left=105, top=135, width=1016, height=735),
        dpi_scale=1.25,
    )
    runtime.bind_window(bound_window, trace_id=new_id())
    bound = WindowBindingService().bind(bound_window, trace_id=new_id())
    coordinate = VisionAlignmentService().align(
        frame_width=1280,
        frame_height=720,
        bound=bound,
    )
    vision_worker.coordinate_mapper = VisionCoordinateMapper(coordinate, bound)
    agent_loop.run_once(
        vision_state=None,
        world_state=None,
        runtime_state=runtime.state.value,
        trace_id=new_id(),
    )  # 演示:执行一轮只读循环(仅 Mock LLM,不执行动作)
    uvicorn.run(app, host="127.0.0.1", port=8080, log_level="info")


if __name__ == "__main__":
    main()
