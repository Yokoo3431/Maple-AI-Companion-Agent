"""启动 Phase 0 WebUI 控制台演示(纯本地,不触碰游戏)。"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import uvicorn

from maple_agent.action_plan import ActionPlanner
from maple_agent.action_proposal import (
    ActionProposalMapper,
    ActionProposalReference,
    ActionProposalValidator,
    ActionType,
    save_action_proposal_trace,
)
from maple_agent.action_verification import (
    ActionOutcomeValidator,
    ActionOutcomeVerifier,
    save_action_verification_trace,
)
from maple_agent.agent import AgentLoop
from maple_agent.agent_loop import AgentLoopOrchestrator
from maple_agent.architecture import (
    ARCHITECTURE_VERSION,
    CORE_MODULES,
    SAFETY_MODE,
    TRACE_SCHEMA_VERSION,
)
from maple_agent.behavior import (
    BehaviorPlanner,
    BehaviorValidator,
    save_behavior_trace,
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
from maple_agent.decision_reference import (
    DecisionReferenceBuilder,
    DecisionReferenceValidator,
    DecisionRiskIntegrator,
    DecisionScorer,
    save_decision_reference_trace,
)
from maple_agent.environment import (
    EnvironmentCollector,
    EnvironmentSnapshotManager,
    EnvironmentStateManager,
    EnvironmentValidator,
    save_environment_trace,
)
from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_planning import (
    EnvironmentAwarePlanner,
    EnvironmentPlanningValidator,
    EnvironmentRiskAdapter,
    save_environment_planning_trace,
)
from maple_agent.environment_reasoning import (
    EnvironmentOpportunityDetector,
    EnvironmentReasoner,
    EnvironmentReasoningValidator,
    EnvironmentRiskAnalyzer,
    save_environment_reasoning_trace,
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
from maple_agent.failure_intelligence import (
    FailureAnalyzer,
    FailureExtractor,
    FailurePatternMatcher,
    FailurePatternRecord,
    FailurePredictor,
    save_failure_intelligence_trace,
)
from maple_agent.fusion import FusionService
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.game_state import (
    EntityStateReference,
    GameStateExtractor,
    GameStateReference,
    GameStateValidator,
    MapStateReference,
    PlayerStateReference,
    QuestStateSnapshot,
    save_game_state_trace,
)
from maple_agent.goal import Goal, MockGoalProvider, RuleBasedGoalSelector
from maple_agent.goal_memory import (
    GoalExperienceRecord,
    GoalExperienceRetriever,
    GoalExperienceStore,
    PlanningOptimizer,
    save_goal_memory_trace,
)
from maple_agent.goal_scheduler import (
    GoalScheduleRecord,
    MultiGoalScheduler,
    save_goal_schedule_trace,
)
from maple_agent.human_alignment import (
    FeedbackAction,
    HumanAlignmentAligner,
    HumanAlignmentValidator,
    HumanFeedback,
    save_human_alignment_trace,
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
from maple_agent.maple_context import (
    MapleContextBuilder,
    MapleContextValidator,
    save_maple_context_trace,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeGraph,
    MapleKnowledgeRetriever,
    MapleKnowledgeValidator,
    load_demo_knowledge,
    save_maple_knowledge_trace,
)
from maple_agent.memory_association import (
    AssociationReasoner,
    SemanticAssociationEngine,
    SemanticAssociationValidator,
    save_semantic_memory_trace,
)
from maple_agent.memory_graph import (
    MemoryConsolidator,
    MemoryGraphValidator,
    MemoryIndex,
    MemoryRelationBuilder,
    MemoryRetriever,
    save_memory_graph_trace,
)
from maple_agent.navigation import (
    NavigationPlanner,
    NavigationValidator,
    save_navigation_trace,
)
from maple_agent.navigation.models import (
    NavigationReference,
    RouteStep,
    RouteStepType,
)
from maple_agent.observation import (
    ObservationAdapter,
    ObservationCollector,
    ObservationValidator,
)
from maple_agent.perception import (
    MaplePerceptionBinder,
    PerceptionValidator,
    save_perception_trace,
)
from maple_agent.perception import (
    MockVisionProvider as PerceptionMockVisionProvider,
)
from maple_agent.perception_fusion import (
    PerceptionFusionEngine,
    PerceptionFusionValidator,
    save_perception_fusion_trace,
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
from maple_agent.quest_reasoning import (
    GoalReference,
    GoalType,
    QuestGoalReference,
    QuestReasoningValidator,
    save_quest_reasoning_trace,
)
from maple_agent.quest_reasoning import (
    QuestPlanner as QuestIntelligencePlanner,
)
from maple_agent.real_vision import (
    RealVisionBenchmarkResult,
    build_real_vision_readiness,
)
from maple_agent.recovery import (
    FailureDetector,
    RecoveryValidator,
    save_recovery_trace,
)
from maple_agent.recovery import (
    RecoveryPlanner as FailureRecoveryPlanner,
)
from maple_agent.reflection import (
    ReflectionEngine,
    ReflectionMemory,
    ReflectionTrigger,
)
from maple_agent.reflection.models import FailureType, ReflectionResult
from maple_agent.reflex import (
    HpMpReference,
    ReflexReference,
    ReflexStateDetector,
    ReflexStateType,
    ReflexThresholds,
    ReflexValidator,
    save_reflex_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_gate import (
    SafetyEvaluator,
    SafetyGateValidator,
    save_safety_gate_trace,
)
from maple_agent.spatial_world import (
    SpatialMapStore,
    SpatialWorldBuilder,
    SpatialWorldValidator,
    load_demo_spatial_map,
    save_spatial_world_trace,
)
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
from maple_agent.vision_runtime import (
    GameStateParser,
    MockScreenshotProvider,
    VisionDetector,
    VisionRuntimeValidator,
    save_vision_runtime_trace,
)
from maple_agent.vision_runtime import (
    MockOCRProvider as VisionRuntimeMockOCR,
)
from maple_agent.webui.app import create_app
from maple_agent.window import MockWindowDetector, WindowBindingService
from maple_agent.window.models import WindowInfo as BoundWindowInfo
from maple_agent.window.models import WindowRect as BoundWindowRect
from maple_agent.world_knowledge import (
    WorldKnowledgeImporter,
    WorldKnowledgeResolver,
    WorldKnowledgeValidator,
    load_demo_world_map,
    save_world_knowledge_trace,
)
from maple_agent.world_model import (
    EnvironmentEventDetector,
    EnvironmentHistoryManager,
    EnvironmentTransitionDetector,
    WorldStatePredictor,
    save_world_model_trace,
)


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
    failure_pattern_store = [
        FailurePatternRecord(
            pattern_id="fp-1",
            failure_type="EXECUTION_FAILED",
            trigger_conditions=["confidence=0.5"],
            context_snapshot={
                "confidence": 0.5,
                "failed_task": "task-3",
            },
            affected_tasks=["task-3"],
            root_cause="前置条件未满足",
            resolution_strategy="重试并检查前置条件",
            success_rate=0.3,
            confidence=0.7,
        )
    ]
    failure_extractor = FailureExtractor()
    new_pattern = failure_extractor.extract(
        reflection=recovery_reflection,
        execution_trace=None,
        task_planning_trace={"current_task": "task-3", "progress": 0.4},
    )
    all_patterns = failure_pattern_store + (
        [new_pattern] if new_pattern is not None else []
    )
    failure_matcher = FailurePatternMatcher()
    match_results = failure_matcher.match(
        patterns=all_patterns,
        current_task_graph=task_graph,
        current_context={
            "confidence": 0.5,
            "failed_task": "task-3",
        },
        failure_type="EXECUTION_FAILED",
    )
    top_match = match_results[0] if match_results else None
    top_pattern = (
        next(
            (
                pattern
                for pattern in all_patterns
                if pattern.pattern_id == top_match.pattern_id
            ),
            None,
        )
        if top_match is not None
        else None
    )
    failure_analyzer = FailureAnalyzer()
    root_cause_analysis = (
        failure_analyzer.analyze(
            pattern=top_pattern,
            match_score=top_match.score,
        )
        if top_pattern is not None
        else None
    )
    failure_predictor = FailurePredictor()
    prevention_reference = failure_predictor.build_prevention_reference(
        task_graph=task_graph,
        patterns=all_patterns,
        analysis=root_cause_analysis,
    )
    save_failure_intelligence_trace(
        "sessions",
        loop_trace_id,
        source_trace=loop_trace_id,
        failure_pattern=top_pattern,
        analysis=root_cause_analysis,
        prevention_reference=prevention_reference,
    )
    failure_intelligence_data = {
        "failure_count": len(all_patterns),
        "top_pattern": (
            top_pattern.model_dump(mode="json")
            if top_pattern is not None
            else None
        ),
        "analysis": (
            root_cause_analysis.model_dump(mode="json")
            if root_cause_analysis is not None
            else None
        ),
        "prevention": prevention_reference.model_dump(mode="json"),
    }
    schedule_goal_b = LongHorizonGoal(
        goal_id="goal-b",
        description="提升到 5 级",
        priority=8,
        success_condition="达到 5 级",
        milestones=[
            Milestone(
                milestone_id="ms-b1",
                title="击败怪物",
                order=0,
                task_ids=["task-b1"],
            )
        ],
    )
    schedule_goal_c = LongHorizonGoal(
        goal_id="goal-c",
        description="收集树液道具",
        priority=5,
        success_condition="收集 10 个树液",
        milestones=[
            Milestone(
                milestone_id="ms-c1",
                title="收集道具",
                order=0,
                task_ids=["task-c1"],
            )
        ],
    )
    goal_scheduler = MultiGoalScheduler()
    schedule_records = [
        GoalScheduleRecord(
            schedule_id="sch-a",
            goal_id=horizon_goal.goal_id,
            priority=10,
            urgency=0.3,
            importance=0.9,
            resource_cost=0.4,
            deadline=datetime.now(UTC) + timedelta(days=5),
            confidence=0.8,
        ),
        GoalScheduleRecord(
            schedule_id="sch-b",
            goal_id=schedule_goal_b.goal_id,
            priority=8,
            urgency=0.7,
            importance=0.7,
            resource_cost=0.7,
            dependency=horizon_goal.goal_id,
            deadline=datetime.now(UTC) + timedelta(days=1),
            confidence=0.6,
        ),
        GoalScheduleRecord(
            schedule_id="sch-c",
            goal_id=schedule_goal_c.goal_id,
            priority=5,
            urgency=0.5,
            importance=0.4,
            resource_cost=0.3,
            deadline=datetime.now(UTC) + timedelta(days=3),
            confidence=0.5,
        ),
    ]
    schedule_result = goal_scheduler.schedule(
        goals=[horizon_goal, schedule_goal_b, schedule_goal_c],
        records=schedule_records,
    )
    save_goal_schedule_trace(
        "sessions",
        loop_trace_id,
        goals=[horizon_goal, schedule_goal_b, schedule_goal_c],
        priority_scores=goal_scheduler.last_priorities,
        schedule=schedule_result,
        conflicts=goal_scheduler.last_conflicts,
    )
    goal_scheduler_data = {
        "goal_count": len(schedule_records),
        "priority_scores": [
            score.model_dump(mode="json")
            for score in goal_scheduler.last_priorities
        ],
        "schedule": schedule_result.model_dump(mode="json"),
        "conflicts": [
            conflict.model_dump(mode="json")
            for conflict in goal_scheduler.last_conflicts
        ],
    }
    environment_collector = EnvironmentCollector(
        knowledge=providers["knowledge"],
    )
    environment_state = environment_collector.collect(
        observation_state=observation_state,
        knowledge_state=knowledge_state,
        trace_id=loop_trace_id,
    )
    environment_manager = EnvironmentStateManager()
    environment_manager.update(environment_state)
    environment_snapshot = EnvironmentSnapshotManager().capture(
        before=None,
        after=environment_state,
        trace_id=loop_trace_id,
    )
    environment_validation = EnvironmentValidator().validate(
        environment_state
    )
    save_environment_trace(
        "sessions",
        loop_trace_id,
        environment_state=environment_state,
        snapshot=environment_snapshot,
        validation=environment_validation,
    )
    environment_data = {
        "state": environment_state.model_dump(mode="json"),
        "snapshot": environment_snapshot.model_dump(mode="json"),
        "validation": environment_validation.model_dump(mode="json"),
    }
    after_environment_state = EnvironmentState(
        environment_id="env-after-2",
        location="魔法密林",
        visible_entities=["爱丽丝"],
        resources=["树液"],
        conditions={
            "observed_count": 2,
            "entity_count": 1,
            "confidence": 0.85,
        },
        world_context="当前位于 魔法密林,可见实体: 爱丽丝,观察 2 条",
        confidence=0.85,
    )
    world_history = EnvironmentHistoryManager()
    world_history.append(environment_state)
    world_history.append(after_environment_state)
    world_transition = EnvironmentTransitionDetector().detect(
        before=environment_state,
        after=after_environment_state,
    )
    world_events = EnvironmentEventDetector().detect(
        transition=world_transition,
    )
    for event in world_events:
        world_history.add_event(event)
    world_prediction = WorldStatePredictor().predict(
        history=world_history.history,
    )
    save_world_model_trace(
        "sessions",
        loop_trace_id,
        history=world_history.history,
        transition=world_transition,
        events=world_events,
        prediction=world_prediction,
    )
    world_model_data = {
        "history_count": len(world_history.history.snapshots),
        "events": [
            event.model_dump(mode="json") for event in world_events
        ],
        "transition": world_transition.model_dump(mode="json"),
        "prediction": world_prediction.model_dump(mode="json"),
    }
    environment_interpretation = EnvironmentReasoner().interpret(
        environment_state=environment_state,
        environment_history=world_history.history,
        world_events=world_events,
        knowledge_state=knowledge_state,
    )
    environment_opportunities = EnvironmentOpportunityDetector().detect(
        environment_state=environment_state,
        history=world_history.history,
        knowledge_state=knowledge_state,
    )
    environment_risk = EnvironmentRiskAnalyzer().analyze(
        environment_state=environment_state,
        interpretation=environment_interpretation,
        history=world_history.history,
    )
    environment_reasoning_validation = (
        EnvironmentReasoningValidator().validate(
            interpretation=environment_interpretation,
            opportunities=environment_opportunities,
            risk_reference=environment_risk,
        )
    )
    save_environment_reasoning_trace(
        "sessions",
        loop_trace_id,
        interpretation=environment_interpretation,
        opportunities=environment_opportunities,
        risks=[environment_risk],
    )
    environment_reasoning_data = {
        "interpretation": environment_interpretation.model_dump(mode="json"),
        "opportunities": [
            opportunity.model_dump(mode="json")
            for opportunity in environment_opportunities
        ],
        "risk": environment_risk.model_dump(mode="json"),
        "validation": environment_reasoning_validation.model_dump(
            mode="json"
        ),
    }
    environment_planner = EnvironmentAwarePlanner()
    environment_planning_reference = environment_planner.build_reference(
        opportunities=environment_opportunities,
        risk_reference=environment_risk,
        goal_id=horizon_goal.goal_id,
    )
    environment_planning_validation = EnvironmentPlanningValidator().validate(
        reference=environment_planning_reference,
        risk_reference=environment_risk,
    )
    environment_planning_constraint = EnvironmentRiskAdapter().adapt(
        risk_reference=environment_risk,
    )
    save_environment_planning_trace(
        "sessions",
        loop_trace_id,
        environment_reference=environment_planning_reference,
        goal_adjustments=(
            environment_planning_reference.priority_adjustments
        ),
        risk_constraints=[environment_planning_constraint],
    )
    environment_planning_data = {
        "reference": environment_planning_reference.model_dump(mode="json"),
        "goal_adjustments": [
            adjustment.model_dump(mode="json")
            for adjustment in environment_planning_reference.priority_adjustments
        ],
        "risk_constraints": [
            environment_planning_constraint.model_dump(mode="json")
        ],
        "validation": environment_planning_validation.model_dump(mode="json"),
    }
    decision_reference_builder = DecisionReferenceBuilder()
    decision_reference_ref = decision_reference_builder.build(
        environment_reference=environment_planning_reference,
        world_prediction=world_prediction,
        failure_prevention=prevention_reference,
        planning_quality=planning_score,
        goal_id=horizon_goal.goal_id,
    )
    decision_score = DecisionScorer().score(
        reference=decision_reference_ref,
        historical_success=0.6,
    )
    decision_reference_validation = DecisionReferenceValidator().validate(
        reference=decision_reference_ref,
        score=decision_score,
    )
    decision_risk_notes = DecisionRiskIntegrator().integrate(
        environment_reference=environment_planning_reference,
        failure_prevention=prevention_reference,
    )
    save_decision_reference_trace(
        "sessions",
        loop_trace_id,
        decision_reference=decision_reference_ref,
        score=decision_score,
        risk_notes=decision_risk_notes.risk_notes,
    )
    decision_reference_data = {
        "reference": decision_reference_ref.model_dump(mode="json"),
        "score": decision_score.model_dump(mode="json"),
        "risk_notes": decision_risk_notes.risk_notes,
        "validation": decision_reference_validation.model_dump(mode="json"),
    }
    human_feedback = HumanFeedback(
        feedback_id="fb-demo",
        option_id="opt-NPC_INTERACTION",
        action=FeedbackAction.ACCEPT,
        comment="用户偏好 NPC 对话推进任务",
        trace_id=loop_trace_id,
    )
    human_aligner = HumanAlignmentAligner()
    human_aligned_reference = human_aligner.align(
        decision_reference=decision_reference_ref,
        feedback=human_feedback,
    )
    human_alignment_validation = HumanAlignmentValidator().validate(
        reference=human_aligned_reference,
        alignment=human_aligner.last_score,
    )
    save_human_alignment_trace(
        "sessions",
        loop_trace_id,
        decision_reference=decision_reference_ref,
        feedback=human_feedback,
        alignment=human_aligner.last_score,
    )
    human_alignment_data = {
        "reference": human_aligned_reference.model_dump(mode="json"),
        "alignment": human_aligner.last_score.model_dump(mode="json"),
        "feedback": human_feedback.model_dump(mode="json"),
        "validation": human_alignment_validation.model_dump(mode="json"),
    }
    memory_consolidator = MemoryConsolidator()
    memory_nodes = memory_consolidator.consolidate(
        experiences=goal_experience_store.all(),
        failures=all_patterns,
        world_history=world_history.history,
        decision_reference=decision_reference_ref,
        preferences=human_aligner.memory,
    )
    memory_nodes = MemoryRelationBuilder().auto_link(memory_nodes)
    memory_index = MemoryIndex()
    memory_index.add_many(memory_nodes)
    memory_retriever = MemoryRetriever(memory_index)
    memory_reference = memory_retriever.retrieve(
        current_goal=horizon_goal,
        environment_state=environment_state,
        decision_reference=decision_reference_ref,
    )
    memory_validation_results = MemoryGraphValidator().validate_graph(
        memory_nodes,
    )
    if all(
        result.verdict.value == "VALID"
        for result in memory_validation_results
    ):
        memory_validation = "VALID"
    elif all(
        result.verdict.value != "BLOCKED"
        for result in memory_validation_results
    ):
        memory_validation = "WARNING"
    else:
        memory_validation = "BLOCKED"
    all_relations = [
        relation for node in memory_nodes for relation in node.relations
    ]
    save_memory_graph_trace(
        "sessions",
        loop_trace_id,
        memory_nodes=memory_nodes,
        relations=all_relations,
        retrieval=memory_reference,
        validation=memory_validation,
    )
    memory_graph_data = {
        "memory_count": memory_index.count(),
        "memory_types": sorted(
            {node.memory_type.value for node in memory_nodes}
        ),
        "retrieval": memory_reference.model_dump(mode="json"),
        "validation": memory_validation,
    }
    semantic_engine = SemanticAssociationEngine()
    semantic_relations = semantic_engine.associate(memory_nodes)
    semantic_reasoner = AssociationReasoner()
    semantic_summary = semantic_reasoner.summarize(semantic_relations)
    semantic_reference = semantic_reasoner.build_reference(
        semantic_relations,
    )
    semantic_validations = [
        SemanticAssociationValidator().validate_relation(relation)
        for relation in semantic_relations
    ]
    if all(
        validation.verdict.value == "VALID"
        for validation in semantic_validations
    ):
        semantic_validation = "VALID"
    elif all(
        validation.verdict.value != "BLOCKED"
        for validation in semantic_validations
    ):
        semantic_validation = "WARNING"
    else:
        semantic_validation = "BLOCKED"
    save_semantic_memory_trace(
        "sessions",
        loop_trace_id,
        relations=semantic_relations,
        summary=semantic_summary.model_dump(mode="json"),
        validation=semantic_validation,
    )
    semantic_memory_data = {
        "relation_count": len(semantic_relations),
        "summary": semantic_summary.model_dump(mode="json"),
        "reference": semantic_reference.model_dump(mode="json"),
        "validation": semantic_validation,
    }
    perception_entities, perception_relations = load_demo_knowledge()
    perception_graph = MapleKnowledgeGraph()
    for entity in perception_entities:
        perception_graph.add_entity(entity)
    for relation in perception_relations:
        perception_graph.add_relation(relation)
    perception_observation = PerceptionMockVisionProvider(
        location="射手村",
        visible_entities=["赫丽娜"],
        ui_state="quest_available",
        confidence=0.9,
    ).capture()
    perception_reference = MaplePerceptionBinder(
        knowledge=perception_graph
    ).bind(perception_observation)
    perception_validation = PerceptionValidator().validate(
        perception_observation,
        perception_reference,
    )
    save_perception_trace(
        "sessions",
        loop_trace_id,
        observation=perception_observation,
        entities=perception_reference.visible_entities,
        knowledge_binding=perception_reference,
        validation=perception_validation.verdict.value,
    )
    perception_data = {
        "observation_id": perception_reference.observation_id,
        "visible_entities": [
            entity.model_dump(mode="json")
            for entity in perception_reference.visible_entities
        ],
        "visible_map": perception_reference.visible_map,
        "ui_state_reference": perception_reference.ui_state_reference,
        "related_knowledge": perception_reference.related_knowledge,
        "confidence": perception_reference.confidence,
        "reasoning": perception_reference.reasoning,
        "validation": perception_validation.verdict.value,
    }
    from maple_agent.agent_loop.models import (
        AgentLoopContext,
        AgentLoopStatus,
    )

    maple_agent_context = AgentLoopContext(
        trace_id=loop_trace_id,
        status=AgentLoopStatus.COMPLETED,
        environment_state=environment_state,
        environment_prediction=world_prediction,
        environment_history=world_history.history,
        environment_risk_reference=environment_risk,
        environment_planning_reference=environment_planning_reference,
        decision_reference=decision_reference_ref,
        human_alignment_reference=human_aligned_reference,
        memory_reference=memory_reference,
        semantic_memory_reference=semantic_reference,
        failure_prevention_reference=prevention_reference,
        goal_state=horizon_goal,
        goal_schedule=schedule_result,
        perception_reference=perception_reference,
    )
    maple_context_builder = MapleContextBuilder()
    maple_context_reference = maple_context_builder.build(
        agent_context=maple_agent_context,
        player_id="maple-player-001",
        trace_id=loop_trace_id,
    )
    maple_context_validation = MapleContextValidator().validate(
        maple_context_reference,
    )
    save_maple_context_trace(
        "sessions",
        loop_trace_id,
        reference=maple_context_reference,
        validation=maple_context_validation.verdict.value,
    )
    maple_context_data = {
        "player": maple_context_reference.player_context.model_dump(
            mode="json"
        ),
        "world": maple_context_reference.world_context.model_dump(
            mode="json"
        ),
        "goal": maple_context_reference.goal_context.model_dump(
            mode="json"
        ),
        "cognitive": maple_context_reference.cognitive_context.model_dump(
            mode="json"
        ),
        "summary": maple_context_reference.summary,
        "confidence": maple_context_reference.confidence,
        "validation": maple_context_validation.verdict.value,
    }
    demo_entities, demo_relations = load_demo_knowledge()
    maple_knowledge_graph = MapleKnowledgeGraph()
    for entity in demo_entities:
        maple_knowledge_graph.add_entity(entity)
    for relation in demo_relations:
        maple_knowledge_graph.add_relation(relation)
    maple_knowledge_retriever = MapleKnowledgeRetriever(
        maple_knowledge_graph,
    )
    maple_knowledge_ref = maple_knowledge_retriever.retrieve(
        context=maple_context_reference,
    )
    maple_knowledge_validations = [
        MapleKnowledgeValidator().validate_entity(entity)
        for entity in demo_entities
    ] + [
        MapleKnowledgeValidator().validate_relation(
            relation,
            maple_knowledge_graph,
        )
        for relation in demo_relations
    ]
    if all(
        validation.verdict.value == "VALID"
        for validation in maple_knowledge_validations
    ):
        maple_knowledge_validation = "VALID"
    elif all(
        validation.verdict.value != "BLOCKED"
        for validation in maple_knowledge_validations
    ):
        maple_knowledge_validation = "WARNING"
    else:
        maple_knowledge_validation = "BLOCKED"
    save_maple_knowledge_trace(
        "sessions",
        loop_trace_id,
        knowledge_entities=demo_entities,
        relations=demo_relations,
        retrieval_result=maple_knowledge_ref,
        validation=maple_knowledge_validation,
    )
    maple_knowledge_data = {
        "entity_count": len(demo_entities),
        "categories": sorted(
            {entity.knowledge_type.value for entity in demo_entities}
        ),
        "relation_count": len(demo_relations),
        "retrieval": maple_knowledge_ref.model_dump(mode="json"),
        "validation": maple_knowledge_validation,
    }
    quest_intelligence_planner = QuestIntelligencePlanner(
        maple_knowledge_graph
    )
    quest_goal_reference = quest_intelligence_planner.plan(
        context=maple_context_reference,
        knowledge_reference=maple_knowledge_ref,
        perception_reference=perception_reference,
    )
    quest_reasoning_validation = QuestReasoningValidator().validate(
        quest_goal_reference
    )
    save_quest_reasoning_trace(
        "sessions",
        loop_trace_id,
        quests=quest_goal_reference.active_quests,
        progress=quest_goal_reference.quest_progress,
        goals=(
            quest_goal_reference.recommended_goals
            + quest_goal_reference.blocked_goals
        ),
        dependencies=quest_goal_reference.dependencies,
        validation=quest_reasoning_validation.verdict.value,
    )
    quest_reasoning_data = {
        "active_quests": [
            quest.model_dump(mode="json")
            for quest in quest_goal_reference.active_quests
        ],
        "quest_progress": [
            progress.model_dump(mode="json")
            for progress in quest_goal_reference.quest_progress
        ],
        "recommended_goals": [
            goal.model_dump(mode="json")
            for goal in quest_goal_reference.recommended_goals
        ],
        "blocked_goals": [
            goal.model_dump(mode="json")
            for goal in quest_goal_reference.blocked_goals
        ],
        "dependencies": [
            dependency.model_dump(mode="json")
            for dependency in quest_goal_reference.dependencies
        ],
        "confidence": quest_goal_reference.confidence,
        "reasoning": quest_goal_reference.reasoning,
        "validation": quest_reasoning_validation.verdict.value,
    }
    perception_fusion_engine = PerceptionFusionEngine()
    perception_fusion_reference = perception_fusion_engine.fuse(
        perception_reference=perception_reference,
        knowledge_reference=maple_knowledge_ref,
        context_reference=maple_context_reference,
        quest_goal_reference=quest_goal_reference,
        memory_reference=memory_reference,
        semantic_memory_reference=semantic_reference,
        human_alignment_reference=human_aligned_reference,
    )
    perception_fusion_validation = PerceptionFusionValidator().validate(
        perception_fusion_reference
    )
    save_perception_fusion_trace(
        "sessions",
        loop_trace_id,
        sources={
            source.source: source.confidence
            for source in perception_fusion_reference.source_inputs
        },
        fusion=perception_fusion_reference,
        conflicts=perception_fusion_reference.conflicts,
        validation=perception_fusion_validation.verdict.value,
    )
    perception_fusion_data = {
        "fusion_id": perception_fusion_reference.fusion_id,
        "source_inputs": [
            source.model_dump(mode="json")
            for source in perception_fusion_reference.source_inputs
        ],
        "fused_confidence": perception_fusion_reference.fused_confidence,
        "consistency_score": (
            perception_fusion_reference.consistency_score
        ),
        "conflicts": perception_fusion_reference.conflicts,
        "missing_signals": perception_fusion_reference.missing_signals,
        "focus_reference": perception_fusion_reference.focus_reference,
        "reasoning": perception_fusion_reference.reasoning,
        "validation": perception_fusion_validation.verdict.value,
    }
    reflex_thresholds = ReflexThresholds.from_dict(
        {
            "low_hp_threshold": 0.4,
            "low_mp_threshold": 0.2,
        }
    )
    reflex_detector = ReflexStateDetector(thresholds=reflex_thresholds)
    reflex_low_hp = reflex_detector.detect(
        fusion_reference=perception_fusion_reference,
        context_reference=maple_context_reference,
        hp_reference=HpMpReference(
            current_value=350,
            max_value=1000,
            ratio=0.35,
            confidence=0.9,
            source="mock",
        ),
        mp_reference=HpMpReference(
            current_value=800,
            max_value=1000,
            ratio=0.8,
            confidence=0.9,
            source="mock",
        ),
        death_signal=False,
    )
    reflex_low_hp_validation = ReflexValidator().validate(reflex_low_hp)
    reflex_low_hp = reflex_low_hp.model_copy(
        update={
            "validation": reflex_low_hp_validation.verdict.value,
        }
    )
    save_reflex_trace(
        "sessions",
        loop_trace_id,
        state=reflex_low_hp,
        hp_reference=reflex_low_hp.hp_reference,
        mp_reference=reflex_low_hp.mp_reference,
        danger_events=reflex_low_hp.danger_events,
        thresholds=reflex_thresholds.to_dict(),
        validation=reflex_low_hp_validation.verdict.value,
    )
    reflex_death = reflex_detector.detect(
        fusion_reference=perception_fusion_reference,
        context_reference=maple_context_reference,
        hp_reference=HpMpReference(
            current_value=0,
            max_value=1000,
            ratio=0.0,
            confidence=0.9,
            source="mock",
        ),
        mp_reference=HpMpReference(
            current_value=500,
            max_value=1000,
            ratio=0.5,
            confidence=0.9,
            source="mock",
        ),
        death_signal=True,
    )
    reflex_death_validation = ReflexValidator().validate(reflex_death)
    assert 0 <= reflex_death.confidence <= 1
    reflex_data = {
        "state": reflex_low_hp.state.value,
        "hp": (
            reflex_low_hp.hp_reference.model_dump(mode="json")
            if reflex_low_hp.hp_reference is not None
            else {}
        ),
        "mp": (
            reflex_low_hp.mp_reference.model_dump(mode="json")
            if reflex_low_hp.mp_reference is not None
            else {}
        ),
        "danger_events": [
            event.model_dump(mode="json")
            for event in reflex_low_hp.danger_events
        ],
        "ui_alerts": reflex_low_hp.ui_alerts,
        "confidence": reflex_low_hp.confidence,
        "reasoning": reflex_low_hp.reasoning,
        "validation": reflex_low_hp_validation.verdict.value,
        "death_example": {
            "state": reflex_death.state.value,
            "danger_events": [
                event.model_dump(mode="json")
                for event in reflex_death.danger_events
            ],
            "confidence": reflex_death.confidence,
            "validation": reflex_death_validation.verdict.value,
        },
    }
    vision_runtime_capture = MockScreenshotProvider(
        map_name="射手村",
        npcs=["赫丽娜"],
        monsters=["绿水灵"],
        items=["红药水"],
        ui_elements=["任务提示"],
        hp_ratio=0.8,
        mp_ratio=0.6,
        quests=["新手任务"],
        confidence=0.9,
    )
    vision_runtime_frame = vision_runtime_capture.capture(
        trace_id=loop_trace_id
    )
    vision_runtime_ocr = VisionRuntimeMockOCR(
        text=vision_runtime_capture.mock_ocr_text(),
        confidence=0.9,
    ).recognize(vision_runtime_frame)
    vision_runtime_elements = VisionDetector().detect(
        vision_runtime_frame,
        vision_runtime_ocr,
    )
    vision_observation = GameStateParser().parse(
        vision_runtime_frame,
        vision_runtime_ocr,
        vision_runtime_elements,
    )
    vision_runtime_validation = VisionRuntimeValidator().validate(
        vision_runtime_frame,
        vision_observation,
    )
    save_vision_runtime_trace(
        "sessions",
        loop_trace_id,
        frame=vision_runtime_frame,
        observation=vision_observation,
        validation=vision_runtime_validation.verdict.value,
    )
    vision_runtime_data = {
        "frame_id": vision_runtime_frame.frame_id,
        "source": vision_runtime_frame.source.value,
        "image_reference": vision_runtime_frame.image_reference,
        "visible_map": vision_observation.visible_map,
        "visible_entities": vision_observation.visible_entities,
        "ui_elements": vision_observation.ui_elements,
        "hp_reference": vision_observation.hp_reference,
        "mp_reference": vision_observation.mp_reference,
        "quest_reference": vision_observation.quest_reference,
        "confidence": vision_observation.confidence,
        "validation": vision_runtime_validation.verdict.value,
    }
    game_state_extractor = GameStateExtractor(maple_knowledge_graph)
    game_state_reference = game_state_extractor.extract(vision_observation)
    game_state_validation = GameStateValidator().validate(
        game_state_reference
    )
    save_game_state_trace(
        "sessions",
        loop_trace_id,
        player_state=game_state_reference.player_state,
        map_state=game_state_reference.current_map,
        entities=game_state_reference.visible_entities,
        quest_state=game_state_reference.quest_state,
        validation=game_state_validation.verdict.value,
    )
    game_state_data = {
        "state_id": game_state_reference.state_id,
        "player_state": (
            game_state_reference.player_state.model_dump(mode="json")
            if game_state_reference.player_state is not None
            else {}
        ),
        "current_map": (
            game_state_reference.current_map.model_dump(mode="json")
            if game_state_reference.current_map is not None
            else {}
        ),
        "visible_entities": [
            entity.model_dump(mode="json")
            for entity in game_state_reference.visible_entities
        ],
        "quest_state": (
            game_state_reference.quest_state.model_dump(mode="json")
            if game_state_reference.quest_state is not None
            else {}
        ),
        "combat_state": game_state_reference.combat_state,
        "confidence": game_state_reference.confidence,
        "reasoning": game_state_reference.reasoning,
        "validation": game_state_validation.verdict.value,
    }
    world_graph = WorldKnowledgeImporter().import_data(
        load_demo_world_map()
    )
    world_knowledge_reference = WorldKnowledgeResolver(
        world_graph
    ).resolve(
        game_state_reference=game_state_reference,
        maple_knowledge_reference=maple_knowledge_ref,
    )
    world_knowledge_validation = WorldKnowledgeValidator().validate(
        world_knowledge_reference
    )
    save_world_knowledge_trace(
        "sessions",
        loop_trace_id,
        current_map=world_knowledge_reference.current_map,
        known_maps=world_knowledge_reference.known_maps,
        connections=world_knowledge_reference.map_connections,
        validation=world_knowledge_validation.verdict.value,
    )
    world_knowledge_data = {
        "current_map": world_knowledge_reference.current_map,
        "known_maps": world_knowledge_reference.known_maps,
        "reachable_maps": world_knowledge_reference.reachable_maps,
        "map_connections": [
            connection.model_dump(mode="json")
            for connection in world_knowledge_reference.map_connections
        ],
        "related_npcs": world_knowledge_reference.related_npcs,
        "related_monsters": world_knowledge_reference.related_monsters,
        "related_quests": world_knowledge_reference.related_quests,
        "confidence": world_knowledge_reference.confidence,
        "reasoning": world_knowledge_reference.reasoning,
        "validation": world_knowledge_validation.verdict.value,
    }
    spatial_store = SpatialMapStore.from_data(load_demo_spatial_map())
    spatial_world_reference = SpatialWorldBuilder(spatial_store).resolve(
        world_knowledge_reference=world_knowledge_reference,
        game_state_reference=game_state_reference,
        maple_knowledge_reference=maple_knowledge_ref,
    )
    spatial_world_validation = SpatialWorldValidator().validate(
        spatial_world_reference
    )
    save_spatial_world_trace(
        "sessions",
        loop_trace_id,
        current_map=spatial_world_reference.current_map,
        portals=spatial_world_reference.portals,
        locations=spatial_world_reference.nearby_points,
        validation=spatial_world_validation.verdict.value,
    )
    spatial_world_data = {
        "current_map": spatial_world_reference.current_map,
        "nearby_points": spatial_world_reference.nearby_points,
        "portals": [
            portal.model_dump(mode="json")
            for portal in spatial_world_reference.portals
        ],
        "npc_positions": spatial_world_reference.npc_positions,
        "quest_targets": spatial_world_reference.quest_targets,
        "spatial_confidence": (
            spatial_world_reference.spatial_confidence
        ),
        "reasoning": spatial_world_reference.reasoning,
        "validation": spatial_world_validation.verdict.value,
    }
    navigation_planner = NavigationPlanner()
    navigation_npc = navigation_planner.plan(
        target="赫丽娜",
        game_state_reference=game_state_reference,
        spatial_world_reference=spatial_world_reference,
        world_knowledge_reference=world_knowledge_reference,
        quest_goal_reference=quest_goal_reference,
    )
    navigation_npc_validation = NavigationValidator().validate(
        navigation_npc
    )
    navigation_map = navigation_planner.plan(
        target="魔法密林",
        game_state_reference=game_state_reference,
        spatial_world_reference=spatial_world_reference,
        world_knowledge_reference=world_knowledge_reference,
        quest_goal_reference=quest_goal_reference,
    )
    navigation_map_validation = NavigationValidator().validate(
        navigation_map
    )
    save_navigation_trace(
        "sessions",
        loop_trace_id,
        start=navigation_npc.start_location,
        target=navigation_npc.target_location,
        route=navigation_npc.route_steps,
        validation=navigation_npc_validation.verdict.value,
    )
    navigation_data = {
        "navigation_id": navigation_npc.navigation_id,
        "start_location": navigation_npc.start_location,
        "target_location": navigation_npc.target_location,
        "route_steps": [
            step.model_dump(mode="json")
            for step in navigation_npc.route_steps
        ],
        "estimated_cost": navigation_npc.estimated_cost,
        "confidence": navigation_npc.confidence,
        "reasoning": navigation_npc.reasoning,
        "validation": navigation_npc_validation.verdict.value,
        "cross_map_example": {
            "start": navigation_map.start_location,
            "target": navigation_map.target_location,
            "route": [
                {
                    "type": step.step_type.value,
                    "source": step.source,
                    "target": step.target,
                }
                for step in navigation_map.route_steps
            ],
            "cost": navigation_map.estimated_cost,
            "confidence": navigation_map.confidence,
            "validation": navigation_map_validation.verdict.value,
        },
    }
    behavior_planner = BehaviorPlanner()
    reflex_normal = ReflexReference(
        reflex_id="reflex-normal-demo",
        state=ReflexStateType.NORMAL,
        confidence=0.9,
    )
    behavior_npc = behavior_planner.plan(
        quest_goal_reference=quest_goal_reference,
        navigation_reference=navigation_npc,
        game_state_reference=game_state_reference,
        reflex_reference=reflex_normal,
    )
    behavior_npc_validation = BehaviorValidator().validate(behavior_npc)
    combat_goal = QuestGoalReference(
        active_quests=[],
        quest_progress=[],
        recommended_goals=[
            GoalReference(
                goal_id="combat-goal",
                goal_type=GoalType.QUEST_PROGRESS,
                description="击杀绿水灵",
                priority=0.8,
                related_quest="绿水灵任务",
                confidence=0.8,
                reasoning="演示:击杀类任务",
            )
        ],
        confidence=0.8,
    )
    behavior_combat = behavior_planner.plan(
        quest_goal_reference=combat_goal,
        navigation_reference=navigation_map,
        game_state_reference=game_state_reference,
        reflex_reference=reflex_normal,
        target_hint="绿水灵",
    )
    behavior_combat_validation = BehaviorValidator().validate(
        behavior_combat
    )
    save_behavior_trace(
        "sessions",
        loop_trace_id,
        goal=behavior_npc.goal_reference,
        steps=behavior_npc.behavior_steps,
        validation=behavior_npc_validation.verdict.value,
    )
    behavior_data = {
        "behavior_id": behavior_npc.behavior_id,
        "goal_reference": behavior_npc.goal_reference,
        "behavior_steps": [
            step.model_dump(mode="json")
            for step in behavior_npc.behavior_steps
        ],
        "confidence": behavior_npc.confidence,
        "reasoning": behavior_npc.reasoning,
        "validation": behavior_npc_validation.verdict.value,
        "combat_example": {
            "goal_reference": behavior_combat.goal_reference,
            "steps": [
                step.model_dump(mode="json")
                for step in behavior_combat.behavior_steps
            ],
            "confidence": behavior_combat.confidence,
            "validation": behavior_combat_validation.verdict.value,
        },
    }
    action_mapper = ActionProposalMapper()
    action_proposals = action_mapper.map(
        behavior_npc,
        game_state_reference=game_state_reference,
        navigation_reference=navigation_npc,
        reflex_reference=reflex_normal,
    )
    action_proposal_validation = ActionProposalValidator().validate_many(
        action_proposals
    )
    action_proposals_combat = action_mapper.map(
        behavior_combat,
        game_state_reference=game_state_reference,
        navigation_reference=navigation_map,
        reflex_reference=reflex_normal,
    )
    action_proposal_combat_validation = (
        ActionProposalValidator().validate_many(action_proposals_combat)
    )
    save_action_proposal_trace(
        "sessions",
        loop_trace_id,
        actions=action_proposals,
        validation=action_proposal_validation.verdict.value,
    )
    action_proposal_data = {
        "actions": [
            action.model_dump(mode="json")
            for action in action_proposals
        ],
        "confidence": (
            action_proposals[0].confidence if action_proposals else 0.0
        ),
        "validation": action_proposal_validation.verdict.value,
        "combat_example": {
            "actions": [
                action.model_dump(mode="json")
                for action in action_proposals_combat
            ],
            "validation": action_proposal_combat_validation.verdict.value,
        },
    }
    safety_evaluator = SafetyEvaluator()
    safety_allow = safety_evaluator.evaluate(
        action_proposals[0],
        game_state_reference=game_state_reference,
        reflex_reference=reflex_normal,
    )
    safety_allow_validation = SafetyGateValidator().validate(safety_allow)
    combat_action = next(
        action
        for action in action_proposals_combat
        if action.action_type.value == "COMBAT"
    )
    hp_low_state = GameStateReference(
        state_id="state-hp-low",
        player_state=PlayerStateReference(hp=0.2, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        confidence=0.9,
    )
    safety_warning = safety_evaluator.evaluate(
        combat_action,
        game_state_reference=hp_low_state,
        reflex_reference=reflex_normal,
    )
    safety_warning_validation = SafetyGateValidator().validate(
        safety_warning
    )
    reflex_death = ReflexReference(
        reflex_id="reflex-death-demo",
        state=ReflexStateType.DEATH,
        confidence=0.9,
    )
    safety_blocked = safety_evaluator.evaluate(
        action_proposals[0],
        game_state_reference=game_state_reference,
        reflex_reference=reflex_death,
    )
    safety_blocked_validation = SafetyGateValidator().validate(
        safety_blocked
    )
    save_safety_gate_trace(
        "sessions",
        loop_trace_id,
        action=safety_allow.source_action,
        decision=safety_allow.decision.value,
        risk_factors=safety_allow.risk_factors,
        validation=safety_allow_validation.verdict.value,
    )
    safety_gate_data = {
        "source_action": safety_allow.source_action,
        "decision": safety_allow.decision.value,
        "risk_factors": safety_allow.risk_factors,
        "reasoning": safety_allow.reasoning,
        "confidence": safety_allow.confidence,
        "validation": safety_allow_validation.verdict.value,
        "warning_example": {
            "action": safety_warning.source_action,
            "decision": safety_warning.decision.value,
            "risk_factors": safety_warning.risk_factors,
            "confidence": safety_warning.confidence,
            "validation": safety_warning_validation.verdict.value,
        },
        "blocked_example": {
            "action": safety_blocked.source_action,
            "decision": safety_blocked.decision.value,
            "risk_factors": safety_blocked.risk_factors,
            "confidence": safety_blocked.confidence,
            "validation": safety_blocked_validation.verdict.value,
        },
    }
    failure_detector = FailureDetector()
    recovery_planner = FailureRecoveryPlanner()
    recovery_timeout = recovery_planner.plan(
        action_proposals[0],
        failure_detector.detect(
            action_proposals[0],
            game_state=game_state_reference,
            safety_evaluation=safety_allow,
            timeout_hint=True,
        ),
        game_state=game_state_reference,
        safety_evaluation=safety_allow,
    )
    recovery_timeout_validation = RecoveryValidator().validate(
        recovery_timeout
    )
    interact_action = next(
        action
        for action in action_proposals
        if action.action_type.value == "INTERACT"
    )
    recovery_mismatch = recovery_planner.plan(
        interact_action,
        failure_detector.detect(
            interact_action,
            game_state=game_state_reference,
            safety_evaluation=safety_allow,
            npc_missing=True,
        ),
        game_state=game_state_reference,
        safety_evaluation=safety_allow,
    )
    recovery_combat = recovery_planner.plan(
        combat_action,
        failure_detector.detect(
            combat_action,
            game_state=hp_low_state,
            safety_evaluation=safety_allow,
            hp_decreased=True,
        ),
        game_state=hp_low_state,
        safety_evaluation=safety_allow,
    )
    recovery_abort = recovery_planner.plan(
        action_proposals[0],
        failure_detector.detect(
            action_proposals[0],
            game_state=game_state_reference,
            safety_evaluation=safety_blocked,
        ),
        game_state=game_state_reference,
        safety_evaluation=safety_blocked,
    )
    recovery_abort_validation = RecoveryValidator().validate(recovery_abort)
    save_recovery_trace(
        "sessions",
        loop_trace_id,
        action=recovery_timeout.source_action,
        failure=recovery_timeout.failure_type.value,
        recovery=recovery_timeout.recovery_type.value,
        validation=recovery_timeout_validation.verdict.value,
    )
    recovery_data = {
        "source_action": recovery_timeout.source_action,
        "failure_type": recovery_timeout.failure_type.value,
        "recovery_type": recovery_timeout.recovery_type.value,
        "reasoning": recovery_timeout.reasoning,
        "confidence": recovery_timeout.confidence,
        "validation": recovery_timeout_validation.verdict.value,
        "examples": {
            "state_mismatch": {
                "failure": recovery_mismatch.failure_type.value,
                "recovery": recovery_mismatch.recovery_type.value,
                "confidence": recovery_mismatch.confidence,
            },
            "combat_failure": {
                "failure": recovery_combat.failure_type.value,
                "recovery": recovery_combat.recovery_type.value,
                "confidence": recovery_combat.confidence,
            },
            "safety_blocked": {
                "failure": recovery_abort.failure_type.value,
                "recovery": recovery_abort.recovery_type.value,
                "confidence": recovery_abort.confidence,
                "validation": recovery_abort_validation.verdict.value,
            },
        },
    }
    outcome_verifier = ActionOutcomeVerifier()
    interact_action = next(
        action
        for action in action_proposals
        if action.action_type.value == "INTERACT"
    )
    before_interact = GameStateReference(
        state_id="state-a-before",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        visible_entities=[
            EntityStateReference(name="赫丽娜", type="NPC")
        ],
        quest_state=QuestStateSnapshot(available_quests=["新手任务"]),
        combat_state="NORMAL",
        confidence=0.9,
    )
    after_interact = GameStateReference(
        state_id="state-a-after",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        visible_entities=[
            EntityStateReference(name="赫丽娜", type="NPC")
        ],
        quest_state=QuestStateSnapshot(active_quests=["新手任务"]),
        combat_state="NORMAL",
        confidence=0.9,
    )
    outcome_interact = outcome_verifier.verify(
        interact_action,
        before=before_interact,
        after=after_interact,
        quest_goal=quest_goal_reference,
        reflex_before=reflex_normal,
        reflex_after=reflex_normal,
    )
    outcome_interact_validation = ActionOutcomeValidator().validate(
        outcome_interact
    )
    save_action_verification_trace(
        "sessions",
        loop_trace_id,
        action={"type": "INTERACT", "target": "赫丽娜"},
        expectation=(
            outcome_interact.expected_outcome.model_dump(mode="json")
            if outcome_interact.expected_outcome is not None
            else {}
        ),
        before_state=before_interact.model_dump(mode="json"),
        after_state=after_interact.model_dump(mode="json"),
        evidence=outcome_interact.evidence,
        outcome=outcome_interact,
        validation=outcome_interact_validation.verdict.value,
    )
    nav_action_east = ActionProposalReference(
        action_id="action-nav-east",
        action_type=ActionType.NAVIGATE,
        target_reference="东部森林",
        confidence=0.9,
    )
    nav_ref_east = NavigationReference(
        navigation_id="nav-east",
        start_location="射手村",
        target_location="东部森林",
        route_steps=[
            RouteStep(
                step_type=RouteStepType.PORTAL_REFERENCE,
                source="射手村",
                target="东部森林",
            )
        ],
        estimated_cost=1.0,
        confidence=0.9,
    )
    outcome_nav_timeout = outcome_verifier.verify(
        nav_action_east,
        before=before_interact,
        after=before_interact,
        navigation=nav_ref_east,
        reflex_before=reflex_normal,
        reflex_after=reflex_normal,
        elapsed_reference=70.0,
    )
    before_combat = GameStateReference(
        state_id="state-c-before",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        visible_entities=[
            EntityStateReference(name="绿水灵", type="MONSTER")
        ],
        quest_state=QuestStateSnapshot(),
        combat_state="ENCOUNTER",
        confidence=0.9,
    )
    after_combat = GameStateReference(
        state_id="state-c-after",
        player_state=PlayerStateReference(hp=0.6, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        visible_entities=[],
        quest_state=QuestStateSnapshot(active_quests=["新手任务"]),
        combat_state="NORMAL",
        confidence=0.9,
    )
    outcome_combat = outcome_verifier.verify(
        combat_action,
        before=before_combat,
        after=after_combat,
        reflex_before=reflex_normal,
        reflex_after=reflex_normal,
    )
    outcome_death = outcome_verifier.verify(
        interact_action,
        before=before_interact,
        after=after_interact,
        reflex_before=reflex_normal,
        reflex_after=reflex_death,
    )
    after_low_confidence = GameStateReference(
        state_id="state-e-after",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        confidence=0.1,
    )
    outcome_inconclusive = outcome_verifier.verify(
        interact_action,
        before=before_interact,
        after=after_low_confidence,
        quest_goal=quest_goal_reference,
        reflex_before=reflex_normal,
        reflex_after=reflex_normal,
    )
    nav_outcome_failure = failure_detector.detect(
        nav_action_east,
        outcome=outcome_nav_timeout,
    )
    nav_outcome_recovery = recovery_planner.plan(
        nav_action_east,
        nav_outcome_failure,
    )
    action_verification_data = {
        "source_action": outcome_interact.source_action,
        "expected_action": (
            outcome_interact.expected_outcome.action_reference
            if outcome_interact.expected_outcome is not None
            else ""
        ),
        "status": outcome_interact.status.value,
        "matched_conditions": outcome_interact.matched_conditions,
        "unmatched_conditions": outcome_interact.unmatched_conditions,
        "recovery_required": outcome_interact.recovery_required,
        "confidence": outcome_interact.confidence,
        "validation": outcome_interact_validation.verdict.value,
        "scenarios": {
            "navigation_timeout": {
                "status": outcome_nav_timeout.status.value,
                "recovery_required": (
                    outcome_nav_timeout.recovery_required
                ),
                "recovery": nav_outcome_recovery.recovery_type.value,
            },
            "combat_hp_loss": {
                "status": outcome_combat.status.value,
                "recovery_required": outcome_combat.recovery_required,
            },
            "death": {
                "status": outcome_death.status.value,
                "recovery_required": outcome_death.recovery_required,
            },
            "inconclusive": {
                "status": outcome_inconclusive.status.value,
                "recovery_required": (
                    outcome_inconclusive.recovery_required
                ),
            },
        },
    }
    real_vision_metrics = RealVisionBenchmarkResult(sample_count=0)
    real_vision_readiness = build_real_vision_readiness(
        real_vision_metrics,
        real_client_tested=False,
        capture_provider="windows",
        ocr_provider="none",
        capture_available=False,
        ocr_available=False,
    )
    real_vision_data = {
        "capture_provider": real_vision_readiness.capture_provider,
        "ocr_provider": real_vision_readiness.ocr_provider,
        "real_client_tested": real_vision_readiness.real_client_tested,
        "sample_count": real_vision_readiness.sample_count,
        "capture_success_rate": real_vision_metrics.capture_success_rate,
        "map_accuracy": real_vision_readiness.map_detection_accuracy,
        "hp_mp_accuracy": real_vision_readiness.hp_mp_accuracy,
        "quest_state_accuracy": (
            real_vision_readiness.quest_state_accuracy
        ),
        "npc_precision": real_vision_metrics.npc_precision,
        "npc_recall": real_vision_metrics.npc_recall,
        "mean_capture_latency_ms": (
            real_vision_metrics.mean_capture_latency_ms
        ),
        "mean_ocr_latency_ms": real_vision_metrics.mean_ocr_latency_ms,
        "validation_status": real_vision_readiness.validation_status.value,
        "reasons": [
            "real client not tested",
            "capture provider unavailable",
            "OCR provider unavailable",
        ],
    }
    maple_agent_context = maple_agent_context.model_copy(
        update={
            "quest_goal_reference": quest_goal_reference,
            "perception_fusion_reference": perception_fusion_reference,
            "reflex_reference": reflex_low_hp,
            "vision_reference": vision_observation,
            "game_state_reference": game_state_reference,
            "world_knowledge_reference": world_knowledge_reference,
            "spatial_world_reference": spatial_world_reference,
            "navigation_reference": navigation_npc,
            "behavior_reference": behavior_npc,
            "action_proposal_reference": (
                action_proposals[0] if action_proposals else None
            ),
            "safety_evaluation_reference": safety_allow,
            "recovery_reference": recovery_timeout,
            "action_outcome_reference": outcome_interact,
            "action_expectation_reference": (
                outcome_interact.expected_outcome
            ),
        }
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
        failure_intelligence=failure_intelligence_data,
        goal_scheduler=goal_scheduler_data,
        environment=environment_data,
        world_model=world_model_data,
        environment_reasoning=environment_reasoning_data,
        environment_planning=environment_planning_data,
        decision_reference=decision_reference_data,
        human_alignment=human_alignment_data,
        memory_graph=memory_graph_data,
        semantic_memory=semantic_memory_data,
        maple_context=maple_context_data,
        maple_knowledge=maple_knowledge_data,
        perception=perception_data,
        quest_reasoning=quest_reasoning_data,
        perception_fusion=perception_fusion_data,
        reflex=reflex_data,
        vision_runtime=vision_runtime_data,
        game_state=game_state_data,
        world_knowledge=world_knowledge_data,
        spatial_world=spatial_world_data,
        navigation=navigation_data,
        behavior=behavior_data,
        action_proposal=action_proposal_data,
        safety_gate=safety_gate_data,
        recovery=recovery_data,
        action_verification=action_verification_data,
        real_vision=real_vision_data,
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
