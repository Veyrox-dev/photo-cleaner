"""
Database migration system for photo_cleaner.

Provides safe, version-controlled schema migrations with rollback support.
Each migration is a standalone script with up() and down() methods.

Usage:
    from photo_cleaner.db.migrations import MigrationManager
    
    manager = MigrationManager(db_path)
    manager.migrate_to_latest()  # Upgrade to latest version
    manager.rollback()            # Rollback to previous version
"""

import json
import logging
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

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


class Migration(ABC):
    """Base class for all database migrations."""

    version: str
    name: str
    description: str

    @abstractmethod
    def up(self, conn: sqlite3.Connection) -> None:
        """Apply migration (upgrade schema)."""
        pass

    @abstractmethod
    def down(self, conn: sqlite3.Connection) -> None:
        """Rollback migration (downgrade schema)."""
        pass

    def get_checksum(self) -> str:
        """Get migration checksum for integrity verification."""
        import hashlib

        # Use class name, version, and docstring for checksum
        content = f"{self.__class__.__name__}{self.version}{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class MigrationManager:
    """Manages database migrations with rollback support."""

    def __init__(self, db_path: Path):
        """
        Initialize migration manager.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.migrations_dir = Path(__file__).parent / "migrations"
        self.migrations_dir.mkdir(exist_ok=True)

    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=5.0)
        conn.row_factory = sqlite3.Row
        conn.isolation_level = "DEFERRED"
        return conn

    def _ensure_migration_table(self, conn: sqlite3.Connection) -> None:
        """Create migrations tracking table if it doesn't exist."""
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
        """Get list of applied migrations."""
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
        """Get current database schema version."""
        cursor = conn.cursor()
        cursor.execute(
            "SELECT version FROM migrations ORDER BY applied_at DESC LIMIT 1"
        )
        result = cursor.fetchone()
        return result[0] if result else None

    def apply_migration(
        self, migration: Migration, conn: sqlite3.Connection
    ) -> Tuple[bool, str]:
        """
        Apply a single migration with transaction support.

        Args:
            migration: Migration to apply
            conn: Database connection

        Returns:
            Tuple of (success, message)
        """
        cursor = conn.cursor()
        start_time = datetime.now()

        try:
            # Verify checksum for integrity
            stored_checksum = migration.get_checksum()

            # Check if already applied
            cursor.execute("SELECT version FROM migrations WHERE version = ?", (migration.version,))
            if cursor.fetchone():
                return False, f"Migration {migration.version} already applied"

            # Apply migration
            logger.info(f"Applying migration {migration.version}: {migration.name}")
            migration.up(conn)

            # Record migration
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
                    stored_checksum,
                    execution_time,
                ),
            )
            conn.commit()

            logger.info(
                f"Migration {migration.version} applied successfully in {execution_time:.2f}ms"
            )
            return True, f"Migration {migration.version} applied"

        except Exception as e:
            conn.rollback()
            error_msg = f"Migration {migration.version} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def rollback_migration(
        self, migration: Migration, conn: sqlite3.Connection
    ) -> Tuple[bool, str]:
        """
        Rollback a single migration with transaction support.

        Args:
            migration: Migration to rollback
            conn: Database connection

        Returns:
            Tuple of (success, message)
        """
        cursor = conn.cursor()

        try:
            # Check if migration is applied
            cursor.execute("SELECT version FROM migrations WHERE version = ?", (migration.version,))
            if not cursor.fetchone():
                return False, f"Migration {migration.version} not applied"

            logger.info(f"Rolling back migration {migration.version}: {migration.name}")
            migration.down(conn)

            # Remove migration record
            cursor.execute("DELETE FROM migrations WHERE version = ?", (migration.version,))
            conn.commit()

            logger.info(f"Migration {migration.version} rolled back successfully")
            return True, f"Migration {migration.version} rolled back"

        except Exception as e:
            conn.rollback()
            error_msg = f"Rollback of {migration.version} failed: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

    def migrate_to_latest(self, migrations: List[Migration]) -> Tuple[int, List[str]]:
        """
        Apply all pending migrations in order.

        Args:
            migrations: List of migrations to apply

        Returns:
            Tuple of (count_applied, messages)
        """
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        messages = []
        applied_count = 0

        # Sort migrations by version
        sorted_migrations = sorted(migrations, key=lambda m: m.version)

        for migration in sorted_migrations:
            success, msg = self.apply_migration(migration, conn)
            messages.append(msg)
            if success:
                applied_count += 1

        conn.close()
        return applied_count, messages

    def rollback_to_version(self, target_version: str, migrations: List[Migration]) -> Tuple[int, List[str]]:
        """
        Rollback migrations until reaching target version.

        Args:
            target_version: Target schema version to rollback to
            migrations: List of all migrations

        Returns:
            Tuple of (count_rolled_back, messages)
        """
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        applied = self.get_applied_migrations(conn)
        messages = []
        rolled_back = 0

        # Rollback in reverse order
        for record in reversed(applied):
            if record.version <= target_version:
                break

            # Find migration
            migration = next((m for m in migrations if m.version == record.version), None)
            if not migration:
                messages.append(f"Migration {record.version} not found")
                continue

            success, msg = self.rollback_migration(migration, conn)
            messages.append(msg)
            if success:
                rolled_back += 1

        conn.close()
        return rolled_back, messages

    def get_migration_status(self, migrations: List[Migration]) -> dict:
        """
        Get current migration status.

        Returns:
            Status dictionary with applied, pending, and current version
        """
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

    def verify_integrity(self, migrations: List[Migration]) -> Tuple[bool, List[str]]:
        """
        Verify migration integrity (checksum validation).

        Returns:
            Tuple of (all_valid, error_messages)
        """
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        applied = self.get_applied_migrations(conn)
        errors = []

        for record in applied:
            migration = next((m for m in migrations if m.version == record.version), None)
            if not migration:
                errors.append(f"Migration {record.version} not found in codebase")
                continue

            expected_checksum = migration.get_checksum()
            if record.checksum != expected_checksum:
                errors.append(
                    f"Migration {record.version} checksum mismatch: "
                    f"expected {expected_checksum}, got {record.checksum}"
                )

        conn.close()
        return len(errors) == 0, errors

    def export_migration_history(self, output_path: Path) -> None:
        """Export migration history to JSON file."""
        conn = self._get_connection()
        self._ensure_migration_table(conn)

        applied = self.get_applied_migrations(conn)
        conn.close()

        history = {
            "exported_at": datetime.utcnow().isoformat(),
            "migrations": [m.to_dict() for m in applied],
        }

        with open(output_path, "w") as f:
            json.dump(history, f, indent=2)

        logger.info(f"Migration history exported to {output_path}")
