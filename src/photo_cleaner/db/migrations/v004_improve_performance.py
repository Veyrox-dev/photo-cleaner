"""
Migration 004: Improve Performance

Optimizes database schema for better performance and user experience.
"""

import sqlite3

from .base import Migration


class V004ImprovePerformance(Migration):
    """Optimize schema for performance."""

    version = "004"
    name = "Improve Performance"
    description = "Add soft-delete columns, improve indexing, enable WAL mode"

    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration."""
        cursor = conn.cursor()

        # Enable WAL mode for better concurrency
        cursor.execute("PRAGMA journal_mode = WAL")

        # Check if soft-delete columns exist
        cursor.execute("PRAGMA table_info(files)")
        cols = {row[1] for row in cursor.fetchall()}

        # Add soft-delete columns if they don't exist
        if "is_deleted" not in cols:
            cursor.execute("ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT 0")

        if "trash_path" not in cols:
            cursor.execute("ALTER TABLE files ADD COLUMN trash_path TEXT")

        if "deleted_at" not in cols:
            cursor.execute("ALTER TABLE files ADD COLUMN deleted_at REAL")

        # Create indexes for soft-delete queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_deleted ON files(is_deleted)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_deleted_at ON files(deleted_at)")

        # Add composite index for efficient queries
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_files_status_locked ON files(file_status, is_locked)"
        )

        # Optimize analysis cache with eviction timestamp
        cursor.execute("PRAGMA table_info(analysis_cache)")
        cache_cols = {row[1] for row in cursor.fetchall()}

        if "evicted_at" not in cache_cols:
            cursor.execute("ALTER TABLE analysis_cache ADD COLUMN evicted_at REAL")

        # Create index for cache eviction
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_analysis_cache_accessed ON analysis_cache(last_accessed)")

        # Analyze database statistics for query optimization
        cursor.execute("ANALYZE")

        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration."""
        cursor = conn.cursor()

        # Drop new indexes
        cursor.execute("DROP INDEX IF EXISTS idx_analysis_cache_accessed")
        cursor.execute("DROP INDEX IF EXISTS idx_files_status_locked")
        cursor.execute("DROP INDEX IF EXISTS idx_files_deleted_at")
        cursor.execute("DROP INDEX IF EXISTS idx_files_deleted")

        # We can't easily remove columns in SQLite, so we recreate the table
        # This is done only if columns were added in this migration
        cursor.execute(
            """
            CREATE TABLE files_old AS
            SELECT 
                file_id, path, phash, file_hash, file_size,
                modified_time, created_time, exif_json,
                sharpness_score, overall_score, quality_score,
                sharpness_component, lighting_component, resolution_component,
                face_quality_component,
                file_status, is_locked, decided_at, indexed_at,
                is_recommended, keeper_source
            FROM files
            WHERE is_deleted = 0 OR is_deleted IS NULL
            """
        )

        cursor.execute("DROP TABLE files")
        cursor.execute("ALTER TABLE files_old RENAME TO files")

        # Recreate all indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_phash ON files(phash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(file_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_locked ON files(is_locked)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_quality ON files(quality_score)")

        conn.commit()
