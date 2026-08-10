# Data Schema

> Phase 7-A Architecture Freeze(冻结版本: 1.0)

核心数据模型统一记录(字段 / 类型 / 生命周期 / 生产者 / 消费者)。

## ObservationFrame

| 字段 | 类型 | 生命周期 | 生产者 | 消费者 |
| --- | --- | --- | --- | --- |
| frame_id | str | 单次观察 | ObservationAdapter | VisionEvaluator |
| timestamp | datetime | 单次观察 | ObservationAdapter | 审计 |
| source | str | 单次观察 | ObservationAdapter | 审计 |
| image_available | bool | 单次观察 | ObservationAdapter | ObservationValidator |
| ocr_text | str | 单次观察 | OCRProvider | Collector/VisionEvaluator |
| confidence | float(0-1) | 单次观察 | OCRProvider | Validator/Evaluator |
| metadata | dict | 单次观察 | Adapter | 审计 |

## ObservationState

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| map_name | str | ObservationCollector | Decision/AgentLoop |
| visible_entities | list[str] | ObservationCollector | Decision/AgentLoop |
| confidence | float | ObservationCollector | VisionEvaluator |
| observations | list[str] | ObservationCollector | 审计 |
| timestamp | datetime | ObservationCollector | 审计 |

## VisionEvaluationResult

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| evaluation_id / frame_id | str | VisionEvaluator | Confirmation/AgentLoop |
| overall_score | float | VisionEvaluator | Confirmation/AgentLoop |
| ocr_score / entity_score / consistency_score / confidence_score | float | VisionEvaluator | 审计 |
| risk_level | LOW/MEDIUM/HIGH | VisionEvaluator | Confirmation 门控 |
| issues / recommendations | list[str] | VisionEvaluator | 审计/WebUI |

## DecisionResult

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| selected_option | DecisionOption \| None | DecisionEngine | ActionPlanner |
| alternatives / rejected | list[DecisionOption] | DecisionEngine | 审计 |
| score | float | DecisionEngine | 审计 |
| explanation / trace_id | str | DecisionEngine | 审计 |

## ActionPlan

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| plan_id / decision_id / goal_id | str | ActionPlanner | Confirmation/AgentLoop |
| action / target | str | ActionPlanner | Confirmation/Sandbox |
| prerequisites / validation_conditions | list[str] | ActionPlanner | Validator/AgentLoop |
| steps | list[ActionStep] | ActionPlanner | Orchestrator |
| status | DRAFT/VALIDATING/READY/BLOCKED | ActionPlanner | AgentLoop |

## ConfirmationRequest

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| confirmation_id | str | HumanConfirmationGate | ConfirmationManager |
| action / target | str | Gate | WebUI/审计 |
| risk_level / vision_score / confidence | str/float | Gate | Validator |
| status | PENDING/APPROVED/REJECTED/EXPIRED/BLOCKED | Manager | AgentLoop |

## PermissionToken

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| token_id / confirmation_id | str | ConfirmationManager | SandboxValidator |
| approved | bool | Manager | Validator |
| scope | str(ACTION:TARGET) | Manager | Validator |
| expires_at | datetime | Manager | Validator |

> 注意: PermissionToken 仅为逻辑许可,禁止绑定真实执行。

## SandboxExecutionResult

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| execution_id | str | LimitedExecutorSandbox | Reflection/AgentLoop |
| status | CREATED...COMPLETED/BLOCKED | Sandbox | AgentLoop |
| success | bool | Sandbox | Reflection |
| message | str | Sandbox | 审计 |
| mode | 固定 MOCK_ONLY | Sandbox | Validator/AgentLoop |
| audit | dict | Sandbox | Replay |

## ReflectionResult

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| reflection_id / execution_id | str | ReflectionEngine | ExperienceMemory |
| success | bool | ReflectionEngine | Trigger/AgentLoop |
| failure_type | WORLD_MISMATCH/KNOWLEDGE_ERROR/LOW_CONFIDENCE/EXECUTION_FAILED/OBSERVATION_FAILED | Engine | Trigger |
| next_action | continue/replan | Engine | AgentLoop |

## EvaluationReport

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| evaluation_id / trace_id | str | EvaluationBenchmark | 审计/WebUI |
| decision/planning/execution/reflection/memory_score | float | Benchmark | 审计 |
| overall_score | float | Benchmark | WebUI |
| issues / recommendations | list[str] | Benchmark | 报告 |

## AgentLoopContext

| 字段 | 类型 | 生产者 | 消费者 |
| --- | --- | --- | --- |
| trace_id | str | AgentLoopOrchestrator | Trace/审计 |
| 各阶段结果(observation...evaluation) | 各模块模型 | Orchestrator | WebUI/Validator |
| status | AgentLoopStatus | Orchestrator | WebUI |

## 强类型要求

- 核心契约禁止裸 dict(模型均为 Pydantic)
- 未来扩展字段必须带默认值,保持向后兼容
