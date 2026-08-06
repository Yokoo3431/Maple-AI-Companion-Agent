"""配置系统实现。

加载优先级:defaults.yaml 提供默认值,.env 与系统环境变量逐项覆盖
(系统环境变量优先于 .env)。各分节使用独立前缀:

- 应用级:MAPLE_*
- LLM:LLM_*
- 游戏:MAPLE_GAME_*
- 知识库:MAPLE_KB_*
- 视觉:VISION_*
"""

from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field

_DEFAULTS_FILE = Path(__file__).parent / "defaults.yaml"
_ENV_FILE = Path.cwd() / ".env"

_SECTION_PREFIXES: dict[str, str] = {
    "app": "MAPLE_",
    "llm": "LLM_",
    "game": "MAPLE_GAME_",
    "knowledge": "MAPLE_KB_",
    "vision": "VISION_",
}


def _load_defaults() -> dict[str, Any]:
    with _DEFAULTS_FILE.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


_DEFAULTS = _load_defaults()


class AppConfig(BaseModel):
    """应用级配置。"""

    model_config = ConfigDict(extra="ignore")

    log_level: str = _DEFAULTS["app"]["log_level"]
    webui_host: str = _DEFAULTS["app"]["webui_host"]
    webui_port: int = Field(default=_DEFAULTS["app"]["webui_port"], ge=1, le=65535)
    emergency_hotkey: str = _DEFAULTS["app"]["emergency_hotkey"]


class LlmConfig(BaseModel):
    """LLM(L2 Planner)配置。"""

    model_config = ConfigDict(extra="ignore")

    provider: str = _DEFAULTS["llm"]["provider"]
    api_key: str = _DEFAULTS["llm"]["api_key"]
    base_url: str = _DEFAULTS["llm"]["base_url"]
    model: str = _DEFAULTS["llm"]["model"]
    timeout_sec: float = Field(default=_DEFAULTS["llm"]["timeout_sec"], gt=0)


class GameConfig(BaseModel):
    """游戏客户端配置。"""

    model_config = ConfigDict(extra="ignore")

    process: str = _DEFAULTS["game"]["process"]
    title: str = _DEFAULTS["game"]["title"]


class KnowledgeConfig(BaseModel):
    """知识库配置。"""

    model_config = ConfigDict(extra="ignore")

    game_profile: str = _DEFAULTS["knowledge"]["game_profile"]


class VisionConfig(BaseModel):
    """视觉配置(Phase 1 生效)。"""

    model_config = ConfigDict(extra="ignore")

    capture_fps: int = Field(default=_DEFAULTS["vision"]["capture_fps"], ge=1, le=60)
    ocr_provider: str = _DEFAULTS["vision"]["ocr_provider"]
    scale_mode: str = _DEFAULTS["vision"]["scale_mode"]


class Settings(BaseModel):
    """根配置,组合各分节。"""

    model_config = ConfigDict(extra="ignore")

    app: AppConfig = Field(default_factory=AppConfig)
    llm: LlmConfig = Field(default_factory=LlmConfig)
    game: GameConfig = Field(default_factory=GameConfig)
    knowledge: KnowledgeConfig = Field(default_factory=KnowledgeConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)


def _merged_env(env_file: Path | None) -> dict[str, str]:
    """合并 .env 与系统环境变量,系统环境变量优先。"""
    merged: dict[str, str] = {}
    if env_file is not None and env_file.exists():
        merged.update({k: v for k, v in dotenv_values(env_file).items() if v is not None})
    for key, value in os.environ.items():
        merged[key] = value
    return merged


def _section_kwargs(env: dict[str, str], prefix: str) -> dict[str, Any]:
    """提取指定前缀的环境变量为分节构造参数(如 MAPLE_LOG_LEVEL → log_level)。"""
    kwargs: dict[str, Any] = {}
    for key, value in env.items():
        if key.upper().startswith(prefix):
            field_name = key[len(prefix) :].lower()
            kwargs[field_name] = value
    return kwargs


def build_settings(env_file: Path | None = _ENV_FILE) -> Settings:
    """按 defaults.yaml + .env + 系统环境变量构造配置。"""
    env = _merged_env(env_file)
    return Settings(
        app=AppConfig(**_section_kwargs(env, _SECTION_PREFIXES["app"])),
        llm=LlmConfig(**_section_kwargs(env, _SECTION_PREFIXES["llm"])),
        game=GameConfig(**_section_kwargs(env, _SECTION_PREFIXES["game"])),
        knowledge=KnowledgeConfig(**_section_kwargs(env, _SECTION_PREFIXES["knowledge"])),
        vision=VisionConfig(**_section_kwargs(env, _SECTION_PREFIXES["vision"])),
    )


@functools.lru_cache
def get_settings() -> Settings:
    """返回进程级缓存的配置;.env 变更后调用 reload_settings()。"""
    return build_settings()


def reload_settings() -> None:
    """清空配置缓存。"""
    get_settings.cache_clear()
