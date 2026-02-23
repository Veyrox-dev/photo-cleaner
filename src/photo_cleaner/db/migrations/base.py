"""
Base migration class.
"""

import sqlite3
from abc import ABC, abstractmethod


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

        content = f"{self.__class__.__name__}{self.version}{self.description}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
