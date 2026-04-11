"""
Unit Tests for Exporter

Tests file export, directory structure creation, and export management.
"""

import tempfile
import zipfile
from pathlib import Path
from datetime import datetime
import os
from unittest import TestCase, mock

import pytest

from photo_cleaner.exporter import Exporter, StreamingExporter


class TestExporter(TestCase):
    """Tests for basic Exporter functionality."""

    def setUp(self):
        """Set up exporter with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_base = Path(self.temp_dir.name)
        self.exporter = Exporter(self.output_base)

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_exporter_initialization(self):
        """Test exporter initializes correctly."""
        assert self.exporter.output_base.exists()
        assert self.exporter.output_base == self.output_base


class TestStreamingExporter(TestCase):
    """Tests for StreamingExporter (ZIP export)."""

    def setUp(self):
        """Set up streaming exporter with temp directory."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.output_base = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up temp directory."""
        self.temp_dir.cleanup()

    def test_streaming_exporter_creates_zip(self):
        """Test that streaming exporter creates ZIP file."""
        exporter = StreamingExporter(self.output_base, archive_name="export.zip")

        # Create test files
        files = []
        try:
            for i in range(2):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(b"test image " + str(i).encode())
                f.flush()
                f.close()
                files.append(Path(f.name))

            # Export files using streaming exporter
            success, failure, errors, archive_path, cancelled = exporter.export_files_streaming(files)

            # Verify ZIP was created
            assert archive_path.exists()
            assert archive_path.stat().st_size > 0
            assert success == len(files)
            assert failure == 0

            # Verify contents
            with zipfile.ZipFile(archive_path) as zf:
                assert len(zf.namelist()) == len(files)
        finally:
            for f in files:
                f.unlink(missing_ok=True)

    def test_streaming_exporter_add_multiple_files(self):
        """Test adding multiple files to ZIP."""
        exporter = StreamingExporter(self.output_base, archive_name="multi.zip")

        files = []
        try:
            for i in range(3):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(b"data " + str(i).encode())
                f.flush()
                f.close()
                files.append(Path(f.name))

            # Export all files
            success, failure, errors, archive_path, cancelled = exporter.export_files_streaming(files)

            assert archive_path.exists()
            assert success == 3
            assert failure == 0
            with zipfile.ZipFile(archive_path) as zf:
                assert len(zf.namelist()) == 3
                assert all(name.count("/") == 3 for name in zf.namelist())
        finally:
            for f in files:
                f.unlink(missing_ok=True)

    def test_streaming_exporter_with_progress_callback(self):
        """Test progress callback in streaming exporter."""
        progress_calls = []

        def progress_callback(current, total, name):
            progress_calls.append((current, total, name))

        exporter = StreamingExporter(self.output_base, archive_name="progress.zip")

        files = []
        try:
            for i in range(2):
                f = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg")
                f.write(b"test")
                f.flush()
                f.close()
                files.append(Path(f.name))

            success, failure, errors, archive_path, cancelled = exporter.export_files_streaming(
                files, progress_callback=progress_callback
            )

            assert success == 2
            # Progress callback should have been called
            assert len(progress_calls) > 0
        finally:
            for f in files:
                f.unlink(missing_ok=True)

    def test_streaming_exporter_preserves_filename(self):
        """Test that ZIP preserves original filenames."""
        exporter = StreamingExporter(self.output_base, archive_name="names.zip")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            original_name = Path(f.name).name
            f.write(b"test")
            f.flush()
            source = Path(f.name)

        try:
            success, failure, errors, archive_path, cancelled = exporter.export_files_streaming([source])

            assert success == 1
            with zipfile.ZipFile(archive_path) as zf:
                names = zf.namelist()
                # Should contain the file (filename preserved)
                assert len(names) == 1
                assert original_name in names[0]
        finally:
            source.unlink(missing_ok=True)

    def test_streaming_exporter_uses_dated_zip_structure(self):
        """Test that streaming ZIP exports files into YYYY/MM/DD folders."""
        exporter = StreamingExporter(self.output_base, archive_name="dated.zip")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as f:
            f.write(b"test")
            f.flush()
            source = Path(f.name)

        try:
            target_dt = datetime(2024, 7, 13, 9, 30, 0)
            timestamp = target_dt.timestamp()
            os.utime(source, (timestamp, timestamp))

            success, failure, errors, archive_path, cancelled = exporter.export_files_streaming([source])

            assert success == 1
            assert failure == 0
            assert errors == []
            with zipfile.ZipFile(archive_path) as zf:
                names = zf.namelist()
                assert names == [f"2024/07/13/{source.name}"]
        finally:
            source.unlink(missing_ok=True)

    def test_streaming_exporter_empty_zip(self):
        """Test creating empty ZIP file."""
        exporter = StreamingExporter(self.output_base, archive_name="empty.zip")
        
        # Export empty list
        success, failure, errors, archive_path, cancelled = exporter.export_files_streaming([])

        # Should create valid ZIP (even if empty)
        assert archive_path.exists()
        assert success == 0
        assert failure == 0
        with zipfile.ZipFile(archive_path) as zf:
            assert len(zf.namelist()) == 0
