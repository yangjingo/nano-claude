"""Tests for memory system."""

import os
import tempfile
import unittest
from datetime import datetime

from src.memory import (
    MemoryType,
    MemoryEntry,
    MemoryIndex,
    LocalStorage,
    save_memory,
    load_memories,
    delete_memory,
    memory_summary,
    rebuild_index,
)


class MemoryModelsTest(unittest.TestCase):
    """Test memory data models."""

    def test_memory_type_values(self):
        """Test MemoryType enum values."""
        self.assertEqual(MemoryType.USER.value, "user")
        self.assertEqual(MemoryType.FEEDBACK.value, "feedback")
        self.assertEqual(MemoryType.PROJECT.value, "project")
        self.assertEqual(MemoryType.REFERENCE.value, "reference")

    def test_memory_entry_filename(self):
        """Test filename generation (uppercase)."""
        entry = MemoryEntry(
            name="User Role",
            description="Test",
            type=MemoryType.USER,
            content="Test content",
        )
        self.assertEqual(entry.filename, "USER_ROLE.md")

        entry2 = MemoryEntry(
            name="feedback: testing",
            description="Test",
            type=MemoryType.FEEDBACK,
            content="Test",
        )
        self.assertEqual(
            entry2.filename, "FEEDBACK__TESTING.md"
        )  # colon + space = two underscores

    def test_memory_entry_to_markdown(self):
        """Test markdown serialization."""
        entry = MemoryEntry(
            name="Test Memory",
            description="A test memory",
            type=MemoryType.FEEDBACK,
            content="Don't mock the database.\n\n**Why:** Incident last quarter.",
            created=datetime(2026, 4, 3),
        )
        md = entry.to_markdown()

        self.assertIn("---", md)
        self.assertIn("name: Test Memory", md)
        self.assertIn("type: feedback", md)
        self.assertIn("Don't mock the database", md)

    def test_memory_entry_from_markdown(self):
        """Test markdown deserialization."""
        md = """---
name: Test Memory
description: A test memory
type: feedback
created: 2026-04-03
updated: 2026-04-05
---

Don't mock the database.

**Why:** Incident last quarter.
"""

        entry = MemoryEntry.from_markdown(md)
        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Test Memory")
        self.assertEqual(entry.type, MemoryType.FEEDBACK)
        self.assertIn("Don't mock", entry.content)

    def test_memory_entry_invalid_markdown(self):
        """Test invalid markdown handling."""
        # No frontmatter
        entry = MemoryEntry.from_markdown("Just content")
        self.assertIsNone(entry)

        # Missing required fields
        invalid_md = "---\nname: Test\n---\nContent"
        entry = MemoryEntry.from_markdown(invalid_md)
        self.assertIsNone(entry)

    def test_memory_index_line(self):
        """Test index line generation."""
        entry = MemoryEntry(
            name="User Role",
            description="Data scientist",
            type=MemoryType.USER,
            content="Test",
        )
        line = entry.index_line()
        self.assertEqual(line, "- [User Role](USER_ROLE.md) — Data scientist")


class LocalStorageTest(unittest.TestCase):
    """Test local storage operations."""

    def setUp(self):
        """Set up temp directory for tests."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = LocalStorage(self.temp_dir)

    def tearDown(self):
        """Clean up temp directory."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_and_load(self):
        """Test save and load operations."""
        entry = MemoryEntry(
            name="Test Entry",
            description="A test",
            type=MemoryType.USER,
            content="This is test content.",
        )

        # Save
        path = self.storage.save(entry)
        self.assertTrue(os.path.exists(path))

        # Load
        loaded = self.storage.load("Test Entry")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.name, "Test Entry")
        self.assertEqual(loaded.content, "This is test content.")

    def test_load_all(self):
        """Test loading all entries."""
        # Save multiple entries
        for i in range(3):
            entry = MemoryEntry(
                name=f"Entry {i}",
                description=f"Test {i}",
                type=MemoryType.USER,
                content=f"Content {i}",
            )
            self.storage.save(entry)

        # Load all
        entries = self.storage.load_all()
        self.assertEqual(len(entries), 3)

    def test_delete(self):
        """Test delete operation."""
        entry = MemoryEntry(
            name="To Delete",
            description="Test",
            type=MemoryType.USER,
            content="Test",
        )
        self.storage.save(entry)

        # Delete
        deleted = self.storage.delete("To Delete")
        self.assertTrue(deleted)

        # Check it's gone
        loaded = self.storage.load("To Delete")
        self.assertIsNone(loaded)

    def test_exists(self):
        """Test exists check."""
        entry = MemoryEntry(
            name="Exists Test",
            description="Test",
            type=MemoryType.USER,
            content="Test",
        )
        self.storage.save(entry)

        self.assertTrue(self.storage.exists("Exists Test"))
        self.assertFalse(self.storage.exists("Not Exists"))

    def test_validation_empty_name(self):
        """Test validation rejects empty name."""
        entry = MemoryEntry(
            name="",
            description="Test",
            type=MemoryType.USER,
            content="Test",
        )
        with self.assertRaises(ValueError):
            self.storage.save(entry)

    def test_validation_long_description(self):
        """Test validation rejects long description."""
        entry = MemoryEntry(
            name="Test",
            description="x" * 200,  # > 150 chars
            type=MemoryType.USER,
            content="Test",
        )
        with self.assertRaises(ValueError):
            self.storage.save(entry)

    def test_validation_empty_content(self):
        """Test validation rejects empty content."""
        entry = MemoryEntry(
            name="Test",
            description="Test",
            type=MemoryType.USER,
            content="",
        )
        with self.assertRaises(ValueError):
            self.storage.save(entry)


class ConvenienceFunctionsTest(unittest.TestCase):
    """Test convenience functions."""

    def setUp(self):
        """Set up temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = LocalStorage(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_save_memory_function(self):
        """Test save_memory convenience function."""
        entry = save_memory(
            name="Test",
            description="Test desc",
            type=MemoryType.USER,
            content="Test content",
            storage=self.storage,
        )

        self.assertIsNotNone(entry)
        self.assertEqual(entry.name, "Test")

        # Check index was updated
        index_path = self.storage.get_index_path()
        self.assertTrue(os.path.exists(index_path))

    def test_load_memories_function(self):
        """Test load_memories convenience function."""
        save_memory("A", "Desc", MemoryType.USER, "Content", self.storage)
        save_memory("B", "Desc", MemoryType.FEEDBACK, "Content", self.storage)

        entries = load_memories(self.storage)
        self.assertEqual(len(entries), 2)

    def test_delete_memory_function(self):
        """Test delete_memory convenience function."""
        save_memory("Test", "Desc", MemoryType.USER, "Content", self.storage)

        deleted = delete_memory("Test", self.storage)
        self.assertTrue(deleted)

        entries = load_memories(self.storage)
        self.assertEqual(len(entries), 0)

    def test_memory_summary_function(self):
        """Test memory_summary convenience function."""
        save_memory("A", "Desc", MemoryType.USER, "Content", self.storage)
        save_memory("B", "Desc", MemoryType.FEEDBACK, "Content", self.storage)
        save_memory("C", "Desc", MemoryType.PROJECT, "Content", self.storage)

        summary = memory_summary(self.storage)
        self.assertIn("Total memories: 3", summary)
        self.assertIn("user: 1", summary)
        self.assertIn("feedback: 1", summary)
        self.assertIn("project: 1", summary)


class MemoryIndexTest(unittest.TestCase):
    """Test memory index."""

    def setUp(self):
        """Set up temp directory."""
        self.temp_dir = tempfile.mkdtemp()
        self.storage = LocalStorage(self.temp_dir)

    def tearDown(self):
        """Clean up."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_index_to_markdown(self):
        """Test index markdown generation."""
        entries = [
            MemoryEntry("A", "Desc A", MemoryType.USER, "Content"),
            MemoryEntry("B", "Desc B", MemoryType.FEEDBACK, "Content"),
        ]
        index = MemoryIndex(entries=entries)
        md = index.to_markdown()

        self.assertIn("# Memory Index", md)
        self.assertIn("[A](A.md)", md)
        self.assertIn("[B](B.md)", md)

    def test_rebuild_index(self):
        """Test rebuild_index function."""
        # Save entries
        self.storage.save(MemoryEntry("A", "Desc", MemoryType.USER, "Content"))
        self.storage.save(MemoryEntry("B", "Desc", MemoryType.FEEDBACK, "Content"))

        count = rebuild_index(self.storage)
        self.assertEqual(count, 2)

        # Check index file exists
        index_path = self.storage.get_index_path()
        self.assertTrue(os.path.exists(index_path))


if __name__ == "__main__":
    unittest.main()
