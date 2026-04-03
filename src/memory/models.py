"""Memory system data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class MemoryType(Enum):
    """Memory entry types."""

    USER = "user"  # User role, preferences, knowledge
    FEEDBACK = "feedback"  # Guidance: what to avoid/keep doing
    PROJECT = "project"  # Project context, decisions, deadlines
    REFERENCE = "reference"  # External system pointers


@dataclass
class MemoryEntry:
    """A single memory entry."""

    name: str
    description: str
    type: MemoryType
    content: str
    created: datetime = field(default_factory=datetime.now)
    updated: Optional[datetime] = None
    file_path: Optional[str] = None

    @property
    def filename(self) -> str:
        """Generate filename from name (uppercase)."""
        # Sanitize: uppercase, replace spaces/colons with underscores
        safe_name = self.name.upper().replace(" ", "_").replace(":", "_")
        return f"{safe_name}.md"

    def to_markdown(self) -> str:
        """Format as markdown file with YAML frontmatter."""
        updated_str = self.updated.strftime("%Y-%m-%d") if self.updated else ""
        frontmatter = f"""---
name: {self.name}
description: {self.description}
type: {self.type.value}
created: {self.created.strftime("%Y-%m-%d")}
updated: {updated_str}
---

"""
        return frontmatter + self.content

    def index_line(self) -> str:
        """Generate one-line index entry."""
        return f"- [{self.name}]({self.filename}) — {self.description}"

    @classmethod
    def from_markdown(
        cls, content: str, file_path: Optional[str] = None
    ) -> Optional["MemoryEntry"]:
        """Parse markdown file into MemoryEntry."""
        if not content.startswith("---"):
            return None

        parts = content.split("---", 2)
        if len(parts) < 3:
            return None

        frontmatter = parts[1].strip()
        body = parts[2].strip()

        # Parse YAML frontmatter (simple key-value parsing)
        meta = {}
        for line in frontmatter.split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                meta[key.strip()] = value.strip()

        # Required fields
        if "name" not in meta or "type" not in meta:
            return None

        try:
            mem_type = MemoryType(meta["type"])
        except ValueError:
            return None

        created = datetime.now()
        if "created" in meta and meta["created"]:
            try:
                created = datetime.strptime(meta["created"], "%Y-%m-%d")
            except ValueError:
                pass

        updated = None
        if "updated" in meta and meta["updated"]:
            try:
                updated = datetime.strptime(meta["updated"], "%Y-%m-%d")
            except ValueError:
                pass

        return cls(
            name=meta["name"],
            description=meta.get("description", ""),
            type=mem_type,
            content=body,
            created=created,
            updated=updated,
            file_path=file_path,
        )


@dataclass
class MemoryIndex:
    """Memory index (MEMORY.md)."""

    entries: list[MemoryEntry] = field(default_factory=list)
    max_lines: int = 200
    max_size: int = 25000  # ~25KB

    def to_markdown(self) -> str:
        """Format as MEMORY.md content."""
        lines = ["# Memory Index\n\n"]
        for entry in self.entries:
            line = entry.index_line()
            # Ensure line < 150 chars
            if len(line) > 150:
                line = line[:147] + "..."
            lines.append(line + "\n")
        return "".join(lines)

    def is_valid(self) -> bool:
        """Check if index is within limits."""
        content = self.to_markdown()
        lines = content.count("\n")
        return lines <= self.max_lines and len(content) <= self.max_size


@dataclass
class DreamResult:
    """Result of dream consolidation."""

    total: int
    created: int = 0
    updated: int = 0
    merged: int = 0
    pruned: int = 0

    def summary(self) -> str:
        """Generate summary string."""
        parts = [f"{self.total} memories total"]
        changes = []
        if self.created > 0:
            changes.append(f"{self.created} created")
        if self.updated > 0:
            changes.append(f"{self.updated} updated")
        if self.merged > 0:
            changes.append(f"{self.merged} merged")
        if self.pruned > 0:
            changes.append(f"{self.pruned} pruned")

        if changes:
            parts.append("| " + ", ".join(changes))
        else:
            parts.append("| no changes")

        return "**Dream complete:** " + " ".join(parts)
