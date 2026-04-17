"""Security system for nano-claude tools.

Provides path sandboxing, sensitive file detection, core dangerous
command interception, and permission levels with user confirmation.

Command safety guidance (whitelist semantics) is provided via system prompt
rather than regex — the model already knows what commands are safe.

Architecture::

    SecurityGate (unified entry point)
      ├─ PathSandbox           — allowed roots + blocked paths
      ├─ SensitiveFileChecker  — .env, .ssh/, credentials, etc.
      ├─ CoreDangerDetector    — fatal command patterns only
      └─ ConfirmCallback       — async user confirmation when needed
"""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Coroutine

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

ConfirmCallback = Callable[[str, str], Coroutine[Any, Any, bool]]


class PermissionLevel(Enum):
    AUTO_APPROVE = "auto_approve"
    CONTEXT_AWARE = "context_aware"
    ALWAYS_ASK = "always_ask"


@dataclass(frozen=True)
class SecurityDecision:
    allowed: bool
    reason: str
    warning: str = ""
    requires_confirmation: bool = False


@dataclass(frozen=True)
class SecurityConfig:
    """Immutable configuration for the security system."""

    allowed_roots: tuple[str, ...] = (".",)
    blocked_paths: tuple[str, ...] = (
        "~/.ssh/",
        "/etc/",
        "~/.aws/",
        "~/.gnupg/",
        "~/.config/gcloud/",
        "~/.azure/",
        "/var/log/",
        "/proc/",
        "/sys/",
    )
    sensitive_file_patterns: tuple[str, ...] = (
        r"\.env$",
        r"\.env\.",
        r"credentials",
        r"\.ssh/",
        r"\.pem$",
        r"\.key$",
        r"id_rsa",
        r"id_ed25519",
        r"\.aws/",
        r"\.gnupg/",
        r"secret",
        r"\.htpasswd",
        r"\.npmrc$",
        r"\.pypirc$",
    )
    core_dangerous_patterns: tuple[str, ...] = (
        # Privilege escalation
        r"\bsudo\b",
        r"\bsu\s",
        # Destructive file operations
        r"\brm\s+(-[^\s]*r[^\s]*f|-[^\s]*f[^\s]*r)\s+/",
        r"\bdd\s+.*of=/dev/",
        r"\bmkfs\b",
        # System disruption
        r"\bshut(down|off)\b",
        r"\breboot\b",
        r"\binit\s+[06]",
        r"\bkill\s+-9\s+1\b",
        # Security weakening
        r"\bchmod\s+(-R\s+)?777\b",
        # Remote code execution via pipe
        r"\|\s*sh\b",
        r"\|\s*bash\b",
        r"\bcurl\b.*\|\s*bash",
        r"\bwget\b.*\|\s*sh",
        # PowerShell critical
        r"\bFormat-",
        r"\bStop-Computer\b",
        r"\bRestart-Computer\b",
        r"Set-ExecutionPolicy",
        r"\bInvoke-Expression\b",
        r"\bStart-Process\b.*-Verb\s+RunAs",
    )


@dataclass(frozen=True)
class ToolSecurityProfile:
    """Default security profile for a tool."""

    level: PermissionLevel


# ---------------------------------------------------------------------------
# Path extraction for file-arg commands
# ---------------------------------------------------------------------------

_FILE_ARG_COMMANDS = frozenset({
    "cat", "head", "tail", "less", "more", "file", "stat",
    "tree", "wc", "sort", "diff", "grep", "find",
})


def _extract_file_paths(command: str) -> list[str]:
    """Extract file paths from a shell command for security checking.

    Only applies to commands that read/write file contents.
    Skips flags (starting with -) and find predicates.
    """
    try:
        parts = shlex.split(command)
    except ValueError:
        parts = command.split()

    if not parts or parts[0] not in _FILE_ARG_COMMANDS:
        return []

    paths: list[str] = []
    for arg in parts[1:]:
        if arg.startswith("-"):
            continue
        if arg in ("{", "}", ";", "+", ","):
            continue
        paths.append(arg)
    return paths


# ---------------------------------------------------------------------------
# PathSandbox
# ---------------------------------------------------------------------------


class PathSandbox:
    """Check if a file path is within allowed bounds."""

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self._config = config or SecurityConfig()

    def check(self, path: str) -> SecurityDecision:
        resolved = Path(path).expanduser().resolve()

        for blocked in self._config.blocked_paths:
            blocked_resolved = Path(blocked).expanduser().resolve()
            try:
                resolved.relative_to(blocked_resolved)
                return SecurityDecision(
                    allowed=False,
                    reason=f"Path is in a protected directory: {blocked}",
                    requires_confirmation=True,
                )
            except ValueError:
                pass

        for root in self._config.allowed_roots:
            root_resolved = Path(root).expanduser().resolve()
            try:
                resolved.relative_to(root_resolved)
                return SecurityDecision(allowed=True, reason="Within allowed root")
            except ValueError:
                pass

        return SecurityDecision(
            allowed=False,
            reason=f"Path '{resolved}' is outside allowed roots",
            requires_confirmation=True,
        )


# ---------------------------------------------------------------------------
# SensitiveFileChecker
# ---------------------------------------------------------------------------


class SensitiveFileChecker:
    """Check if a file path is sensitive (credentials, secrets, etc.)."""

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self._config = config or SecurityConfig()
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self._config.sensitive_file_patterns
        ]

    def check(self, file_path: str) -> SecurityDecision:
        for pattern in self._compiled:
            if pattern.search(file_path):
                return SecurityDecision(
                    allowed=False,
                    reason=f"Sensitive file path detected: {file_path}",
                    requires_confirmation=True,
                )
        return SecurityDecision(allowed=True, reason="Path is not sensitive")


# ---------------------------------------------------------------------------
# CoreDangerDetector
# ---------------------------------------------------------------------------


class CoreDangerDetector:
    """Detect truly dangerous commands that must always be intercepted.

    This is a small, focused set of fatal patterns — NOT a comprehensive
    command whitelist. Broader command safety guidance is provided via
    system prompt (the model already knows what's safe/dangerous).
    """

    def __init__(self, config: SecurityConfig | None = None) -> None:
        self._config = config or SecurityConfig()
        self._compiled = [
            re.compile(p, re.IGNORECASE) for p in self._config.core_dangerous_patterns
        ]

    def check(self, command: str) -> SecurityDecision:
        stripped = command.strip()
        for pattern in self._compiled:
            if pattern.search(stripped):
                return SecurityDecision(
                    allowed=False,
                    reason="Dangerous command pattern detected",
                    requires_confirmation=True,
                )
        return SecurityDecision(allowed=True, reason="No dangerous pattern")


# ---------------------------------------------------------------------------
# SecurityGate — unified entry point
# ---------------------------------------------------------------------------


class SecurityGate:
    """Central security gate for all tool invocations.

    Three-layer check for CONTEXT_AWARE tools:
      1. CoreDangerDetector — fatal commands (sudo, rm -rf /, etc.)
      2. SensitiveFileChecker — .env, credentials, etc.
      3. PathSandbox — /etc/, ~/.ssh/, etc.

    Command whitelist semantics are handled via system prompt, not regex.
    """

    def __init__(
        self,
        config: SecurityConfig | None = None,
        confirm_callback: ConfirmCallback | None = None,
    ) -> None:
        self._config = config or SecurityConfig()
        self._path_sandbox = PathSandbox(self._config)
        self._sensitive_checker = SensitiveFileChecker(self._config)
        self._danger_detector = CoreDangerDetector(self._config)
        self._confirm_callback = confirm_callback
        self._profiles: dict[str, ToolSecurityProfile] = {}
        self._user_overrides: dict[str, PermissionLevel] = {}

    def set_profile(self, tool_name: str, profile: ToolSecurityProfile) -> None:
        self._profiles[tool_name] = profile

    def set_override(self, tool_name: str, level: PermissionLevel) -> None:
        self._user_overrides[tool_name] = level

    def _effective_level(self, tool_name: str) -> PermissionLevel:
        if tool_name in self._user_overrides:
            return self._user_overrides[tool_name]
        profile = self._profiles.get(tool_name)
        return profile.level if profile else PermissionLevel.ALWAYS_ASK

    async def check(self, tool_name: str, args: dict[str, Any]) -> SecurityDecision:
        level = self._effective_level(tool_name)

        # AUTO_APPROVE — always allow
        if level == PermissionLevel.AUTO_APPROVE:
            return SecurityDecision(allowed=True, reason="Auto-approved tool")

        # ALWAYS_ASK — always require confirmation
        if level == PermissionLevel.ALWAYS_ASK:
            return await self._ask_or_deny(
                tool_name, f"Tool '{tool_name}' requires confirmation"
            )

        # CONTEXT_AWARE — three-layer check

        # Shell tools — dangerous pattern + file path arguments
        if tool_name in ("Bash", "PowerShell"):
            command = args.get("command", "")

            # 1. Core dangerous pattern check
            danger = self._danger_detector.check(command)
            if not danger.allowed:
                return await self._ask_or_deny(tool_name, danger.reason)

            # 2. File path argument check
            for path in _extract_file_paths(command):
                sensitive = self._sensitive_checker.check(path)
                if not sensitive.allowed:
                    return await self._ask_or_deny(tool_name, sensitive.reason)
                sandbox = self._path_sandbox.check(path)
                if not sandbox.allowed:
                    return await self._ask_or_deny(tool_name, sandbox.reason)

            return SecurityDecision(allowed=True, reason="Command passed security checks")

        # File tools — sensitive file + path sandbox
        for param_key in ("file_path", "path"):
            if param_key in args:
                file_path = args[param_key]

                sensitive = self._sensitive_checker.check(file_path)
                if not sensitive.allowed:
                    return await self._ask_or_deny(tool_name, sensitive.reason)

                sandbox = self._path_sandbox.check(file_path)
                if not sandbox.allowed:
                    return await self._ask_or_deny(tool_name, sandbox.reason)

                return SecurityDecision(
                    allowed=True, reason="Context-aware: within sandbox"
                )

        # Unknown tool — always ask
        return await self._ask_or_deny(
            tool_name, f"Tool '{tool_name}' requires confirmation"
        )

    async def _ask_or_deny(
        self, tool_name: str, reason: str
    ) -> SecurityDecision:
        if self._confirm_callback:
            approved = await self._confirm_callback(tool_name, reason)
            if approved:
                return SecurityDecision(
                    allowed=True,
                    reason=reason,
                    warning=f"[Security] {reason} — user approved",
                )
            return SecurityDecision(
                allowed=False,
                reason=reason,
                warning=f"[Security] {reason} — user denied",
            )
        # No callback (non-interactive): soft-allow with warning
        return SecurityDecision(
            allowed=True,
            reason=reason,
            warning=f"[Security Warning] {reason}",
        )
