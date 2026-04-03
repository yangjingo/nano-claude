"""Local memory storage operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from .models import MemoryEntry, MemoryType


# Default storage location: project root/.nano_claude/memory/
def get_memory_dir(project_root: Optional[str] = None) -> str:
    """Get memory directory path."""
    if project_root is None:
        # Find project root (where .git or CLAUDE.md exists)
        project_root = find_project_root()

    return os.path.join(project_root, ".nano_claude", "memory")


def find_project_root() -> str:
    """Find project root directory."""
    # Start from current directory
    cwd = os.getcwd()

    # Look for .git or CLAUDE.md
    path = Path(cwd)
    while path != path.parent:
        if (path / ".git").exists() or (path / "CLAUDE.md").exists():
            return str(path)
        path = path.parent

    # Fallback to cwd
    return cwd


class LocalStorage:
    """Local file system storage for memories."""

    def __init__(self, memory_dir: Optional[str] = None):
        """Initialize storage with memory directory."""
        self.memory_dir = memory_dir or get_memory_dir()
        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Create memory directory if not exists."""
        os.makedirs(self.memory_dir, exist_ok=True)

    def save(self, entry: MemoryEntry) -> str:
        """Save memory entry to file.

        Args:
            entry: Memory entry to save

        Returns:
            File path where entry was saved
        """
        self._validate(entry)

        file_path = os.path.join(self.memory_dir, entry.filename)
        content = entry.to_markdown()

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)

        entry.file_path = file_path
        return file_path

    def load(self, name: str) -> Optional[MemoryEntry]:
        """Load memory entry by name.

        Args:
            name: Memory entry name

        Returns:
            Memory entry or None if not found
        """
        filename = name.upper().replace(" ", "_").replace(":", "_") + ".md"
        file_path = os.path.join(self.memory_dir, filename)

        if not os.path.exists(file_path):
            return None

        return self._parse_file(file_path)

    def load_all(self) -> list[MemoryEntry]:
        """Load all memory entries.

        Returns:
            List of all memory entries, sorted by created date (newest first)
        """
        entries = []

        for filename in os.listdir(self.memory_dir):
            if filename.endswith(".md") and filename != "MEMORY.md":
                file_path = os.path.join(self.memory_dir, filename)
                entry = self._parse_file(file_path)
                if entry:
                    entries.append(entry)

        # Sort by created date, newest first
        entries.sort(key=lambda e: e.created, reverse=True)
        return entries

    def delete(self, name: str) -> bool:
        """Delete memory entry by name.

        Args:
            name: Memory entry name

        Returns:
            True if deleted, False if not found
        """
        filename = name.upper().replace(" ", "_").replace(":", "_") + ".md"
        file_path = os.path.join(self.memory_dir, filename)

        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False

    def exists(self, name: str) -> bool:
        """Check if memory entry exists.

        Args:
            name: Memory entry name

        Returns:
            True if exists
        """
        filename = name.upper().replace(" ", "_").replace(":", "_") + ".md"
        file_path = os.path.join(self.memory_dir, filename)
        return os.path.exists(file_path)

    def _parse_file(self, file_path: str) -> Optional[MemoryEntry]:
        """Parse memory file into entry."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            return MemoryEntry.from_markdown(content, file_path)
        except (IOError, OSError):
            return None

    def _validate(self, entry: MemoryEntry) -> None:
        """Validate memory entry."""
        if not entry.name or not entry.name.strip():
            raise ValueError("Memory name cannot be empty")

        if len(entry.description) > 150:
            raise ValueError(
                f"Description too long ({len(entry.description)} chars, max 150)"
            )

        if not entry.content or not entry.content.strip():
            raise ValueError("Memory content cannot be empty")

        if entry.type not in MemoryType:
            raise ValueError(f"Invalid memory type: {entry.type}")

    def get_index_path(self) -> str:
        """Get MEMORY.md index file path."""
        return os.path.join(self.memory_dir, "MEMORY.md")

    def count(self) -> int:
        """Count memory entries."""
        count = 0
        for filename in os.listdir(self.memory_dir):
            if filename.endswith(".md") and filename != "MEMORY.md":
                count += 1
        return count

    def list_files(self) -> list[str]:
        """List all memory files."""
        files = []
        for filename in os.listdir(self.memory_dir):
            if filename.endswith(".md") and filename != "MEMORY.md":
                files.append(filename)
        return sorted(files)
