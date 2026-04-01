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


@dataclass
class Settings:
    """User settings for nano-claude, mirrors ~/.claude/settings.json structure."""
    env: dict[str, str] = field(default_factory=lambda: {
        "NANO_CLAUDE_API_KEY": "",
        "NANO_CLAUDE_BASE_URL": "",
        "NANO_CLAUDE_MODEL": "glm-5",
        "API_TIMEOUT_MS": "60000",
    })
    mcpServers: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "env": self.env,
            "mcpServers": self.mcpServers,
        }


DEFAULT_SETTINGS = Settings()


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
    SETTINGS_FILE.write_text(
        json.dumps(settings.to_dict(), indent=2),
        encoding="utf-8"
    )


def get_api_key() -> str:
    """Get API key from settings or environment."""
    import os
    settings = load_settings()
    # Check nano-claude settings first
    key = settings.env.get("NANO_CLAUDE_API_KEY", "")
    if key:
        return key
    # Check ANTHROPIC_AUTH_TOKEN (Claude Code style)
    key = settings.env.get("ANTHROPIC_AUTH_TOKEN", "")
    if key:
        return key
    # Fall back to environment variables
    return os.environ.get("ANTHROPIC_API_KEY", "") or os.environ.get("ANTHROPIC_AUTH_TOKEN", "")


def get_base_url() -> str:
    """Get API base URL from settings or environment."""
    import os
    settings = load_settings()
    url = settings.env.get("NANO_CLAUDE_BASE_URL", "")
    if url:
        return url
    # Check ANTHROPIC_BASE_URL in settings
    url = settings.env.get("ANTHROPIC_BASE_URL", "")
    if url:
        return url
    return os.environ.get("ANTHROPIC_BASE_URL", "")


def get_model() -> str:
    """Get model name from settings."""
    settings = load_settings()
    return settings.env.get("NANO_CLAUDE_MODEL", "glm-5")