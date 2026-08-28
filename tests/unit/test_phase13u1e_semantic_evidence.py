from datetime import UTC, datetime

from maple_agent.companion_runtime.observation_adapter import (
    ExistingVisionObservationAdapter,
)
from maple_agent.hybrid_vision.models import PerceptionMethod
from maple_agent.vision_runtime.models import ScreenObservation

BASE_TIME = datetime(2026, 8, 27, tzinfo=UTC)


def test_screen_observation_maps_existing_fields_to_structured_evidence():
    screen = ScreenObservation(
        visible_map="map_m1",
        visible_entities=["npc_heena"],
        quest_reference=["quest_intro"],
        confidence=0.8,
    )

    current = ExistingVisionObservationAdapter.from_screen_observation(
        observation_id="obs-1",
        timestamp=BASE_TIME,
        frame_id="frame-1",
        observation=screen,
        source="REAL_VISION",
    )

    assert [item.evidence_type for item in current.evidence] == [
        "map",
        "entity",
        "quest",
    ]
    assert [item.value for item in current.evidence] == [
        "map_m1",
        "npc_heena",
        "quest_intro",
    ]
    assert all(
        item.method is PerceptionMethod.SCREEN_PARSER
        for item in current.evidence
    )
    assert all(item.confidence == 0.8 for item in current.evidence)
    assert all(item.frame_id == "frame-1" for item in current.evidence)


def test_screen_observation_keeps_hp_mp_as_player_state():
    current = ExistingVisionObservationAdapter.from_screen_observation(
        observation_id="obs-2",
        timestamp=BASE_TIME,
        frame_id="frame-2",
        observation=ScreenObservation(
            hp_reference=0.8,
            mp_reference=0.5,
            confidence=0.7,
        ),
    )

    assert current.evidence == []
    assert current.player_status is not None
    assert current.player_status.hp == 0.8
    assert current.player_status.mp == 0.5


def test_empty_screen_observation_does_not_create_fake_evidence():
    current = ExistingVisionObservationAdapter.from_screen_observation(
        observation_id="obs-3",
        timestamp=BASE_TIME,
        frame_id="frame-3",
        observation=ScreenObservation(confidence=0.0),
    )

    assert current.evidence == []
    assert current.player_status is None


def test_screen_observation_adapter_preserves_source_and_timestamp():
    current = ExistingVisionObservationAdapter.from_screen_observation(
        observation_id="obs-4",
        timestamp=BASE_TIME,
        frame_id="frame-4",
        observation=ScreenObservation(
            visible_map="map_m1",
            confidence=0.6,
        ),
        source="EXISTING_VISION_RESULT",
    )

    assert current.source == "EXISTING_VISION_RESULT"
    assert current.timestamp == BASE_TIME
    assert current.evidence[0].source == "EXISTING_VISION_RESULT"
    assert current.evidence[0].timestamp == BASE_TIME
