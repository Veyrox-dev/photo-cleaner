"""Migration manager for package-based migrations."""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

from .base import Migration

logger = logging.getLogger(__name__)


@dataclass
class MigrationRecord:
    """Record of a migration execution."""

    version: str
    name: str
    applied_at: str
    checksum: str
    execution_time_ms: float

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return asdict(self)


class MigrationManager:
    """Manages database migrations with rollback support."""

    def __init__(self, db_path: Path):
        self.db_path = db_path

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = "DEFERRED"
        return conn

    def _ensure_migration_table(self, conn: sqlite3.Connection) -> None:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS migrations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                version TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL,
                checksum TEXT NOT NULL,
                execution_time_ms REAL NOT NULL,
                applied_by TEXT DEFAULT 'system',
                rollback_available BOOLEAN DEFAULT 1
            )
            """
        )
        conn.commit()

    def get_applied_migrations(self, conn: sqlite3.Connection) -> List[MigrationRecord]:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version, name, applied_at, checksum, execution_time_ms FROM migrations ORDER BY applied_at"
        )
        return [
            MigrationRecord(
                version=row[0],
                name=row[1],
                applied_at=row[2],
                checksum=row[3],
                execution_time_ms=row[4],
            )
            for row in cursor.fetchall()
        ]

    def get_current_version(self, conn: sqlite3.Connection) -> Optional[str]:
        cursor = conn.cursor()
        cursor.execute("SELECT version FROM migrations ORDER BY applied_at DESC LIMIT 1")
        row = cursor.fetchone()
        return row[0] if row else None

    def apply_migration(self, migration: Migration, conn: sqlite3.Connection) -> Tuple[bool, str]:
        cursor = conn.cursor()
        start_time = datetime.now()

        try:
            cursor.execute("SELECT version FROM migrations WHERE version = ?", (migration.version,))
            if cursor.fetchone():
                return False, f"Migration {migration.version} already applied"

            logger.info("Applying migration %s: %s", migration.version, migration.name)
            migration.up(conn)

            execution_time = (datetime.now() - start_time).total_seconds() * 1000
            cursor.execute(
                """
                INSERT INTO migrations (version, name, applied_at, checksum, execution_time_ms)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    migration.version,
                    migration.name,
                    datetime.utcnow().isoformat(),
                    migration.get_checksum(),
                    execution_time,
                ),
            )
            conn.commit()
            return True, f"Migration {migration.version} applied"
        except Exception as exc:
            conn.rollback()
            msg = f"Migration {migration.version} failed: {exc}"
            logger.error(msg, exc_info=True)
            return False, msg

    def migrate_to_latest(self, migrations: List[Migration]) -> Tuple[int, List[str]]:
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        applied_count = 0
        messages: List[str] = []

        for migration in sorted(migrations, key=lambda m: m.version):
            success, msg = self.apply_migration(migration, conn)
            messages.append(msg)
            if success:
                applied_count += 1

        conn.close()
        return applied_count, messages

    def get_migration_status(self, migrations: List[Migration]) -> dict:
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        applied = self.get_applied_migrations(conn)
        applied_versions = {m.version for m in applied}
        pending = [m for m in migrations if m.version not in applied_versions]
        current = self.get_current_version(conn)
        conn.close()

        return {
            "current_version": current,
            "applied": [m.to_dict() for m in applied],
            "pending": [
                {
                    "version": m.version,
                    "name": m.name,
                    "description": m.description,
                }
                for m in sorted(pending, key=lambda m: m.version)
            ],
            "total_applied": len(applied),
            "total_pending": len(pending),
        }