"""ActionOutcomeVerifier:预期 + 前后状态 -> 结果判定(确定性,无 LLM)。"""

from __future__ import annotations

from maple_agent.action_proposal.models import (
    ActionProposalReference,
)
from maple_agent.action_verification.comparator import GameStateComparator
from maple_agent.action_verification.expectation import (
    ActionExpectationBuilder,
)
from maple_agent.action_verification.models import (
    ActionOutcomeReference,
    ActionOutcomeStatus,
    ExpectedOutcomeReference,
    OutcomeEvidence,
)
from maple_agent.game_state.models import GameStateReference
from maple_agent.logging_setup import new_id
from maple_agent.navigation.models import NavigationReference
from maple_agent.quest_reasoning.models import QuestGoalReference
from maple_agent.reflex.models import ReflexReference, ReflexStateType
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)


class ActionOutcomeVerifier:
    """把动作前后状态与预期对比,输出结果参考。"""

    _CONFIDENCE = {
        ActionOutcomeStatus.SUCCESS: 0.9,
        ActionOutcomeStatus.PARTIAL_SUCCESS: 0.7,
        ActionOutcomeStatus.FAILED: 0.85,
        ActionOutcomeStatus.TIMEOUT: 0.8,
        ActionOutcomeStatus.INCONCLUSIVE: 0.4,
        ActionOutcomeStatus.BLOCKED: 0.95,
        ActionOutcomeStatus.NOT_EVALUATED: 0.0,
    }

    def __init__(
        self,
        *,
        expectation_builder: ActionExpectationBuilder | None = None,
        comparator: GameStateComparator | None = None,
        low_confidence_threshold: float = 0.3,
    ) -> None:
        self.expectation_builder = (
            expectation_builder or ActionExpectationBuilder()
        )
        self.comparator = comparator or GameStateComparator()
        self.low_confidence_threshold = low_confidence_threshold
        self.last_outcome: ActionOutcomeReference | None = None

    def verify(
        self,
        action: ActionProposalReference,
        *,
        before: GameStateReference | None = None,
        after: GameStateReference | None = None,
        expectation: ExpectedOutcomeReference | None = None,
        navigation: NavigationReference | None = None,
        quest_goal: QuestGoalReference | None = None,
        reflex_before: ReflexReference | None = None,
        reflex_after: ReflexReference | None = None,
        safety_evaluation: SafetyEvaluationReference | None = None,
        elapsed_reference: float = 0.0,
    ) -> ActionOutcomeReference:
        if expectation is None:
            expectation = self.expectation_builder.build(
                action,
                game_state=before,
                navigation=navigation,
                quest_goal=quest_goal,
            )
        reasoning: list[str] = []
        evidence: list[OutcomeEvidence] = []
        if (
            safety_evaluation is not None
            and safety_evaluation.decision
            is SafetyDecisionType.BLOCKED
        ):
            reasoning.append("安全门已阻止动作,无实际执行结果可验证")
            return self._build(
                action,
                expectation,
                evidence,
                ActionOutcomeStatus.BLOCKED,
                [],
                [],
                elapsed_reference,
                reasoning,
                recovery_required=False,
            )
        if after is None:
            reasoning.append("缺少有效 After 状态,无法判定")
            return self._build(
                action,
                expectation,
                evidence,
                ActionOutcomeStatus.INCONCLUSIVE,
                [],
                [],
                elapsed_reference,
                reasoning,
                recovery_required=False,
            )
        if (
            reflex_after is not None
            and reflex_after.state is ReflexStateType.DEATH
        ):
            evidence.append(
                OutcomeEvidence(
                    evidence_type="PLAYER_DEATH",
                    before_value=(
                        reflex_before.state.value
                        if reflex_before is not None
                        else ""
                    ),
                    after_value="DEATH",
                    matched=True,
                    confidence=0.95,
                    reason="player death",
                )
            )
            reasoning.append("检测到玩家死亡,判定失败")
            return self._build(
                action,
                expectation,
                evidence,
                ActionOutcomeStatus.FAILED,
                [],
                ["player death"],
                elapsed_reference,
                reasoning,
                recovery_required=True,
            )
        if after.confidence < self.low_confidence_threshold:
            reasoning.append(
                f"After 状态置信度过低({after.confidence}),无法判定"
            )
            return self._build(
                action,
                expectation,
                evidence,
                ActionOutcomeStatus.INCONCLUSIVE,
                [],
                [],
                elapsed_reference,
                reasoning,
                recovery_required=False,
            )
        if before is None:
            reasoning.append("缺少有效 Before 状态,无法比较")
            return self._build(
                action,
                expectation,
                evidence,
                ActionOutcomeStatus.INCONCLUSIVE,
                [],
                [],
                elapsed_reference,
                reasoning,
                recovery_required=False,
            )
        evidence = self.comparator.compare(
            before,
            after,
            target=action.target_reference,
            reflex_before=reflex_before,
            reflex_after=reflex_after,
        )
        matched, unmatched, unknown = self._evaluate_conditions(
            action,
            expectation,
            evidence,
            before,
            after,
        )
        timeout = (
            elapsed_reference
            > expectation.timeout_reference_seconds
        )
        all_matched = bool(matched and not unmatched and not unknown)
        status = ActionOutcomeStatus.INCONCLUSIVE
        recovery_required = False
        if timeout and not all_matched:
            status = ActionOutcomeStatus.TIMEOUT
            recovery_required = True
            reasoning.append(
                f"超过参考超时({expectation.timeout_reference_seconds}s)"
                "且预期未满足"
            )
        elif all_matched:
            status = ActionOutcomeStatus.SUCCESS
            reasoning.append("全部核心预期满足")
        elif matched and not unmatched and unknown:
            status = ActionOutcomeStatus.PARTIAL_SUCCESS
            recovery_required = True
            reasoning.append("核心预期满足但存在无法判定的条件")
        elif matched and unmatched:
            status = ActionOutcomeStatus.PARTIAL_SUCCESS
            recovery_required = True
            reasoning.append("部分预期满足,部分未满足")
        elif not matched and unmatched and not unknown:
            status = ActionOutcomeStatus.FAILED
            recovery_required = True
            reasoning.append("核心预期均未满足,判定失败")
        elif not matched and not unmatched and unknown:
            status = ActionOutcomeStatus.INCONCLUSIVE
            reasoning.append("信息不足,无法判定")
        else:
            status = ActionOutcomeStatus.INCONCLUSIVE
            reasoning.append("缺少明确证据")
        reasoning.append(f"判定: {status.value}")
        return self._build(
            action,
            expectation,
            evidence,
            status,
            matched,
            unmatched,
            elapsed_reference,
            reasoning,
            recovery_required=recovery_required,
        )

    def _evaluate_conditions(
        self,
        action: ActionProposalReference,
        expectation: ExpectedOutcomeReference,
        evidence: list[OutcomeEvidence],
        before: GameStateReference,
        after: GameStateReference,
    ) -> tuple[list[str], list[str], list[str]]:
        matched: list[str] = []
        unmatched: list[str] = []
        unknown: list[str] = []
        if expectation.expected_map:
            after_map = (
                after.current_map.map_name
                if after.current_map is not None
                else ""
            )
            if after_map == expectation.expected_map:
                matched.append("expected_map")
            else:
                unmatched.append("expected_map")
        if expectation.expected_target_visible:
            visible = {
                entity.name for entity in after.visible_entities
            }
            if action.target_reference in visible:
                matched.append("expected_target_visible")
            else:
                unmatched.append("expected_target_visible")
        if expectation.expected_target_absent:
            visible = {
                entity.name for entity in after.visible_entities
            }
            if action.target_reference not in visible:
                matched.append("expected_target_absent")
            else:
                unmatched.append("expected_target_absent")
        if expectation.expected_quest_progress:
            after_active = (
                set(after.quest_state.active_quests)
                if after.quest_state is not None
                else set()
            )
            if any(
                quest in after_active
                for quest in expectation.expected_quest_progress
            ):
                matched.append("expected_quest_progress")
            else:
                unmatched.append("expected_quest_progress")
        evidence_by_type = {
            item.evidence_type: item for item in evidence
        }
        for change_type in expectation.expected_state_changes:
            item = evidence_by_type.get(change_type)
            if item is None:
                unknown.append(change_type)
            elif item.matched:
                matched.append(change_type)
            else:
                unmatched.append(change_type)
        return (
            list(dict.fromkeys(matched)),
            list(dict.fromkeys(unmatched)),
            list(dict.fromkeys(unknown)),
        )

    def _build(
        self,
        action: ActionProposalReference,
        expectation: ExpectedOutcomeReference,
        evidence: list[OutcomeEvidence],
        status: ActionOutcomeStatus,
        matched: list[str],
        unmatched: list[str],
        elapsed_reference: float,
        reasoning: list[str],
        *,
        recovery_required: bool,
    ) -> ActionOutcomeReference:
        outcome = ActionOutcomeReference(
            outcome_id=new_id(),
            source_action=(
                f"{getattr(action.action_type, 'value', action.action_type)}: "
                f"{action.target_reference}"
            ),
            status=status,
            expected_outcome=expectation,
            evidence=evidence,
            matched_conditions=matched,
            unmatched_conditions=unmatched,
            elapsed_reference=elapsed_reference,
            confidence=self._CONFIDENCE[status],
            reasoning=reasoning,
            recovery_required=recovery_required,
        )
        self.last_outcome = outcome
        return outcome
