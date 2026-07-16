"""Tests for settings.py — especially Claude Code fallback logic.

Priority chain tested:
1. nano-claude ~/.nano-claude/settings.json env
2. OS environment variables
3. Claude Code ~/.claude/settings.json env (mapped)
4. Hardcoded fallback
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from src.agent.settings import (
    _CLAUDE_CODE_ENV_MAP,
    _get_claude_code_env,
    _resolve,
    get_api_key,
    get_base_url,
    get_context_window,
    get_model,
    get_actual_model,
    load_settings,
)


class TestContextWindow(unittest.TestCase):
    def test_minimax_m2_uses_documented_context_window(self):
        with (
            patch("src.agent.settings._resolve", return_value=""),
            patch("src.agent.settings.get_model", return_value="MiniMax-M2.7"),
        ):
            self.assertEqual(get_context_window(), 204_800)

    def test_explicit_context_window_takes_priority(self):
        with patch("src.agent.settings._resolve", return_value="128000"):
            self.assertEqual(get_context_window(), 128_000)


def _write_tmp_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")


class TestClaudeCodeEnvMap(unittest.TestCase):
    """Verify the nano-claude → Claude Code env var name mapping."""

    def test_api_key_mapping(self):
        self.assertEqual(
            _CLAUDE_CODE_ENV_MAP["NANO_CLAUDE_API_KEY"],
            "ANTHROPIC_AUTH_TOKEN",
        )

    def test_base_url_mapping(self):
        self.assertEqual(
            _CLAUDE_CODE_ENV_MAP["NANO_CLAUDE_BASE_URL"],
            "ANTHROPIC_BASE_URL",
        )

    def test_model_mappings(self):
        for tier in ("HAIKU", "SONNET", "OPUS"):
            nano_key = f"NANO_CLAUDE_DEFAULT_{tier}_MODEL"
            claude_key = f"ANTHROPIC_DEFAULT_{tier}_MODEL"
            self.assertEqual(_CLAUDE_CODE_ENV_MAP[nano_key], claude_key)

    def test_timeout_mapping_passthrough(self):
        # Same name on both sides
        self.assertEqual(_CLAUDE_CODE_ENV_MAP["API_TIMEOUT_MS"], "API_TIMEOUT_MS")


class TestGetClaudeCodeEnv(unittest.TestCase):
    """Test _get_claude_code_env reads from ~/.claude/settings.json with mapping."""

    def test_reads_mapped_key(self, tmp_path=None):
        tmp_path = tmp_path or Path(os.environ.get("TEMP", "/tmp"))
        cc_file = tmp_path / "claude_settings.json"
        _write_tmp_json(cc_file, {
            "env": {
                "ANTHROPIC_AUTH_TOKEN": "cc-token-123",
                "ANTHROPIC_BASE_URL": "https://cc.example.com",
                "ANTHROPIC_DEFAULT_SONNET_MODEL": "cc-sonnet",
            }
        })
        with patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file):
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_API_KEY"), "cc-token-123")
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_BASE_URL"), "https://cc.example.com")
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_DEFAULT_SONNET_MODEL"), "cc-sonnet")

    def test_returns_empty_when_file_missing(self):
        with patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", Path("/nonexistent/claude_settings.json")):
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_API_KEY"), "")

    def test_returns_empty_for_missing_key(self, tmp_path=None):
        tmp_path = tmp_path or Path(os.environ.get("TEMP", "/tmp"))
        cc_file = tmp_path / "claude_settings_empty.json"
        _write_tmp_json(cc_file, {"env": {}})
        with patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file):
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_API_KEY"), "")

    def test_handles_invalid_json(self, tmp_path=None):
        tmp_path = tmp_path or Path(os.environ.get("TEMP", "/tmp"))
        cc_file = tmp_path / "claude_settings_bad.json"
        cc_file.write_text("not json", encoding="utf-8")
        with patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file):
            self.assertEqual(_get_claude_code_env("NANO_CLAUDE_API_KEY"), "")


class TestResolvePriority(unittest.TestCase):
    """Test the 4-level priority chain: nano → os env → claude code → fallback."""

    def _make_tmp(self) -> Path:
        return Path(os.environ.get("TEMP", "/tmp"))

    def test_priority_1_nano_settings_wins(self):
        """nano-claude settings.json value takes highest priority."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings.json"
        _write_tmp_json(nano_file, {
            "env": {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": "nano-model"}
        })
        cc_file = tmp / "claude_settings.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": "cc-model"}
        })

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
            patch.dict(os.environ, {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": "env-model"}, clear=False),
        ):
            self.assertEqual(get_model(), "nano-model")

    def test_priority_2_os_env_over_claude_code(self):
        """OS env var wins over Claude Code settings."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_empty.json"
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": ""}})
        cc_file = tmp / "claude_settings2.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": "cc-model"}
        })

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
            patch.dict(os.environ, {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": "env-model"}, clear=False),
        ):
            self.assertEqual(get_model(), "env-model")

    def test_priority_3_claude_code_fallback(self):
        """Claude Code settings used when nano + env are empty."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_fallback.json"
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": ""}})
        cc_file = tmp / "claude_settings3.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": "cc-fallback-model"}
        })

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
            patch.dict(os.environ, {}, clear=False),
        ):
            # Remove the env var if present
            os.environ.pop("NANO_CLAUDE_DEFAULT_SONNET_MODEL", None)
            self.assertEqual(get_model(), "cc-fallback-model")

    def test_priority_4_hardcoded_fallback(self):
        """Hardcoded fallback when all sources are empty."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_hardcoded.json"
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_DEFAULT_SONNET_MODEL": ""}})
        cc_file = tmp / "claude_settings_empty2.json"
        _write_tmp_json(cc_file, {"env": {"ANTHROPIC_DEFAULT_SONNET_MODEL": ""}})

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
        ):
            os.environ.pop("NANO_CLAUDE_DEFAULT_SONNET_MODEL", None)
            os.environ.pop("ANTHROPIC_DEFAULT_SONNET_MODEL", None)
            self.assertEqual(get_model(), "glm-5")

    def test_api_key_full_chain(self):
        """Test get_api_key with all 4 levels."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_key.json"
        cc_file = tmp / "claude_settings_key.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_AUTH_TOKEN": "cc-key-456"}
        })

        # Level 1: nano wins
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_API_KEY": "nano-key"}})
        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
            patch.dict(os.environ, {"NANO_CLAUDE_API_KEY": "env-key"}, clear=False),
        ):
            self.assertEqual(get_api_key(), "nano-key")

        # Level 2: env wins (nano empty)
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_API_KEY": ""}})
        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
            patch.dict(os.environ, {"NANO_CLAUDE_API_KEY": "env-key"}, clear=False),
        ):
            self.assertEqual(get_api_key(), "env-key")

        # Level 3: Claude Code wins (nano + env empty)
        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
        ):
            os.environ.pop("NANO_CLAUDE_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
            self.assertEqual(get_api_key(), "cc-key-456")

    def test_base_url_fallback(self):
        """Test get_base_url falls through to Claude Code."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_url.json"
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_BASE_URL": ""}})
        cc_file = tmp / "claude_settings_url.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_BASE_URL": "https://cc.api.example.com"}
        })

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
        ):
            os.environ.pop("NANO_CLAUDE_BASE_URL", None)
            os.environ.pop("ANTHROPIC_BASE_URL", None)
            self.assertEqual(get_base_url(), "https://cc.api.example.com")

    def test_get_actual_model_all_tiers(self):
        """Test get_actual_model for haiku/sonnet/opus tiers."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_tiers.json"
        _write_tmp_json(nano_file, {"env": {
            "NANO_CLAUDE_DEFAULT_HAIKU_MODEL": "",
            "NANO_CLAUDE_DEFAULT_SONNET_MODEL": "",
            "NANO_CLAUDE_DEFAULT_OPUS_MODEL": "",
        }})
        cc_file = tmp / "claude_settings_tiers.json"
        _write_tmp_json(cc_file, {"env": {
            "ANTHROPIC_DEFAULT_HAIKU_MODEL": "cc-haiku",
            "ANTHROPIC_DEFAULT_SONNET_MODEL": "cc-sonnet",
            "ANTHROPIC_DEFAULT_OPUS_MODEL": "cc-opus",
        }})

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
        ):
            for var in ("NANO_CLAUDE_DEFAULT_HAIKU_MODEL",
                        "NANO_CLAUDE_DEFAULT_SONNET_MODEL",
                        "NANO_CLAUDE_DEFAULT_OPUS_MODEL",
                        "ANTHROPIC_DEFAULT_HAIKU_MODEL",
                        "ANTHROPIC_DEFAULT_SONNET_MODEL",
                        "ANTHROPIC_DEFAULT_OPUS_MODEL"):
                os.environ.pop(var, None)

            self.assertEqual(get_actual_model("haiku"), "cc-haiku")
            self.assertEqual(get_actual_model("sonnet"), "cc-sonnet")
            self.assertEqual(get_actual_model("opus"), "cc-opus")

    def test_whitespace_values_treated_as_empty(self):
        """Whitespace-only values should be skipped in priority chain."""
        tmp = self._make_tmp()
        nano_file = tmp / "nano_settings_ws.json"
        _write_tmp_json(nano_file, {"env": {"NANO_CLAUDE_API_KEY": "   "}})
        cc_file = tmp / "claude_settings_ws.json"
        _write_tmp_json(cc_file, {
            "env": {"ANTHROPIC_AUTH_TOKEN": "cc-trimmed"}
        })

        with (
            patch("src.agent.settings.SETTINGS_FILE", nano_file),
            patch("src.agent.settings.CLAUDE_CODE_SETTINGS_FILE", cc_file),
        ):
            os.environ.pop("NANO_CLAUDE_API_KEY", None)
            os.environ.pop("ANTHROPIC_API_KEY", None)
            os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)
            self.assertEqual(get_api_key(), "cc-trimmed")


if __name__ == "__main__":
    unittest.main()
