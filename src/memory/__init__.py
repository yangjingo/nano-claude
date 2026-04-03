"""Memory system for persistent user preferences and project context.

Storage location: .nano_claude/memory/
"""

from __future__ import annotations

from .models import DreamResult, MemoryEntry, MemoryIndex, MemoryType
from .storage import LocalStorage, get_memory_dir, find_project_root
from .index import update_index, load_index, write_index, rebuild_index, prune_index

__all__ = [
    "MemoryType",
    "MemoryEntry",
    "MemoryIndex",
    "DreamResult",
    "LocalStorage",
    "get_memory_dir",
    "find_project_root",
    "update_index",
    "load_index",
    "write_index",
    "rebuild_index",
    "prune_index",
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
