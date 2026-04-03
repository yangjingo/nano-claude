"""Memory index management (MEMORY.md)."""

from __future__ import annotations

import os
from typing import Optional

from .models import MemoryEntry, MemoryIndex, MemoryType
from .storage import LocalStorage


def update_index(storage: LocalStorage, entry: MemoryEntry) -> None:
    """Update MEMORY.md index with new/updated entry.

    Args:
        storage: LocalStorage instance
        entry: Memory entry to add/update
    """
    index_path = storage.get_index_path()
    existing = load_index(storage)

    # Check if entry already exists
    found = False
    for i, e in enumerate(existing.entries):
        if e.name == entry.name:
            existing.entries[i] = entry
            found = True
            break

    if not found:
        existing.entries.append(entry)

    # Sort by type order: user, feedback, project, reference
    type_order = {
        MemoryType.USER: 0,
        MemoryType.FEEDBACK: 1,
        MemoryType.PROJECT: 2,
        MemoryType.REFERENCE: 3,
    }
    existing.entries.sort(
        key=lambda e: (type_order.get(e.type, 4), e.created), reverse=True
    )

    # Write index
    write_index(storage, existing)


def load_index(storage: LocalStorage) -> MemoryIndex:
    """Load MEMORY.md index.

    Args:
        storage: LocalStorage instance

    Returns:
        MemoryIndex with entries
    """
    index_path = storage.get_index_path()

    if not os.path.exists(index_path):
        return MemoryIndex()

    # Load all memories and create index
    entries = storage.load_all()
    return MemoryIndex(entries=entries)


def write_index(storage: LocalStorage, index: MemoryIndex) -> None:
    """Write MEMORY.md index file.

    Args:
        storage: LocalStorage instance
        index: MemoryIndex to write
    """
    index_path = storage.get_index_path()
    content = index.to_markdown()

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


def rebuild_index(storage: LocalStorage) -> int:
    """Rebuild MEMORY.md from all memory files.

    Args:
        storage: LocalStorage instance

    Returns:
        Number of entries in index
    """
    entries = storage.load_all()
    index = MemoryIndex(entries=entries)
    write_index(storage, index)
    return len(entries)


def prune_index(storage: LocalStorage) -> int:
    """Prune index to fit limits (200 lines, 25KB).

    Args:
        storage: LocalStorage instance

    Returns:
        Number of entries pruned
    """
    entries = storage.load_all()
    original_count = len(entries)

    # Sort by importance: user > feedback > project > reference
    # Then by recency
    type_priority = {
        MemoryType.USER: 100,
        MemoryType.FEEDBACK: 80,
        MemoryType.PROJECT: 60,
        MemoryType.REFERENCE: 40,
    }

    entries.sort(
        key=lambda e: (
            type_priority.get(e.type, 0),
            e.created,
        ),
        reverse=True,
    )

    # Trim to fit limits
    index = MemoryIndex()
    pruned = 0

    for entry in entries:
        index.entries.append(entry)
        if not index.is_valid():
            # Remove last entry that exceeded limits
            index.entries.pop()
            pruned += 1

    write_index(storage, index)
    return original_count - len(index.entries)
