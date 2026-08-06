"""配置系统单测:默认值 / 环境变量覆盖 / 非法值。"""

from pathlib import Path

import pytest
from pydantic import ValidationError

from maple_agent.config.settings import build_settings

_ENV_KEYS = (
    "MAPLE_LOG_LEVEL",
    "MAPLE_WEBUI_HOST",
    "MAPLE_WEBUI_PORT",
    "MAPLE_EMERGENCY_HOTKEY",
    "LLM_PROVIDER",
    "LLM_API_KEY",
    "LLM_BASE_URL",
    "LLM_MODEL",
    "LLM_TIMEOUT_SEC",
    "MAPLE_GAME_PROCESS",
    "MAPLE_GAME_TITLE",
    "MAPLE_KB_GAME_PROFILE",
    "VISION_CAPTURE_FPS",
    "VISION_OCR_PROVIDER",
    "VISION_SCALE_MODE",
)


def _clear_env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key in _ENV_KEYS:
        monkeypatch.delenv(key, raising=False)


def test_defaults_without_env(monkeypatch):
    _clear_env(monkeypatch)
    s = build_settings(env_file=None)
    assert s.app.log_level == "INFO"
    assert s.app.webui_host == "127.0.0.1"
    assert s.app.webui_port == 8080
    assert s.app.emergency_hotkey == "ctrl+alt+pause"
    assert s.llm.provider == "deepseek"
    assert s.llm.model == "deepseek-v4-flash"
    assert s.llm.base_url == "https://api.deepseek.com"
    assert s.game.process == "MapleStory.exe"
    assert s.game.title == "MapleStory"
    assert s.knowledge.game_profile == ""
    assert s.vision.capture_fps == 5
    assert s.vision.ocr_provider == "tesseract"
    assert s.vision.scale_mode == "auto"


def test_env_override(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("LLM_MODEL", "custom-model")
    monkeypatch.setenv("MAPLE_WEBUI_PORT", "9090")
    monkeypatch.setenv("MAPLE_KB_GAME_PROFILE", "classic_beta")
    s = build_settings(env_file=None)
    assert s.llm.model == "custom-model"
    assert s.app.webui_port == 9090
    assert s.knowledge.game_profile == "classic_beta"


def test_invalid_value_raises(monkeypatch):
    _clear_env(monkeypatch)
    monkeypatch.setenv("MAPLE_WEBUI_PORT", "not-a-port")
    with pytest.raises(ValidationError):
        build_settings(env_file=None)


def test_dotenv_file_override(tmp_path: Path, monkeypatch):
    _clear_env(monkeypatch)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "MAPLE_WEBUI_PORT=7777\n"
        "LLM_MODEL=dotenv-model\n",
        encoding="utf-8",
    )
    s = build_settings(env_file=env_file)
    assert s.app.webui_port == 7777
    assert s.llm.model == "dotenv-model"
