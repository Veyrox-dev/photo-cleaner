"""
Migration 005: Add EXIF geo grouping tables

Adds schema objects required for EXIF smart grouping and reverse geocoding.
"""

import sqlite3

from .base import Migration


class V005AddExifGeoGrouping(Migration):
    """Create EXIF geo grouping tables and indexes."""

    version = "005"
    name = "Add EXIF Geo Grouping"
    description = "Create geo_groups, geo_group_images, geocoding_cache, grouping_fallback_log tables"

    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration."""
        cursor = conn.cursor()

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                scan_session_id TEXT,
                group_key TEXT UNIQUE NOT NULL,
                latitude REAL,
                longitude REAL,
                location_name TEXT,
                city TEXT,
                country TEXT,
                date_start DATE,
                date_end DATE,
                image_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS geo_group_images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                geo_group_id INTEGER NOT NULL REFERENCES geo_groups(id) ON DELETE CASCADE,
                file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
                UNIQUE(geo_group_id, file_id)
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS geocoding_cache (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coordinates TEXT UNIQUE NOT NULL,
                location_name TEXT,
                city TEXT,
                country TEXT,
                raw_response TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                ttl_hours INTEGER DEFAULT 168,
                hits INTEGER DEFAULT 0
            )
            """
        )

        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS grouping_fallback_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE,
                tier_used INTEGER,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_groups_key ON geo_groups(group_key)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_groups_location ON geo_groups(location_name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_groups_session ON geo_groups(scan_session_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_group_images_group ON geo_group_images(geo_group_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geo_group_images_file ON geo_group_images(file_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_geocoding_cache_coords ON geocoding_cache(coordinates)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_grouping_fallback_file ON grouping_fallback_log(file_id)")

        conn.commit()

    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration."""
        cursor = conn.cursor()

        cursor.execute("DROP INDEX IF EXISTS idx_grouping_fallback_file")
        cursor.execute("DROP INDEX IF EXISTS idx_geocoding_cache_coords")
        cursor.execute("DROP INDEX IF EXISTS idx_geo_group_images_file")
        cursor.execute("DROP INDEX IF EXISTS idx_geo_group_images_group")
        cursor.execute("DROP INDEX IF EXISTS idx_geo_groups_session")
        cursor.execute("DROP INDEX IF EXISTS idx_geo_groups_location")
        cursor.execute("DROP INDEX IF EXISTS idx_geo_groups_key")

        cursor.execute("DROP TABLE IF EXISTS grouping_fallback_log")
        cursor.execute("DROP TABLE IF EXISTS geocoding_cache")
        cursor.execute("DROP TABLE IF EXISTS geo_group_images")
        cursor.execute("DROP TABLE IF EXISTS geo_groups")

        conn.commit()