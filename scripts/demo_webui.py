"""启动 Phase 0 WebUI 控制台演示(纯本地,不触碰游戏)。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn

from maple_agent.action_plan import ActionPlanner
from maple_agent.agent import AgentLoop
from maple_agent.agent_loop import AgentLoopOrchestrator
from maple_agent.architecture import (
    ARCHITECTURE_VERSION,
    CORE_MODULES,
    SAFETY_MODE,
    TRACE_SCHEMA_VERSION,
)
from maple_agent.confirmation import (
    ConfirmationManager,
    ConfirmationStatus,
    HumanConfirmationGate,
)
from maple_agent.context import ContextBuilder
from maple_agent.decision import (
    DecisionContext,
    DecisionEngine,
    DecisionOption,
)
from maple_agent.evaluation import EvaluationBenchmark, EvaluationReport
from maple_agent.events import EventBus
from maple_agent.execution import ExecutionOrchestrator
from maple_agent.executor import MockExecutorProvider
from maple_agent.executor_sandbox import (
    LimitedExecutorSandbox,
    SandboxExecutionRequest,
)
from maple_agent.experience import (
    ExperienceRecord,
    ExperienceRetriever,
    ExperienceStore,
)
from maple_agent.fusion import FusionService
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.goal import Goal, MockGoalProvider, RuleBasedGoalSelector
from maple_agent.goal_memory import (
    GoalExperienceRecord,
    GoalExperienceRetriever,
    GoalExperienceStore,
    PlanningOptimizer,
    save_goal_memory_trace,
)
from maple_agent.knowledge.evaluation import (
    EvaluationRunner,
    RetrievalBenchmark,
    load_retrieval_cases,
)
from maple_agent.knowledge.importer import ImportSource, run_import
from maple_agent.knowledge.retrieval import AliasIndex
from maple_agent.knowledge_graph import build_graph
from maple_agent.logging_setup import new_id, setup_logging
from maple_agent.observation import (
    ObservationAdapter,
    ObservationCollector,
    ObservationValidator,
)
from maple_agent.planner import LLMPlannerProvider
from maple_agent.planning_optimizer import (
    AdaptivePlannerOptimizer,
    TaskGraphAnalyzer,
    save_planning_optimization_trace,
)
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
from maple_agent.reflection import (
    ReflectionEngine,
    ReflectionMemory,
    ReflectionTrigger,
)
from maple_agent.reflection.models import FailureType, ReflectionResult
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import (
    LongHorizonGoal,
    Milestone,
    RecoveryPlanner,
    TaskDecomposer,
    TaskExecutionStateManager,
    save_task_planning_trace,
)
from maple_agent.validation import VisionPipelineValidator
from maple_agent.vision import (
    MockCaptureProvider,
    Observation,
    ScreenshotPolicy,
    VisionWorker,
)
from maple_agent.vision.coordinate import (
    VisionAlignmentService,
    VisionCoordinateMapper,
)
from maple_agent.vision_eval import VisionEvaluator
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
    world_state = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手村",
                normalized_value="射手村",
                confidence=0.95,
                source="mock",
            )
        ],
        trace_id=new_id(),
    )
    knowledge_state = ContextBuilder(
        knowledge=providers["knowledge"]
    ).build(
        vision_state=vision_worker.latest_vision,
        world_state=world_state,
        runtime_state=runtime.state.value,
        trace_id=new_id(),
    ).knowledge_state
    loop_trace_id = new_id()
    decision_options: list[DecisionOption] = []
    experience_store = ExperienceStore(
        [
            ExperienceRecord(
                experience_id="exp-1",
                context_snapshot={"map_name": "射手村"},
                goal="新手教学",
                action="TALK",
                result="任务已接受",
                reflection="对话成功",
                success=True,
                resolution="直接与 NPC 对话",
            ),
            ExperienceRecord(
                experience_id="exp-2",
                context_snapshot={"map_name": "射手村"},
                goal="新手教学",
                action="DEFEAT",
                result="执行失败",
                reflection="等级不足",
                success=False,
                failure_type="EXECUTION_FAILED",
                resolution="提升等级后再挑战",
            ),
            ExperienceRecord(
                experience_id="exp-3",
                context_snapshot={"map_name": "射手村"},
                goal="新手教学",
                action="COLLECT",
                result="收集完成",
                reflection="收集成功",
                success=True,
                resolution="按地图引导收集",
            ),
        ]
    )
    experience_retriever = ExperienceRetriever(store=experience_store)
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
    decision_engine = DecisionEngine(
        sessions_dir="sessions",
        experience=experience_retriever,
    )
    decision_result = decision_engine.decide(
        DecisionContext(
            world_state=world_state,
            knowledge_state=knowledge_state,
            goal=goal,
            quest_plan=quest_plan,
            options=decision_options,
        ),
        trace_id=loop_trace_id,
    )
    action_planner = ActionPlanner(sessions_dir="sessions")
    action_plan = action_planner.plan(
        decision_result,
        world_state=world_state,
        knowledge_state=knowledge_state,
        goal_id=goal.goal_id if goal is not None else None,
        trace_id=loop_trace_id,
    )
    decision = {
        "goal": goal.model_dump(mode="json") if goal is not None else None,
        "result": decision_result.model_dump(mode="json"),
    }
    action_plan_data = {
        "plan": action_plan.model_dump(mode="json"),
    }
    orchestrator = ExecutionOrchestrator(sessions_dir="sessions")
    orchestration_state = orchestrator.run(
        action_plan,
        trace_id=loop_trace_id,
    )
    execution_orchestration = {
        "plan": f"{action_plan.action} {action_plan.target}".strip(),
        "state": orchestration_state.model_dump(mode="json"),
    }
    reflection_memory = ReflectionMemory()
    reflection_engine = ReflectionEngine(
        memory=reflection_memory,
        trigger=ReflectionTrigger(),
        sessions_dir="sessions",
    )
    last_record = (
        orchestrator.last_records[-1] if orchestrator.last_records else None
    )
    reflection_result = reflection_engine.reflect(
        execution=last_record.result,
        feedback=last_record.feedback,
        world_state=world_state,
        expected_result=action_plan.expected_result,
        trace_id=loop_trace_id,
    )
    reflection = {
        "result": reflection_result.model_dump(mode="json"),
        "trigger": ReflectionTrigger().evaluate(reflection_result).value,
        "state": reflection_memory.state.model_dump(mode="json"),
    }
    experience_data = {
        "total": experience_store.count(),
        "success_count": len(experience_store.successful_recovery()),
        "failure_count": len(experience_store.similar_failure()),
        "last_query": experience_retriever.last_query,
        "last_results": [
            {
                "experience_id": record.experience_id,
                "action": record.action,
                "success": record.success,
            }
            for record in experience_retriever.last_results
        ],
    }
    observation_ocr = MockOCRProvider(text="射手村", confidence=0.95)
    observation_ocr.initialize()
    observation_adapter = ObservationAdapter(
        ocr=observation_ocr,
        sessions_dir="sessions",
    )
    observation_collector = ObservationCollector(
        observation_adapter,
        knowledge=providers["knowledge"],
        sessions_dir="sessions",
    )
    observation_state = observation_collector.collect_and_save(
        image_bytes=b"mock-image-bytes",
        source="mock",
        trace_id=loop_trace_id,
    )
    observation_validation = ObservationValidator().validate(
        observation_collector.last_frame
    )
    observation = {
        "frame": observation_collector.last_frame.model_dump(mode="json"),
        "state": observation_state.model_dump(mode="json"),
        "validation": observation_validation.model_dump(mode="json"),
    }
    vision_evaluator = VisionEvaluator(
        knowledge=providers["knowledge"],
        sessions_dir="sessions",
    )
    vision_eval_result = vision_evaluator.evaluate(
        frame=observation_collector.last_frame,
        state=observation_state,
        trace_id=loop_trace_id,
    )
    vision_evaluation = {
        "result": vision_eval_result.model_dump(mode="json"),
    }
    confirmation_manager = ConfirmationManager(sessions_dir="sessions")
    confirmation_request = HumanConfirmationGate().create_request(
        action_plan=action_plan,
        vision_result=vision_eval_result,
        decision_result=decision_result,
        trace_id=loop_trace_id,
    )
    confirmation_manager.create(confirmation_request)
    permission_token = None
    if confirmation_request.status is ConfirmationStatus.PENDING:
        permission_token = confirmation_manager.approve(
            confirmation_request.confirmation_id
        )
    confirmation = {
        "request": confirmation_request.model_dump(mode="json"),
        "token": (
            permission_token.model_dump(mode="json")
            if permission_token is not None
            else None
        ),
    }
    executor_sandbox = LimitedExecutorSandbox(sessions_dir="sessions")
    sandbox_request = SandboxExecutionRequest(
        execution_id=new_id(),
        trace_id=loop_trace_id,
        permission_token_id=(
            permission_token.token_id if permission_token is not None else ""
        ),
        action=action_plan.action,
        target=action_plan.target,
        scope=permission_token.scope if permission_token is not None else "",
    )
    sandbox_result = executor_sandbox.execute(
        request=sandbox_request,
        token=permission_token,
        trace_id=loop_trace_id,
    )
    executor_sandbox_data = {
        "request": sandbox_request.model_dump(mode="json"),
        "result": sandbox_result.model_dump(mode="json"),
    }
    evaluation_benchmark = EvaluationBenchmark(sessions_dir="sessions")
    evaluation_metrics = evaluation_benchmark.benchmark()
    evaluation_report_text = EvaluationReport().generate(
        evaluation_benchmark.last_result,
        evaluation_metrics,
    )
    evaluation = {
        "trace_count": evaluation_benchmark.last_trace_count,
        "metrics": evaluation_metrics.model_dump(mode="json"),
        "last_result": (
            evaluation_benchmark.last_result.model_dump(mode="json")
            if evaluation_benchmark.last_result is not None
            else None
        ),
        "report": evaluation_report_text,
    }
    agent_loop_orchestrator = AgentLoopOrchestrator(
        observation_collector=observation_collector,
        vision_evaluator=vision_evaluator,
        decision_engine=decision_engine,
        action_planner=action_planner,
        confirmation_manager=confirmation_manager,
        confirmation_gate=HumanConfirmationGate(),
        sandbox=executor_sandbox,
        reflection_engine=reflection_engine,
        evaluation_benchmark=evaluation_benchmark,
        sessions_dir="sessions",
        knowledge=providers["knowledge"],
    )
    agent_loop_context = agent_loop_orchestrator.run(
        image_bytes=b"mock-image-bytes",
        goal=goal,
        auto_approve=True,
        trace_id=new_id(),
    )
    agent_loop_data = {
        "context": agent_loop_context.model_dump(mode="json"),
        "trace": agent_loop_orchestrator.last_trace.model_dump(mode="json"),
        "validation": agent_loop_orchestrator.last_validation.model_dump(
            mode="json"
        ),
    }
    architecture_data = {
        "version": ARCHITECTURE_VERSION,
        "module_count": len(CORE_MODULES),
        "trace_version": TRACE_SCHEMA_VERSION,
        "safety_mode": SAFETY_MODE,
    }
    horizon_goal = LongHorizonGoal(
        goal_id="goal-horizon-1",
        description="完成新手任务链",
        priority=10,
        constraints=["只读观察", "Mock Only"],
        success_condition="提交任务并验证完成",
        milestones=[
            Milestone(
                milestone_id="ms-1",
                title="找到 NPC",
                order=0,
                task_ids=["task-1"],
            ),
            Milestone(
                milestone_id="ms-2",
                title="接受任务",
                order=1,
                task_ids=["task-2"],
            ),
            Milestone(
                milestone_id="ms-3",
                title="收集材料",
                order=2,
                task_ids=["task-3", "task-4"],
            ),
            Milestone(
                milestone_id="ms-4",
                title="提交任务",
                order=3,
                task_ids=["task-5"],
            ),
        ],
    )
    task_graph = TaskDecomposer().decompose(horizon_goal)
    task_manager = TaskExecutionStateManager(task_graph)
    task_manager.mark_completed("task-1")
    task_manager.mark_completed("task-2")
    recovery_reflection = ReflectionResult(
        reflection_id="refl-recovery",
        execution_id="exec-recovery",
        success=False,
        failure_type=FailureType.EXECUTION_FAILED,
        failure_reason="模拟执行失败",
        confidence=0.5,
        next_action="replan",
        trace_id=loop_trace_id,
    )
    recovery_plan = RecoveryPlanner().plan(
        recovery_reflection,
        goal_id=horizon_goal.goal_id,
        task_id="task-3",
    )
    save_task_planning_trace(
        "sessions",
        loop_trace_id,
        goal=horizon_goal,
        graph=task_graph,
        state=task_manager.snapshot(),
        recovery=recovery_plan,
    )
    long_horizon_data = {
        "goal": horizon_goal.model_dump(mode="json"),
        "graph": task_graph.model_dump(mode="json"),
        "state": task_manager.snapshot().model_dump(mode="json"),
        "recovery": recovery_plan.model_dump(mode="json"),
        "progress": task_manager.progress(),
    }
    goal_experience_store = GoalExperienceStore(
        [
            GoalExperienceRecord(
                experience_id="gxp-1",
                goal_type="QUEST",
                goal_description="完成新手任务链",
                successful_path=[
                    "task-1",
                    "task-2",
                    "task-3",
                    "task-4",
                    "task-5",
                ],
                failed_points=[],
                task_pattern=[
                    "task-1",
                    "task-2",
                    "task-3",
                    "task-4",
                    "task-5",
                ],
                duration_estimate=600,
                success=True,
                confidence=0.9,
            ),
            GoalExperienceRecord(
                experience_id="gxp-2",
                goal_type="QUEST",
                goal_description="收集材料失败案例",
                successful_path=["task-3"],
                failed_points=["task-3"],
                task_pattern=["task-3", "task-4"],
                duration_estimate=300,
                success=False,
                confidence=0.6,
            ),
        ]
    )
    goal_retriever = GoalExperienceRetriever(goal_experience_store)
    retrieved_experience = goal_retriever.retrieve(
        current_goal=horizon_goal,
        task_graph=task_graph,
        goal_type="QUEST",
    )
    planning_optimizer = PlanningOptimizer()
    optimized_graph = planning_optimizer.optimize(
        graph=task_graph,
        experience=(
            retrieved_experience[0] if retrieved_experience else None
        ),
    )
    save_goal_memory_trace(
        "sessions",
        loop_trace_id,
        goal=horizon_goal,
        retrieved=retrieved_experience,
        similarity_score=goal_retriever.last_best_score,
        optimization=optimized_graph,
    )
    goal_memory_data = {
        "goal": horizon_goal.model_dump(mode="json"),
        "retrieved": [
            record.model_dump(mode="json")
            for record in retrieved_experience
        ],
        "similarity": goal_retriever.last_best_score,
        "optimization": optimized_graph.model_dump(mode="json"),
    }
    planning_optimizer = AdaptivePlannerOptimizer()
    planning_analysis = TaskGraphAnalyzer().analyze(task_graph)
    optimized_reference, planning_score = planning_optimizer.optimize(
        graph=task_graph,
        experience=(
            retrieved_experience[0] if retrieved_experience else None
        ),
        analysis=planning_analysis,
    )
    save_planning_optimization_trace(
        "sessions",
        loop_trace_id,
        goal_id=horizon_goal.goal_id,
        original_plan=task_graph.model_dump(mode="json"),
        analysis=planning_optimizer.last_analysis,
        optimized_plan=optimized_reference,
        score=planning_score,
    )
    planning_optimizer_data = {
        "goal_id": horizon_goal.goal_id,
        "analysis": planning_optimizer.last_analysis.model_dump(mode="json"),
        "score": planning_score.model_dump(mode="json"),
        "optimized": optimized_reference.model_dump(mode="json"),
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
        action_plan=action_plan_data,
        execution_orchestration=execution_orchestration,
        reflection=reflection,
        experience=experience_data,
        evaluation=evaluation,
        observation=observation,
        vision_evaluation=vision_evaluation,
        confirmation_manager=confirmation_manager,
        confirmation=confirmation,
        executor_sandbox=executor_sandbox_data,
        cognitive_loop=agent_loop_data,
        architecture=architecture_data,
        long_horizon=long_horizon_data,
        goal_memory=goal_memory_data,
        planning_optimizer=planning_optimizer_data,
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
