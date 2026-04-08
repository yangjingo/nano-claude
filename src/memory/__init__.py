"""Memory system for persistent user preferences and project context.

7-layer architecture:
  L1: Spill to Disk (large output offloading)
  L2: Cache Micro-compression (API dependency)
  L3: Session Notes (in-conversation capture)
  L4: Summary Agent (context window protection)
  L5: Persistent Memory (file-based storage)
  L6: Blood Moon (/dream consolidation engine)
  L7: Cache Alignment (runtime optimization)

Storage location: .nano_claude/memory/
"""

from __future__ import annotations

from .models import DreamResult, MemoryEntry, MemoryIndex, MemoryType
from .storage import LocalStorage, get_memory_dir, find_project_root
from .index import update_index, load_index, write_index, rebuild_index, prune_index
from .keywords import KeywordMatcher, MatchedSignal, SignalType
from .notes import SessionNotes, NOTE_MODULES
from .dreamer import BloodMoon
from .scheduler import (
    BloodMoonScheduler,
    CronExpression,
    TokenAccumulator,
    IdleDetector,
)

__all__ = [
    # Models
    "MemoryType",
    "MemoryEntry",
    "MemoryIndex",
    "DreamResult",
    # Storage
    "LocalStorage",
    "get_memory_dir",
    "find_project_root",
    # Index
    "update_index",
    "load_index",
    "write_index",
    "rebuild_index",
    "prune_index",
    # Keywords (L6)
    "KeywordMatcher",
    "MatchedSignal",
    "SignalType",
    # Notes (L3)
    "SessionNotes",
    "NOTE_MODULES",
    # Dreamer (L6)
    "BloodMoon",
    # Scheduler (L6)
    "BloodMoonScheduler",
    "CronExpression",
    "TokenAccumulator",
    "IdleDetector",
]


# Convenience functions
def save_memory(
    name: str,
    description: str,
    type: MemoryType,
    content: str,
    storage: LocalStorage | None = None,
) -> MemoryEntry:
    """Save a memory entry.

    Args:
        name: Memory name
        description: One-line description (< 150 chars)
        type: Memory type (user/feedback/project/reference)
        content: Memory content
        storage: Optional LocalStorage instance

    Returns:
        Saved MemoryEntry
    """
    if storage is None:
        storage = LocalStorage()

    entry = MemoryEntry(
        name=name,
        description=description,
        type=type,
        content=content,
    )

    storage.save(entry)
    update_index(storage, entry)
    return entry


def load_memories(storage: LocalStorage | None = None) -> list[MemoryEntry]:
    """Load all memories.

    Args:
        storage: Optional LocalStorage instance

    Returns:
        List of MemoryEntry
    """
    if storage is None:
        storage = LocalStorage()
    return storage.load_all()


def get_memory(name: str, storage: LocalStorage | None = None) -> MemoryEntry | None:
    """Get a specific memory by name.

    Args:
        name: Memory name
        storage: Optional LocalStorage instance

    Returns:
        MemoryEntry or None
    """
    if storage is None:
        storage = LocalStorage()
    return storage.load(name)


def delete_memory(name: str, storage: LocalStorage | None = None) -> bool:
    """Delete a memory by name.

    Args:
        name: Memory name
        storage: Optional LocalStorage instance

    Returns:
        True if deleted
    """
    if storage is None:
        storage = LocalStorage()

    deleted = storage.delete(name)
    if deleted:
        rebuild_index(storage)
    return deleted


def memory_summary(storage: LocalStorage | None = None) -> str:
    """Generate memory summary.

    Args:
        storage: Optional LocalStorage instance

    Returns:
        Summary string
    """
    if storage is None:
        storage = LocalStorage()

    entries = storage.load_all()
    total = len(entries)

    by_type = {}
    for entry in entries:
        t = entry.type.value
        by_type[t] = by_type.get(t, 0) + 1

    lines = [f"Total memories: {total}"]
    for t, count in sorted(by_type.items()):
        lines.append(f"  {t}: {count}")

    return "\n".join(lines)


def dream(
    transcript_files: list[str] | None = None,
    storage: LocalStorage | None = None,
) -> DreamResult:
    """Trigger blood moon consolidation.

    Args:
        transcript_files: Specific transcript files to scan (auto-discovers if None).
        storage: Optional LocalStorage instance.

    Returns:
        DreamResult with consolidation statistics.
    """
    if storage is None:
        storage = LocalStorage()

    moon = BloodMoon(storage=storage)
    return moon.consolidate(transcript_files=transcript_files)
