"""
Migration 002: Add Quality Scoring

Adds detailed quality analysis columns for image scoring.
"""

import sqlite3

from .base import Migration


class V002AddQualityScoring(Migration):
    """Add quality scoring columns."""

    version = "002"
    name = "Add Quality Scoring"
    description = "Add quality_score and component scores to files table"

    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration."""
        cursor = conn.cursor()

        # Check if columns exist before adding
        cursor.execute("PRAGMA table_info(files)")
        cols = {row[1] for row in cursor.fetchall()}

        # Add quality score columns if they don't exist
        columns_to_add = {
            "quality_score": "REAL",
            "sharpness_component": "REAL",
            "lighting_component": "REAL",
            "resolution_component": "REAL",
            "face_quality_component": "REAL",
        }

        for col_name, col_type in columns_to_add.items():
            if col_name not in cols:
                cursor.execute(f"ALTER TABLE files ADD COLUMN {col_name} {col_type}")

        # Create index on quality_score for efficient sorting
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_quality ON files(quality_score)")

        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration."""
        cursor = conn.cursor()

        # SQLite doesn't support DROP COLUMN in older versions
        # So we need to recreate the table without the quality columns
        cursor.execute("DROP INDEX IF EXISTS idx_files_quality")

        # Create temporary table with old schema
        cursor.execute(
            """
            CREATE TABLE files_old AS
            SELECT 
                file_id, path, phash, file_hash, file_size,
                modified_time, created_time, exif_json,
                sharpness_score, overall_score,
                file_status, is_locked, decided_at, indexed_at,
                is_recommended, keeper_source
            FROM files
            """
        )

        # Drop original table
        cursor.execute("DROP TABLE files")

        # Rename old table to files
        cursor.execute("ALTER TABLE files_old RENAME TO files")

        # Recreate indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_phash ON files(phash)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_status ON files(file_status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_files_locked ON files(is_locked)")

        conn.commit()
