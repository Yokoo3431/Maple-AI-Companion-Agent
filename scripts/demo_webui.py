"""启动 Phase 0 WebUI 控制台演示(纯本地,不触碰游戏)。"""

import sys
from datetime import UTC, datetime, timedelta
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
