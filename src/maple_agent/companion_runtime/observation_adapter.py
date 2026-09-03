"""Thin adapter for existing Vision results; no capture or OCR is implemented."""

from __future__ import annotations

from datetime import datetime

from maple_agent.game_state.models import (
    CurrentObservation,
    PlayerStateReference,
)
from maple_agent.game_state.player import PlayerStateParser
from maple_agent.hybrid_vision.models import PerceptionEvidence, PerceptionMethod
from maple_agent.vision_runtime.models import ScreenObservation
from maple_agent.vision_runtime.visual_semantics import (
    VisualCandidateType,
    VisualSemanticCandidate,
)


class ExistingVisionObservationAdapter:
    """Convert an existing observation/evidence result into the shared contract."""

    @staticmethod
    def from_current_observation(
        observation: CurrentObservation,
    ) -> CurrentObservation:
        return observation.model_copy(deep=True)

    @staticmethod
    def from_evidence(
        *,
        observation_id: str,
        timestamp: datetime,
        evidence: list[PerceptionEvidence],
        source: str = "REAL_VISION",
        player_status: PlayerStateReference | None = None,
    ) -> CurrentObservation:
        return CurrentObservation(
            observation_id=observation_id,
            timestamp=timestamp,
            evidence=evidence,
            player_status=player_status,
            source=source,
        )

    @staticmethod
    def from_screen_observation(
        *,
        observation_id: str,
        timestamp: datetime,
        frame_id: str,
        observation: ScreenObservation,
        source: str = "REAL_VISION",
    ) -> CurrentObservation:
        """Bridge an existing parser result without adding inference."""
        evidence: list[PerceptionEvidence] = []
        if observation.visible_map:
            evidence.append(
                PerceptionEvidence(
                    evidence_id=f"{frame_id}:map",
                    evidence_type="map",
                    value=observation.visible_map,
                    confidence=observation.confidence,
                    source=source,
                    timestamp=timestamp,
                    frame_id=frame_id,
                    method=PerceptionMethod.SCREEN_PARSER,
                )
            )
        for index, name in enumerate(observation.visible_entities):
            if not name:
                continue
            evidence.append(
                PerceptionEvidence(
                    evidence_id=f"{frame_id}:entity:{index}",
                    evidence_type="entity",
                    value=name,
                    confidence=observation.confidence,
                    source=source,
                    timestamp=timestamp,
                    frame_id=frame_id,
                    method=PerceptionMethod.SCREEN_PARSER,
                )
            )
        for index, quest in enumerate(observation.quest_reference):
            if not quest:
                continue
            evidence.append(
                PerceptionEvidence(
                    evidence_id=f"{frame_id}:quest:{index}",
                    evidence_type="quest",
                    value=quest,
                    confidence=observation.confidence,
                    source=source,
                    timestamp=timestamp,
                    frame_id=frame_id,
                    method=PerceptionMethod.SCREEN_PARSER,
                )
            )
        player_status = (
            PlayerStateParser.parse(observation)
            if (
                observation.hp_reference is not None
                or observation.mp_reference is not None
            )
            else None
        )
        return ExistingVisionObservationAdapter.from_evidence(
            observation_id=observation_id,
            timestamp=timestamp,
            evidence=evidence,
            source=source,
            player_status=player_status,
        )

    @staticmethod
    def from_visual_semantic_candidates(
        *,
        observation_id: str,
        timestamp: datetime,
        candidates: list[VisualSemanticCandidate],
        source: str = "VLM_VISUAL_OBSERVATION",
    ) -> CurrentObservation:
        """Adapt validated visible facts into the existing observation contract."""
        evidence: list[PerceptionEvidence] = []
        hp: float | None = None
        mp: float | None = None
        confidence = 0.0
        for index, candidate in enumerate(candidates):
            confidence = max(confidence, candidate.confidence)
            if candidate.candidate_type is VisualCandidateType.HP:
                try:
                    value = (
                        candidate.normalized_ratio
                        if candidate.normalized_ratio is not None
                        else float(candidate.candidate_value)
                    )
                except ValueError:
                    continue
                if 0 <= value <= 1:
                    hp = value
                continue
            if candidate.candidate_type is VisualCandidateType.MP:
                try:
                    value = (
                        candidate.normalized_ratio
                        if candidate.normalized_ratio is not None
                        else float(candidate.candidate_value)
                    )
                except ValueError:
                    continue
                if 0 <= value <= 1:
                    mp = value
                continue
            evidence_type = (
                "map"
                if candidate.candidate_type is VisualCandidateType.MAP
                else "ui_text"
            )
            evidence.append(
                PerceptionEvidence(
                    evidence_id=f"{candidate.frame_reference}:{index}",
                    evidence_type=evidence_type,
                    value=candidate.candidate_value,
                    confidence=candidate.confidence,
                    source=source,
                    timestamp=timestamp,
                    frame_id=candidate.frame_reference,
                    method=PerceptionMethod.VLM_VISUAL_OBSERVATION,
                )
            )
        player_status = (
            PlayerStateReference(hp=hp, mp=mp)
            if hp is not None or mp is not None
            else None
        )
        return ExistingVisionObservationAdapter.from_evidence(
            observation_id=observation_id,
            timestamp=timestamp,
            evidence=evidence,
            source=source,
            player_status=player_status,
        )
