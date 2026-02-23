"""
Migration package initialization.

Auto-discovers and registers all migrations.
"""

import sqlite3
from typing import List

from .base import Migration
from .v001_initial_schema import V001InitialSchema
from .v002_add_quality_scoring import V002AddQualityScoring
from .v003_add_incremental_indexing import V003AddIncrementalIndexing
from .v004_improve_performance import V004ImprovePerformance


# Registry of all migrations (must be in order)
__all_migrations__: List[Migration] = [
    V001InitialSchema(),
    V002AddQualityScoring(),
    V003AddIncrementalIndexing(),
    V004ImprovePerformance(),
]


def get_all_migrations() -> List[Migration]:
    """Get all registered migrations."""
    return __all_migrations__


def get_migration_by_version(version: str) -> Migration:
    """Get migration by version string."""
    for migration in __all_migrations__:
        if migration.version == version:
            return migration
    raise ValueError(f"Migration {version} not found")
