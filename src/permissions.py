"""Permission system for nano-claude tools.

Provides:
  - ToolPermissionContext: lightweight deny-list (legacy, used by mirrored registry)
  - build_security_gate(): factory that bridges the old system to the new SecurityGate
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


@dataclass(frozen=True)
class ToolPermissionContext:
    deny_names: frozenset[str] = field(default_factory=frozenset)
    deny_prefixes: tuple[str, ...] = ()

    @classmethod
    def from_iterables(
        cls, deny_names: list[str] | None = None, deny_prefixes: list[str] | None = None
    ) -> "ToolPermissionContext":
        return cls(
            deny_names=frozenset(name.lower() for name in (deny_names or [])),
            deny_prefixes=tuple(prefix.lower() for prefix in (deny_prefixes or [])),
        )

    def blocks(self, tool_name: str) -> bool:
        lowered = tool_name.lower()
        return lowered in self.deny_names or any(
            lowered.startswith(prefix) for prefix in self.deny_prefixes
        )


# ---------------------------------------------------------------------------
# Security gate factory
# ---------------------------------------------------------------------------

ConfirmCallback = Callable[[str, str], Coroutine[Any, Any, bool]]


def build_security_gate(
    permission_context: ToolPermissionContext | None = None,
    confirm_callback: ConfirmCallback | None = None,
) -> Any:
    """Build a SecurityGate with default tool profiles.

    Bridges the legacy ToolPermissionContext deny-list into the new
    SecurityGate system by applying deny_names as ALWAYS_ASK overrides.

    Args:
        permission_context: Optional legacy deny-list context.
        confirm_callback: Async callback for user confirmation prompts.

    Returns:
        Configured SecurityGate instance.
    """
    from .tools.security import (
        SecurityGate,
        SecurityConfig,
        ToolSecurityProfile,
        PermissionLevel,
    )

    gate = SecurityGate(confirm_callback=confirm_callback)

    # Apply deny_names as ALWAYS_ASK overrides
    if permission_context:
        for name in permission_context.deny_names:
            gate.set_override(name, PermissionLevel.ALWAYS_ASK)

    # Default security profiles for built-in tools
    gate.set_profile("Read", ToolSecurityProfile(level=PermissionLevel.CONTEXT_AWARE))
    gate.set_profile("Write", ToolSecurityProfile(level=PermissionLevel.CONTEXT_AWARE))
    gate.set_profile("Edit", ToolSecurityProfile(level=PermissionLevel.CONTEXT_AWARE))
    gate.set_profile("Bash", ToolSecurityProfile(level=PermissionLevel.CONTEXT_AWARE))
    gate.set_profile("PowerShell", ToolSecurityProfile(level=PermissionLevel.CONTEXT_AWARE))
    gate.set_profile("Glob", ToolSecurityProfile(level=PermissionLevel.AUTO_APPROVE))
    gate.set_profile("Grep", ToolSecurityProfile(level=PermissionLevel.AUTO_APPROVE))

    return gate
