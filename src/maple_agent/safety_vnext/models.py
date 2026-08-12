"""Safety Architecture vNext 契约模型(Phase 13-E,仅契约,不启用执行)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ExecutionMode(StrEnum):
    """未来执行模式(仅契约枚举)。"""

    MOCK_ONLY = "MOCK_ONLY"
    CONTROLLED_TEST = "CONTROLLED_TEST"
    HUMAN_SUPERVISED = "HUMAN_SUPERVISED"


class SafetyArchitectureVersion(StrEnum):
    """安全架构版本。"""

    V1 = "V1"
    VNEXT = "VNEXT"


class PermissionScopeV2(StrEnum):
    """权限范围 v2(复用 Phase 6-C 扩展)。"""

    OBSERVE = "OBSERVE"
    NAVIGATE = "NAVIGATE"
    INTERACT = "INTERACT"
    COMBAT = "COMBAT"
    COLLECT = "COLLECT"
    USE_ITEM = "USE_ITEM"


class KillSwitchType(StrEnum):
    """杀开关类型。"""

    GLOBAL_SOFTWARE = "GLOBAL_SOFTWARE"
    SESSION = "SESSION"
    USER_EMERGENCY = "USER_EMERGENCY"


class KillSwitchState(StrEnum):
    """杀开关状态。"""

    ARMED = "ARMED"
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class ReadinessStatus(StrEnum):
    """就绪状态。"""

    NOT_READY = "NOT_READY"
    FOUNDATION_ONLY = "FOUNDATION_ONLY"
    READY = "READY"
    PASSED = "PASSED"


class GateVerdict(StrEnum):
    """受控执行门结论(不等于真实执行许可)。"""

    ELIGIBLE_REFERENCE = "ELIGIBLE_REFERENCE"
    WARNING_REFERENCE = "WARNING_REFERENCE"
    BLOCKED_REFERENCE = "BLOCKED_REFERENCE"


class ControlledExecutionPolicyReference(BaseModel):
    """受控执行策略参考(默认 MOCK_ONLY 且未启用)。"""

    policy_id: str
    architecture_version: SafetyArchitectureVersion = (
        SafetyArchitectureVersion.VNEXT
    )
    execution_mode: ExecutionMode = ExecutionMode.MOCK_ONLY
    allowed_action_types: list[str] = Field(default_factory=list)
    target_restrictions: list[str] = Field(default_factory=list)
    window_restriction: str = ""
    max_actions_per_second: int = Field(default=1, ge=0)
    max_actions_per_minute: int = Field(default=20, ge=0)
    max_continuous_execution_time: float = Field(default=300.0, ge=0)
    max_retry_count: int = Field(default=3, ge=0)
    max_failure_count: int = Field(default=5, ge=0)
    max_navigation_timeout: float = Field(default=60.0, ge=0)
    max_combat_duration: float = Field(default=30.0, ge=0)
    requires_human_confirmation: bool = True
    requires_permission_token: bool = True
    requires_window_binding: bool = True
    requires_outcome_verification: bool = True
    requires_kill_switch: bool = True
    enabled: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None


class PermissionPolicyV2(BaseModel):
    """权限策略 v2(目标/窗口/期限/预算限制,禁止 ALL_ACCESS 默认)。"""

    scope: PermissionScopeV2
    target_restrictions: list[str] = Field(default_factory=list)
    window_restriction: str = ""
    expires_at: datetime | None = None
    max_actions: int = Field(default=0, ge=0)
    max_rate: int = Field(default=0, ge=0)
    allowed_action_types: list[str] = Field(default_factory=list)
    session_restriction: str = ""


class GameWindowBindingReference(BaseModel):
    """游戏窗口绑定参考(仅契约,不调用 Win32 Input API)。"""

    binding_id: str
    process_reference: str = ""
    window_reference: str = ""
    title_reference: str = ""
    session_reference: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    validation_status: ReadinessStatus = ReadinessStatus.NOT_READY


class ExecutionSessionReference(BaseModel):
    """执行会话参考(仅 Reference)。"""

    session_id: str
    architecture_version: SafetyArchitectureVersion = (
        SafetyArchitectureVersion.VNEXT
    )
    execution_mode: ExecutionMode = ExecutionMode.MOCK_ONLY
    window_binding_id: str = ""
    policy_id: str = ""
    permission_token_ids: list[str] = Field(default_factory=list)
    started_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    expires_at: datetime | None = None
    kill_switch_state: KillSwitchState = KillSwitchState.ARMED
    action_count: int = 0
    failure_count: int = 0
    retry_count: int = 0
    status: str = "IDLE"


class KillSwitchReference(BaseModel):
    """杀开关参考。"""

    kill_switch_id: str
    kill_switch_type: KillSwitchType
    state: KillSwitchState = KillSwitchState.ARMED


class RealVisionReadinessReference(BaseModel):
    """真实视觉就绪参考(当前必须 NOT_READY)。"""

    capture_provider: str = "MOCK_SCREENSHOT"
    ocr_provider: str = "MOCK_OCR"
    real_client_tested: bool = False
    map_detection_accuracy: float = Field(default=0.0, ge=0, le=1)
    entity_detection_accuracy: float = Field(default=0.0, ge=0, le=1)
    ui_detection_accuracy: float = Field(default=0.0, ge=0, le=1)
    hp_mp_accuracy: float = Field(default=0.0, ge=0, le=1)
    quest_state_accuracy: float = Field(default=0.0, ge=0, le=1)
    confidence_calibration: float = Field(default=0.0, ge=0, le=1)
    sample_count: int = 0
    validation_status: ReadinessStatus = ReadinessStatus.NOT_READY


class KnowledgeReadinessReference(BaseModel):
    """知识质量就绪参考(当前仅 FOUNDATION_ONLY)。"""

    game_profile: str = ""
    server_version: str = ""
    dataset_version: str = ""
    source_provenance: str = "manual-dataset"
    map_coverage: float = Field(default=0.0, ge=0, le=1)
    portal_coverage: float = Field(default=0.0, ge=0, le=1)
    npc_coverage: float = Field(default=0.0, ge=0, le=1)
    monster_coverage: float = Field(default=0.0, ge=0, le=1)
    quest_coverage: float = Field(default=0.0, ge=0, le=1)
    item_coverage: float = Field(default=0.0, ge=0, le=1)
    validation_score: float = Field(default=0.0, ge=0, le=1)
    status: ReadinessStatus = ReadinessStatus.FOUNDATION_ONLY


class ControlledExecutionGateReference(BaseModel):
    """受控执行门参考(ELIGIBLE 不等于真实执行)。"""

    gate_id: str
    verdict: GateVerdict = GateVerdict.BLOCKED_REFERENCE
    blocked_reasons: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    action_reference: str = ""
    policy_id: str = ""
    session_id: str = ""
    window_binding_id: str = ""
    expected_outcome_id: str = ""
    validation: str = ""


class ControlledExecutionReadinessReference(BaseModel):
    """受控执行整体就绪参考。"""

    safety_contract_ready: bool = False
    real_vision_ready: bool = False
    knowledge_ready: bool = False
    permission_ready: bool = False
    window_binding_ready: bool = False
    kill_switch_ready: bool = False
    rate_limit_ready: bool = False
    outcome_verification_ready: bool = False
    overall_status: ReadinessStatus = ReadinessStatus.NOT_READY
    reasons: list[str] = Field(default_factory=list)
