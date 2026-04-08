"""Session notes for in-conversation memory capture.

L3: Takes notes during conversation to avoid rushed summarization
when the context window is nearly full.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


# The 9-module template for session notes
NOTE_MODULES = [
    "workflow",
    "learnings",
    "errors_corrections",
    "current_state",
    "decisions",
    "blockers",
    "next_steps",
    "files_touched",
    "user_preferences",
]

MODULE_TITLES = {
    "workflow": "Workflow",
    "learnings": "Learnings",
    "errors_corrections": "Errors & Corrections",
    "current_state": "Current State",
    "decisions": "Decisions",
    "blockers": "Blockers",
    "next_steps": "Next Steps",
    "files_touched": "Files Touched",
    "user_preferences": "User Preferences",
}


@dataclass
class SessionNotes:
    """In-conversation notes following the 9-module template.

    Each module is a list of string entries, accumulated during the session.
    """

    session_id: str = ""
    started_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    _entries: dict[str, list[str]] = field(
        default_factory=lambda: {m: [] for m in NOTE_MODULES}
    )

    def add(self, module: str, text: str) -> None:
        """Add an entry to a note module.

        Args:
            module: One of NOTE_MODULES keys.
            text: Entry text.
        """
        if module not in self._entries:
            module = _fuzzy_match_module(module)
            if module is None:
                return

        self._entries[module].append(text)
        self.updated_at = datetime.now()

    def get(self, module: str) -> list[str]:
        """Get entries for a module."""
        return list(self._entries.get(module, []))

    def get_all(self) -> dict[str, list[str]]:
        """Get all module entries."""
        return {k: list(v) for k, v in self._entries.items()}

    def has_content(self) -> bool:
        """Check if any module has entries."""
        return any(entries for entries in self._entries.values())

    def to_markdown(self) -> str:
        """Render notes as markdown."""
        lines = [
            f"# Session Notes",
            f"",
            f"> Session: {self.session_id or 'unknown'}",
            f"> Started: {self.started_at.strftime('%Y-%m-%d %H:%M')}",
            f"> Updated: {self.updated_at.strftime('%Y-%m-%d %H:%M')}",
            f"",
        ]

        for module in NOTE_MODULES:
            entries = self._entries.get(module, [])
            if not entries:
                continue

            title = MODULE_TITLES.get(module, module.replace("_", " ").title())
            lines.append(f"### {title}")
            lines.append("")
            for entry in entries:
                lines.append(f"- {entry}")
            lines.append("")

        return "\n".join(lines)

    @classmethod
    def from_markdown(cls, content: str, session_id: str = "") -> SessionNotes:
        """Parse markdown content back into SessionNotes.

        Args:
            content: Markdown content from a previous session note.
            session_id: Optional session ID override.

        Returns:
            SessionNotes instance.
        """
        notes = cls(session_id=session_id)
        current_module = None

        for line in content.splitlines():
            stripped = line.strip()

            if stripped.startswith("### "):
                title = stripped[4:].lower()
                # Reverse lookup: title → module key
                current_module = None
                for key, val in MODULE_TITLES.items():
                    if val.lower() == title:
                        current_module = key
                        break
                continue

            if current_module and stripped.startswith("- "):
                notes.add(current_module, stripped[2:])

        return notes

    def merge(self, other: SessionNotes) -> None:
        """Merge another SessionNotes into this one.

        Deduplicates entries within each module.

        Args:
            other: Another SessionNotes to merge.
        """
        for module in NOTE_MODULES:
            existing = set(self._entries[module])
            for entry in other._entries.get(module, []):
                if entry not in existing:
                    self._entries[module].append(entry)
                    existing.add(entry)

        self.updated_at = datetime.now()

    def extract_preferences(self) -> list[str]:
        """Extract user preference signals from notes.

        Returns:
            List of preference entries.
        """
        prefs = list(self._entries.get("user_preferences", []))
        # Also check decisions for preference-like entries
        for decision in self._entries.get("decisions", []):
            if any(
                kw in decision.lower()
                for kw in ["prefer", "always", "never", "不要", "总是"]
            ):
                prefs.append(decision)
        return prefs

    def extract_errors(self) -> list[str]:
        """Extract error/correction signals from notes.

        Returns:
            List of error entries.
        """
        return list(self._entries.get("errors_corrections", []))


def _fuzzy_match_module(name: str) -> Optional[str]:
    """Fuzzy match a module name to a valid NOTE_MODULES key.

    Args:
        name: Module name to match.

    Returns:
        Matched module key or None.
    """
    name_lower = name.lower().replace(" ", "_").replace("-", "_")

    # Exact match
    if name_lower in NOTE_MODULES:
        return name_lower

    # Prefix match
    for module in NOTE_MODULES:
        if module.startswith(name_lower) or name_lower.startswith(module):
            return module

    # Title match
    for key, title in MODULE_TITLES.items():
        if title.lower() == name_lower:
            return key

    return None
