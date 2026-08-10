"""Architecture Contract(Phase 7-A):核心契约元数据,仅文档/审计用途。"""

from __future__ import annotations

from maple_agent import __version__

# 架构冻结版本
ARCHITECTURE_VERSION = "1.0"

# 统一 Trace Schema 版本(未来升级保持兼容)
TRACE_SCHEMA_VERSION = "1.0"

# Agent 版本(与包版本一致)
AGENT_VERSION = __version__

# 安全模式(永久约束)
SAFETY_MODE = "MOCK_ONLY"

# 核心模块清单(Phase 0 - 6-E 冻结)
CORE_MODULES = [
    "observation",
    "vision_eval",
    "knowledge",
    "decision",
    "action_plan",
    "confirmation",
    "executor_sandbox",
    "reflection",
    "experience",
    "evaluation",
    "agent_loop",
]

# 依赖方向:source 模块禁止导入 target 模块(防循环依赖与职责越界)
FORBIDDEN_DEPENDENCIES = {
    "observation": [
        "decision",
        "confirmation",
        "executor_sandbox",
        "reflection",
        "evaluation",
        "agent_loop",
    ],
    "vision_eval": [
        "decision",
        "executor_sandbox",
        "reflection",
        "agent_loop",
    ],
    "decision": [
        "confirmation",
        "executor_sandbox",
        "reflection",
        "evaluation",
        "agent_loop",
    ],
    "action_plan": [
        "executor_sandbox",
        "reflection",
        "evaluation",
        "agent_loop",
    ],
    "confirmation": [
        "executor_sandbox",
        "reflection",
        "evaluation",
        "agent_loop",
    ],
    "executor_sandbox": ["reflection", "evaluation", "agent_loop"],
    "reflection": ["evaluation", "agent_loop"],
    "evaluation": ["agent_loop"],
}

# 永久安全边界
SAFETY_BOUNDARY = {
    "allowed": [
        "observation",
        "analysis",
        "planning",
        "confirmation",
        "mock_execution",
        "replay",
    ],
    "forbidden": [
        "physical_input",
        "automation_control",
        "client_modification",
    ],
}

# 统一 Trace 字段契约
TRACE_CONTRACT = {
    "schema_version": TRACE_SCHEMA_VERSION,
    "required_fields": ["trace_id", "stages", "final_status"],
    "optional_fields": ["agent_version"],
}
