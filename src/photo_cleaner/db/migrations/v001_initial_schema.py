"""
Migration 001: Initial Schema

Creates the core tables for PhotoCleaner:
- files: Main file index
- duplicates: Duplicate groups
- metadata: Configuration
- status_history: Action tracking
"""

import sqlite3

from .base import Migration


class V001InitialSchema(Migration):
    """Initial database schema."""

    version = "001"
    name = "Initial Schema"
    description = "Create core tables: files, duplicates, metadata, status_history"

    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration."""
        cursor = conn.cursor()

        # Files table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS files (
                file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE,
                phash TEXT,
                file_hash TEXT,
                file_size INTEGER,
                modified_time REAL,
                created_time REAL,
                exif_json TEXT,
                sharpness_score REAL,
                overall_score REAL,
                file_status TEXT NOT NULL DEFAULT 'UNDECIDED',
                is_locked BOOLEAN NOT NULL DEFAULT 0,
                decided_at REAL,
                indexed_at REAL DEFAULT (unixepoch()),
                is_recommended BOOLEAN DEFAULT 0,
                keeper_source TEXT DEFAULT 'undecided'
            )
            """
        )

        # Duplicates table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS duplicates (
                duplicate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                similarity_score REAL,
                is_keeper BOOLEAN DEFAULT 0,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
            )
            """
        )

        # Metadata table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS metadata (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )

        # Status history table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS status_history (
                history_id INTEGER PRIMARY KEY AUTOINCREMENT,
                action_id TEXT NOT NULL,
                file_id INTEGER NOT NULL,
                file_path TEXT NOT NULL,
                old_status TEXT,
                new_status TEXT,
                old_locked BOOLEAN,
                new_locked BOOLEAN,
                reason TEXT,
                created_at REAL DEFAULT (unixepoch()),
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
            )
            """
        )

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_phash ON files(phash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(file_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_locked ON files(is_locked)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicates_group ON duplicates(group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_duplicates_file ON duplicates(file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_action ON status_history(action_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_history_file ON status_history(file_id)")

        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration."""
        cursor = conn.cursor()

        # Drop indexes
        cursor.execute("DROP INDEX IF EXISTS idx_history_file")
        cursor.execute("DROP INDEX IF EXISTS idx_history_action")
        cursor.execute("DROP INDEX IF EXISTS idx_duplicates_file")
        cursor.execute("DROP INDEX IF EXISTS idx_duplicates_group")
        cursor.execute("DROP INDEX IF EXISTS idx_files_locked")
        cursor.execute("DROP INDEX IF EXISTS idx_files_status")
        cursor.execute("DROP INDEX IF EXISTS idx_files_path")
        cursor.execute("DROP INDEX IF EXISTS idx_files_phash")

        # Drop tables
        cursor.execute("DROP TABLE IF EXISTS status_history")
        cursor.execute("DROP TABLE IF EXISTS metadata")
        cursor.execute("DROP TABLE IF EXISTS duplicates")
        cursor.execute("DROP TABLE IF EXISTS files")

        conn.commit()
