"""Settings management for nano-claude."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# Config directory in user home
CONFIG_DIR = Path.home() / ".nano-claude"
SETTINGS_FILE = CONFIG_DIR / "settings.json"
PROJECTS_DIR = CONFIG_DIR / "projects"
SESSIONS_DIR = CONFIG_DIR / "sessions"
MEMORY_DIR = CONFIG_DIR / "memory"


@dataclass
class Settings:
    """User settings for nano-claude, mirrors ~/.claude/settings.json structure."""

    env: dict[str, str] = field(
        default_factory=lambda: {
            "NANO_CLAUDE_API_KEY": "",
            "NANO_CLAUDE_BASE_URL": "",
            "NANO_CLAUDE_DEFAULT_HAIKU_MODEL": "glm-5",
            "NANO_CLAUDE_DEFAULT_SONNET_MODEL": "glm-5",
            "NANO_CLAUDE_DEFAULT_OPUS_MODEL": "qwen3.5-plus",
            "API_TIMEOUT_MS": "60000",
        }
    )
    mcpServers: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "env": self.env,
            "mcpServers": self.mcpServers,
        }


DEFAULT_SETTINGS = Settings()


def _first_nonempty(*values: str) -> str:
    for value in values:
        candidate = value.strip()
        if candidate:
            return candidate
    return ""


def ensure_config_dir() -> Path:
    """Ensure config directory and subdirs exist."""
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    PROJECTS_DIR.mkdir(parents=True, exist_ok=True)
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_settings() -> Settings:
    """Load settings from file, create default if not exists."""
    ensure_config_dir()

    if not SETTINGS_FILE.exists():
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS

    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        return Settings(
            env=data.get("env", DEFAULT_SETTINGS.env),
            mcpServers=data.get("mcpServers", DEFAULT_SETTINGS.mcpServers),
        )
    except (json.JSONDecodeError, TypeError):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS


def save_settings(settings: Settings) -> None:
    """Save settings to file."""
    ensure_config_dir()
    SETTINGS_FILE.write_text(json.dumps(settings.to_dict(), indent=2), encoding="utf-8")


def get_api_key() -> str:
    """Get API key from settings or environment."""
    import os

    settings = load_settings()
    return _first_nonempty(
        settings.env.get("NANO_CLAUDE_API_KEY", ""),
        settings.env.get("ANTHROPIC_AUTH_TOKEN", ""),
        os.environ.get("NANO_CLAUDE_API_KEY", ""),
        os.environ.get("ANTHROPIC_API_KEY", ""),
        os.environ.get("ANTHROPIC_AUTH_TOKEN", ""),
    )


def get_base_url() -> str:
    """Get API base URL from settings or environment."""
    import os

    settings = load_settings()
    return _first_nonempty(
        settings.env.get("NANO_CLAUDE_BASE_URL", ""),
        settings.env.get("ANTHROPIC_BASE_URL", ""),
        os.environ.get("NANO_CLAUDE_BASE_URL", ""),
        os.environ.get("ANTHROPIC_BASE_URL", ""),
    )


def get_model() -> str:
    """Get current model name directly from settings/env."""
    import os

    settings = load_settings()
    return _first_nonempty(
        settings.env.get("NANO_CLAUDE_DEFAULT_SONNET_MODEL", ""),
        os.environ.get("NANO_CLAUDE_DEFAULT_SONNET_MODEL", ""),
        "glm-5",  # Fallback
    )


def get_actual_model(tier: str) -> str:
    """Get actual model name for a tier (haiku/sonnet/opus)."""
    import os

    settings = load_settings()

    tier_key = f"NANO_CLAUDE_DEFAULT_{tier.upper()}_MODEL"
    return _first_nonempty(
        settings.env.get(tier_key, ""),
        os.environ.get(tier_key, ""),
        "glm-5",  # Fallback
    )
