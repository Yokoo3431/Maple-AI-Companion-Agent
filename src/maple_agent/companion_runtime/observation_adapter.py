"""Thin adapter for existing Vision results; no capture or OCR is implemented."""

from __future__ import annotations

from datetime import datetime

from maple_agent.game_state.models import (
    CurrentObservation,
    PlayerStateReference,
)
from maple_agent.hybrid_vision.models import PerceptionEvidence


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
