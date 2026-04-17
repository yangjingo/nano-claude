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

# Claude Code config (fallback source for model/api settings)
CLAUDE_CODE_SETTINGS_FILE = Path.home() / ".claude" / "settings.json"

# Mapping: nano-claude env key → Claude Code env key
_CLAUDE_CODE_ENV_MAP: dict[str, str] = {
    "NANO_CLAUDE_API_KEY": "ANTHROPIC_AUTH_TOKEN",
    "NANO_CLAUDE_BASE_URL": "ANTHROPIC_BASE_URL",
    "NANO_CLAUDE_DEFAULT_HAIKU_MODEL": "ANTHROPIC_DEFAULT_HAIKU_MODEL",
    "NANO_CLAUDE_DEFAULT_SONNET_MODEL": "ANTHROPIC_DEFAULT_SONNET_MODEL",
    "NANO_CLAUDE_DEFAULT_OPUS_MODEL": "ANTHROPIC_DEFAULT_OPUS_MODEL",
    "API_TIMEOUT_MS": "API_TIMEOUT_MS",
}


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


def _get_claude_code_env(key: str) -> str:
    """Look up a key from Claude Code's settings.json as fallback.

    Maps nano-claude env key names to Claude Code env key names automatically.
    """
    claude_key = _CLAUDE_CODE_ENV_MAP.get(key, key)
    if not CLAUDE_CODE_SETTINGS_FILE.exists():
        return ""
    try:
        data = json.loads(CLAUDE_CODE_SETTINGS_FILE.read_text(encoding="utf-8"))
        return str(data.get("env", {}).get(claude_key, "")).strip()
    except (json.JSONDecodeError, TypeError, OSError):
        return ""


def _resolve(key: str, *os_env_keys: str, fallback: str = "") -> str:
    """Resolve a setting value with priority:

    1. nano-claude settings.json env (nano-claude key name)
    2. nano-claude settings.json env (Claude Code mapped key name)
    3. OS environment variables (os_env_keys)
    4. Claude Code ~/.claude/settings.json env (mapped)
    5. fallback
    """
    settings = load_settings()
    # Step 1: nano-claude specific key
    nano_val = settings.env.get(key, "").strip()
    if nano_val:
        return nano_val
    # Step 2: also check Claude Code mapped key in nano-claude settings
    # (users may use ANTHROPIC_* key names in their nano-claude settings)
    cc_key = _CLAUDE_CODE_ENV_MAP.get(key)
    if cc_key and cc_key != key:
        cc_val = settings.env.get(cc_key, "").strip()
        if cc_val:
            return cc_val
    import os
    # Step 3: OS env vars
    for ek in os_env_keys:
        val = os.environ.get(ek, "").strip()
        if val:
            return val
    # Step 4: Claude Code settings fallback
    cc_val = _get_claude_code_env(key)
    if cc_val:
        return cc_val
    return fallback


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
    """Get API key: nano-claude settings → env → Claude Code settings."""
    return _resolve(
        "NANO_CLAUDE_API_KEY",
        "NANO_CLAUDE_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
    )


def get_base_url() -> str:
    """Get API base URL: nano-claude settings → env → Claude Code settings."""
    return _resolve(
        "NANO_CLAUDE_BASE_URL",
        "NANO_CLAUDE_BASE_URL",
        "ANTHROPIC_BASE_URL",
    )


def get_model() -> str:
    """Get current model with priority:

    1. Generic ANTHROPIC_MODEL override (from settings or env)
    2. Tier-specific SONNET_MODEL (from settings → env → Claude Code)
    3. fallback
    """
    # Check generic model override first
    settings = load_settings()
    for generic_key in ("ANTHROPIC_MODEL", "NANO_CLAUDE_MODEL"):
        val = settings.env.get(generic_key, "").strip()
        if val:
            return val
    import os
    for generic_key in ("ANTHROPIC_MODEL", "NANO_CLAUDE_MODEL"):
        val = os.environ.get(generic_key, "").strip()
        if val:
            return val
    # Fall back to tier-specific sonnet model
    return _resolve(
        "NANO_CLAUDE_DEFAULT_SONNET_MODEL",
        "NANO_CLAUDE_DEFAULT_SONNET_MODEL",
        "ANTHROPIC_DEFAULT_SONNET_MODEL",
        fallback="glm-5",
    )


def get_actual_model(tier: str) -> str:
    """Get actual model name for a tier (haiku/sonnet/opus): nano-claude → env → Claude Code."""
    # Check generic model override first (applies to all tiers)
    settings = load_settings()
    for generic_key in ("ANTHROPIC_MODEL", "NANO_CLAUDE_MODEL"):
        val = settings.env.get(generic_key, "").strip()
        if val:
            return val
    import os
    for generic_key in ("ANTHROPIC_MODEL", "NANO_CLAUDE_MODEL"):
        val = os.environ.get(generic_key, "").strip()
        if val:
            return val
    # Fall back to tier-specific model
    tier_key = f"NANO_CLAUDE_DEFAULT_{tier.upper()}_MODEL"
    claude_os_key = f"ANTHROPIC_DEFAULT_{tier.upper()}_MODEL"
    return _resolve(
        tier_key,
        tier_key,
        claude_os_key,
        fallback="glm-5",
    )
