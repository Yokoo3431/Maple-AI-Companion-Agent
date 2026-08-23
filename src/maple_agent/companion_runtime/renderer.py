"""Formatting-only renderer and structural safety audit."""

from __future__ import annotations

from maple_agent.companion_runtime.models import CompanionSnapshot

FORBIDDEN_SCHEMA_FIELDS = {
    "action",
    "command",
    "executor",
    "input",
    "target_action",
    "tool_call",
    "movement_plan",
    "combat_plan",
    "execution_request",
}


def validate_snapshot_schema(snapshot: CompanionSnapshot) -> list[str]:
    """Return forbidden schema keys; this is structural, not phrase matching."""
    payload = snapshot.model_dump(mode="json")
    keys: set[str] = set()

    def collect(value: object) -> None:
        if isinstance(value, dict):
            keys.update(str(key).lower() for key in value)
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)

    collect(payload)
    return sorted(keys & FORBIDDEN_SCHEMA_FIELDS)


def render_snapshot(snapshot: CompanionSnapshot) -> str:
    """Render existing fields only; no reasoning or enrichment occurs here."""
    lines = [
        f"当前助手状态（{snapshot.snapshot_id}）",
        f"观察：{snapshot.observation_id}",
        f"置信度：{snapshot.confidence:.4f}",
        f"地点：{_location(snapshot)}",
        f"附近实体：{_names(snapshot.semantic_state.nearby_entities)}",
        f"任务上下文：{_names(snapshot.semantic_state.quest_context)}",
        f"信息参考：{_reference_text(snapshot)}",
        f"信息缺口：{_join(snapshot.information_gaps)}",
        f"不确定性：{_join(snapshot.uncertainties)}",
        f"数据质量：{_join(snapshot.data_quality_notes)}",
        f"就绪状态：{_join(snapshot.readiness_notes)}",
    ]
    return "\n".join(lines)


def _location(snapshot: CompanionSnapshot) -> str:
    location = snapshot.semantic_state.location
    return location.display_name if location is not None else "未确认"


def _names(entities: list) -> str:
    return _join([getattr(entity, "display_name", "UNKNOWN") for entity in entities])


def _reference_text(snapshot: CompanionSnapshot) -> str:
    return _join(
        [
            f"{reference.title}：{reference.description}"
            for reference in snapshot.planning_references
        ]
    )


def _join(values: list[str]) -> str:
    return "；".join(values) if values else "无"
