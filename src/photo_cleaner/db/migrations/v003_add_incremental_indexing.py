"""
Migration 003: Add Incremental Indexing & Caching

Adds tables for incremental scanning and analysis result caching.
"""

import sqlite3

from .base import Migration


class V003AddIncrementalIndexing(Migration):
    """Add incremental indexing and caching tables."""

    version = "003"
    name = "Add Incremental Indexing & Caching"
    description = "Create file_hashes, scan_history, analysis_cache, file_hash_mapping tables"

    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration."""
        cursor = conn.cursor()

        # File hashes table for incremental indexing
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hashes (
                hash_id TEXT PRIMARY KEY,
                file_path TEXT UNIQUE NOT NULL,
                phash TEXT,
                md5 TEXT,
                file_size INTEGER,
                modified_time REAL,
                indexed_at REAL DEFAULT (unixepoch())
            )
            """
        )

        # Scan history for tracking incremental scans
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS scan_history (
                scan_id TEXT PRIMARY KEY,
                scan_time REAL DEFAULT (unixepoch()),
                input_folder TEXT NOT NULL,
                total_files INTEGER,
                new_files INTEGER,
                hashed_files INTEGER,
                duplicates_found INTEGER
            )
            """
        )

        # Analysis cache for caching quality analysis results
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS analysis_cache (
                hash_key TEXT PRIMARY KEY,
                file_hash TEXT UNIQUE NOT NULL,
                quality_score REAL,
                face_quality TEXT,
                sharpness REAL,
                lighting_score REAL,
                cached_at REAL DEFAULT (unixepoch()),
                hit_count INTEGER DEFAULT 0,
                last_accessed REAL DEFAULT (unixepoch())
            )
            """
        )

        # File hash mapping for linking files to cached analyses
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS file_hash_mapping (
                mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER NOT NULL,
                hash_key TEXT NOT NULL,
                file_path TEXT NOT NULL,
                FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
                FOREIGN KEY (hash_key) REFERENCES analysis_cache(hash_key) ON DELETE CASCADE,
                UNIQUE(file_id, hash_key)
            )
            """
        )

        # Create indexes for performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hashes_path ON file_hashes(file_path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_scan_history_folder ON scan_history(input_folder)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_hash ON analysis_cache(file_hash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash_mapping_file ON file_hash_mapping(file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_file_hash_mapping_hash ON file_hash_mapping(hash_key)")

        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration."""
        cursor = conn.cursor()

        # Drop indexes
        cursor.execute("DROP INDEX IF EXISTS idx_file_hash_mapping_hash")
        cursor.execute("DROP INDEX IF EXISTS idx_file_hash_mapping_file")
        cursor.execute("DROP INDEX IF EXISTS idx_analysis_cache_hash")
        cursor.execute("DROP INDEX IF EXISTS idx_scan_history_folder")
        cursor.execute("DROP INDEX IF EXISTS idx_file_hashes_path")

        # Drop tables
        cursor.execute("DROP TABLE IF EXISTS file_hash_mapping")
        cursor.execute("DROP TABLE IF EXISTS analysis_cache")
        cursor.execute("DROP TABLE IF EXISTS scan_history")
        cursor.execute("DROP TABLE IF EXISTS file_hashes")

        conn.commit()
