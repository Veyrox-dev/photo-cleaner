"""
Unit Tests for SessionManager

Tests core session persistence, undo/redo stack, and state management.
"""

import json
import tempfile
from pathlib import Path
from unittest import TestCase, mock

import pytest

from photo_cleaner.session_manager import (
    SessionManager,
    FileReference,
    UndoRedoStack,
)


class TestFileReference(TestCase):
    """Tests for FileReference data class."""

    def test_create_from_file(self):
        """Test creating file reference from actual file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()
            path = Path(f.name)

        try:
            ref = FileReference.create(path)
            assert ref.original_path == str(path)
            assert ref.file_hash is not None
            assert ref.file_size == 12  # "test content"
        finally:
            path.unlink()

    def test_create_from_file_with_base_path(self):
        """Test creating file reference with base path for relative path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_path = Path(tmpdir)
            file_path = base_path / "subdir" / "test.jpg"
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text("test")

            ref = FileReference.create(file_path, base_path)
            # Compare as strings to avoid path separator issues
            assert str(ref.relative_path).replace("\\", "/") == "subdir/test.jpg"
            assert ref.original_path == str(file_path)


class TestUndoRedoStack(TestCase):
    """Tests for UndoRedoStack."""

    def setUp(self):
        """Set up undo/redo stack."""
        self.stack = UndoRedoStack(max_history=10)

    def test_push_state(self):
        """Test pushing state onto stack."""
        from photo_cleaner.session_manager import SessionSnapshot
        snapshot = SessionSnapshot(timestamp="t1", description="s1", image_groups={})
        self.stack.push(snapshot)
        assert len(self.stack.undo_stack) == 1

    def test_undo(self):
        """Test undo operation."""
        from photo_cleaner.session_manager import SessionSnapshot
        snapshot1 = SessionSnapshot(timestamp="t1", description="s1", image_groups={})
        snapshot2 = SessionSnapshot(timestamp="t2", description="s2", image_groups={})
        self.stack.push(snapshot1)
        self.stack.push(snapshot2)

        undo_state = self.stack.undo()
        assert undo_state is not None
        assert len(self.stack.undo_stack) == 1
        assert len(self.stack.redo_stack) == 1

    def test_redo(self):
        """Test redo operation."""
        from photo_cleaner.session_manager import SessionSnapshot
        snapshot1 = SessionSnapshot(timestamp="t1", description="s1", image_groups={})
        snapshot2 = SessionSnapshot(timestamp="t2", description="s2", image_groups={})
        self.stack.push(snapshot1)
        self.stack.push(snapshot2)

        self.stack.undo()  # Undo snapshot2
        redo_state = self.stack.redo()
        assert redo_state is not None

    def test_redo_clears_on_new_push(self):
        """Test that new push clears redo stack."""
        from photo_cleaner.session_manager import SessionSnapshot
        snapshot1 = SessionSnapshot(timestamp="t1", description="s1", image_groups={})
        snapshot2 = SessionSnapshot(timestamp="t2", description="s2", image_groups={})
        snapshot3 = SessionSnapshot(timestamp="t3", description="s3", image_groups={})

        self.stack.push(snapshot1)
        self.stack.push(snapshot2)
        self.stack.undo()
        self.stack.push(snapshot3)

        assert len(self.stack.redo_stack) == 0

    def test_max_history_limit(self):
        """Test that stack respects max history."""
        from photo_cleaner.session_manager import SessionSnapshot
        stack = UndoRedoStack(max_history=3)
        for i in range(5):
            snapshot = SessionSnapshot(timestamp=f"t{i}", description=f"s{i}", image_groups={})
            stack.push(snapshot)

        assert len(stack.undo_stack) <= 3

    def test_can_undo_redo(self):
        """Test can_undo and can_redo methods."""
        from photo_cleaner.session_manager import SessionSnapshot
        snapshot1 = SessionSnapshot(timestamp="t1", description="s1", image_groups={})
        snapshot2 = SessionSnapshot(timestamp="t2", description="s2", image_groups={})
        assert not self.stack.can_undo()
        assert not self.stack.can_redo()

        self.stack.push(snapshot1)
        self.stack.push(snapshot2)
        assert self.stack.can_undo()
        assert not self.stack.can_redo()

        self.stack.undo()
        assert not self.stack.can_undo()
        assert self.stack.can_redo()


class TestSessionManager(TestCase):
    """Tests for SessionManager."""

    def setUp(self):
        """Set up session manager with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.session_dir = Path(self.temp_dir.name)
        self.session_manager = SessionManager(self.session_dir)

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_session_manager_initialization(self):
        """Test session manager initializes correctly."""
        assert self.session_manager is not None
        assert self.session_manager.sessions_dir.exists()

    def test_get_undo_stack(self):
        """Test getting undo/redo stack."""
        stack = self.session_manager.undo_redo_stack
        assert stack is not None
        assert hasattr(stack, "push")
        assert hasattr(stack, "undo")

    def test_auto_save_functionality(self):
        """Test auto-save basic functionality."""
        db_path = self.session_dir / "test.db"
        self.session_manager.create_session(db_path)
        ok = self.session_manager.save_auto(image_groups={}, db_path=db_path)
        assert ok is True

    def test_session_dir_created(self):
        """Test that session directory is created."""
        assert self.session_manager.sessions_dir.exists()
        assert self.session_manager.sessions_dir.is_dir()
