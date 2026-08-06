"""GameWindowDetector 接口与 Mock 单测。"""

import pytest

from maple_agent.game import (
    GameWindowDetector,
    MockGameWindowDetector,
    WindowInfo,
    WindowRect,
)


def test_window_rect_fields():
    rect = WindowRect(left=0, top=0, width=800, height=600)
    assert (rect.left, rect.top, rect.width, rect.height) == (0, 0, 800, 600)


def test_window_info_fields():
    rect = WindowRect(left=0, top=0, width=800, height=600)
    info = WindowInfo(
        handle=12345,
        title="MapleStory",
        process_name="MapleStory.exe",
        rect=rect,
    )
    assert info.handle == 12345
    assert info.title == "MapleStory"
    assert info.process_name == "MapleStory.exe"
    assert info.rect is rect


def test_interface_is_abstract():
    with pytest.raises(TypeError):
        GameWindowDetector()


def test_mock_detector_with_window():
    info = WindowInfo(
        handle=1,
        title="MapleStory",
        process_name="MapleStory.exe",
        rect=WindowRect(left=0, top=0, width=800, height=600),
    )
    detector = MockGameWindowDetector(info)
    assert detector.exists() is True
    assert detector.find_window() is info


def test_mock_detector_without_window():
    detector = MockGameWindowDetector()
    assert detector.exists() is False
    assert detector.find_window() is None
