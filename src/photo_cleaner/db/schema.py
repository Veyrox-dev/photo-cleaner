"""
Database schema and initialization for photo_cleaner.

Tables:
- files: Main file index with hashes and metadata
- duplicates: Detected duplicate groups
- file_hashes: v0.5.3 - Persistent hash cache for incremental indexing
- scan_history: v0.5.3 - Track scan history for incremental analysis
- analysis_cache: v0.5.3 - Cache quality analysis results by file hash
- file_hash_mapping: v0.5.3 - Map files to content hashes
"""

import logging
import sqlite3
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCHEMA_VERSION = 6

CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS files (
    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL UNIQUE,
    phash TEXT,
    file_hash TEXT,
    file_size INTEGER,
    capture_time REAL,
    modified_time REAL,
    created_time REAL,
    exif_json TEXT,
    exif_location_name TEXT,
    sharpness_score REAL,
    overall_score REAL,
    quality_score REAL,
    sharpness_component REAL,
    lighting_component REAL,
    resolution_component REAL,
    face_quality_component REAL,
    is_keeper BOOLEAN DEFAULT 0,
    is_deleted BOOLEAN DEFAULT 0,
    trash_path TEXT,
    deleted_at REAL,
    file_status TEXT NOT NULL DEFAULT 'UNDECIDED',
    is_locked BOOLEAN NOT NULL DEFAULT 0,
    decided_at REAL,
    indexed_at REAL DEFAULT (unixepoch()),
    is_recommended BOOLEAN DEFAULT 0,
    keeper_source TEXT DEFAULT 'undecided',
    UNIQUE(path)
);
"""

CREATE_STATUS_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS status_history (
    history_id INTEGER PRIMARY KEY AUTOINCREMENT,
    action_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    old_status TEXT,
    new_status TEXT,
    old_locked BOOLEAN,
    new_locked BOOLEAN,
    old_decided_at REAL,
    new_decided_at REAL,
    reason TEXT,
    created_at REAL DEFAULT (unixepoch()),
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);
"""

CREATE_DUPLICATES_TABLE = """
CREATE TABLE IF NOT EXISTS duplicates (
    duplicate_id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id TEXT NOT NULL,
    file_id INTEGER NOT NULL,
    similarity_score REAL,
    is_keeper BOOLEAN DEFAULT 0,
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE
);
"""

CREATE_METADATA_TABLE = """
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT
);
"""

# ========== v0.5.3: New tables for incremental indexing & smart caching ==========

CREATE_FILE_HASHES_TABLE = """
CREATE TABLE IF NOT EXISTS file_hashes (
    hash_id TEXT PRIMARY KEY,
    file_path TEXT UNIQUE NOT NULL,
    phash TEXT,
    md5 TEXT,
    file_size INTEGER,
    modified_time REAL,
    indexed_at REAL DEFAULT (unixepoch()),
    FOREIGN KEY (hash_id) REFERENCES files(file_id) ON DELETE CASCADE
);
"""

CREATE_SCAN_HISTORY_TABLE = """
CREATE TABLE IF NOT EXISTS scan_history (
    scan_id TEXT PRIMARY KEY,
    scan_time REAL DEFAULT (unixepoch()),
    input_folder TEXT NOT NULL,
    total_files INTEGER,
    new_files INTEGER,
    hashed_files INTEGER,
    duplicates_found INTEGER
);
"""

CREATE_ANALYSIS_CACHE_TABLE = """
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
);
"""

CREATE_FILE_HASH_MAPPING_TABLE = """
CREATE TABLE IF NOT EXISTS file_hash_mapping (
    mapping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER NOT NULL,
    hash_key TEXT NOT NULL,
    file_path TEXT NOT NULL,
    FOREIGN KEY (file_id) REFERENCES files(file_id) ON DELETE CASCADE,
    FOREIGN KEY (hash_key) REFERENCES analysis_cache(hash_key) ON DELETE CASCADE,
    UNIQUE(file_id, hash_key)
);
"""

# ========== v0.9: EXIF Smart Grouping tables ==========

CREATE_GEO_GROUPS_TABLE = """
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
);
"""

CREATE_GEO_GROUP_IMAGES_TABLE = """
CREATE TABLE IF NOT EXISTS geo_group_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    geo_group_id INTEGER NOT NULL REFERENCES geo_groups(id) ON DELETE CASCADE,
    file_id INTEGER NOT NULL REFERENCES files(file_id) ON DELETE CASCADE,
    UNIQUE(geo_group_id, file_id)
);
"""

CREATE_GEOCODING_CACHE_TABLE = """
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
);
"""

CREATE_GROUPING_FALLBACK_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS grouping_fallback_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_id INTEGER REFERENCES files(file_id) ON DELETE CASCADE,
    tier_used INTEGER,
    reason TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_files_phash ON files(phash);",
    "CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);",
    "CREATE INDEX IF NOT EXISTS idx_files_status ON files(file_status);",
    "CREATE INDEX IF NOT EXISTS idx_files_locked ON files(is_locked);",
    "CREATE INDEX IF NOT EXISTS idx_history_action ON status_history(action_id);",
    "CREATE INDEX IF NOT EXISTS idx_history_file ON status_history(file_id);",
    "CREATE INDEX IF NOT EXISTS idx_duplicates_group ON duplicates(group_id);",
    "CREATE INDEX IF NOT EXISTS idx_duplicates_file ON duplicates(file_id);",
    # v0.5.3 indexes for incremental + caching
    "CREATE INDEX IF NOT EXISTS idx_file_hashes_path ON file_hashes(file_path);",
    "CREATE INDEX IF NOT EXISTS idx_scan_history_folder ON scan_history(input_folder);",
    "CREATE INDEX IF NOT EXISTS idx_analysis_cache_hash ON analysis_cache(file_hash);",
    "CREATE INDEX IF NOT EXISTS idx_file_hash_mapping_file ON file_hash_mapping(file_id);",
    "CREATE INDEX IF NOT EXISTS idx_file_hash_mapping_hash ON file_hash_mapping(hash_key);",
    # v0.9: EXIF Smart Grouping indexes
    "CREATE INDEX IF NOT EXISTS idx_geo_groups_key ON geo_groups(group_key);",
    "CREATE INDEX IF NOT EXISTS idx_geo_groups_location ON geo_groups(location_name);",
    "CREATE INDEX IF NOT EXISTS idx_geo_groups_session ON geo_groups(scan_session_id);",
    "CREATE INDEX IF NOT EXISTS idx_geo_group_images_group ON geo_group_images(geo_group_id);",
    "CREATE INDEX IF NOT EXISTS idx_geo_group_images_file ON geo_group_images(file_id);",
    "CREATE INDEX IF NOT EXISTS idx_geocoding_cache_coords ON geocoding_cache(coordinates);",
    "CREATE INDEX IF NOT EXISTS idx_grouping_fallback_file ON grouping_fallback_log(file_id);",
]


class RetryingConnection(sqlite3.Connection):
    """SQLite connection with simple retry-on-busy handling.

    Retries common busy/locked errors with exponential backoff to avoid
    transient "database is locked" crashes during concurrent UI actions.
    """

    _RETRYABLE = ("database is locked", "database is busy", "busy")
    _MAX_RETRIES = 3
    _BASE_SLEEP = 0.05

    def execute(self, sql, parameters=(), /):  # type: ignore[override]
        return self._execute_with_retry(super().execute, sql, parameters)

    def executemany(self, sql, seq_of_parameters, /):  # type: ignore[override]
        return self._execute_with_retry(super().executemany, sql, seq_of_parameters)

    def executescript(self, sql_script, /):  # type: ignore[override]
        return self._execute_with_retry(super().executescript, sql_script)

    def _execute_with_retry(self, func, *args):
        for attempt in range(self._MAX_RETRIES + 1):
            try:
                return func(*args)
            except sqlite3.OperationalError as e:
                msg = str(e).lower()
                if not any(token in msg for token in self._RETRYABLE):
                    raise
                if attempt >= self._MAX_RETRIES:
                    raise
                sleep_for = self._BASE_SLEEP * (attempt + 1)
                time.sleep(sleep_for)
        # Should never reach here
        return func(*args)


class Database:
    """SQLite database manager for photo_cleaner."""

    def __init__(self, db_path: Path) -> None:
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self.conn: Optional[sqlite3.Connection] = None

    def connect(self) -> sqlite3.Connection:
        """
        Establish database connection and initialize schema.

        Returns:
            Active SQLite connection
        """
        if self.conn is None:
            self.db_path = Path(self.db_path).expanduser()
            try:
                self.db_path.parent.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                logger.error(f"Failed to create database directory {self.db_path.parent}: {e}")
                raise sqlite3.OperationalError(f"Cannot create database directory: {self.db_path.parent}") from e

            logger.info(f"Connecting to database: {self.db_path}")
            self.conn = sqlite3.connect(
                str(self.db_path),
                timeout=5.0,
                check_same_thread=False,
                factory=RetryingConnection,
            )
            self.conn.row_factory = sqlite3.Row
            try:
                self.conn.execute("PRAGMA busy_timeout = 5000")
                # BUG #6 FIX: Set isolation level to DEFERRED for proper transaction semantics
                # Prevents dirty reads and ensures data consistency
                self.conn.isolation_level = "DEFERRED"
                logger.debug("SQLite isolation level set to DEFERRED")
            except (sqlite3.Error, RuntimeError):
                logger.debug("Could not set isolation level pragma; continuing with defaults")
            self._initialize_schema()
        return self.conn

    def _initialize_schema(self) -> None:
        """Create tables and indexes if they don't exist."""
        # P4.4: Enable WAL mode for better concurrency and crash recovery
        try:
            self.conn.execute("PRAGMA journal_mode = WAL")
            logger.debug("SQLite WAL mode enabled")
        except sqlite3.Error as e:
            logger.warning(f"Could not enable WAL mode: {e}")
        
        cursor = self.conn.cursor()

        # Create tables
        cursor.execute(CREATE_FILES_TABLE)
        cursor.execute(CREATE_DUPLICATES_TABLE)
        cursor.execute(CREATE_METADATA_TABLE)
        cursor.execute(CREATE_STATUS_HISTORY_TABLE)
        
        # v0.5.3: Create new tables for incremental indexing & smart caching
        cursor.execute(CREATE_FILE_HASHES_TABLE)
        cursor.execute(CREATE_SCAN_HISTORY_TABLE)
        cursor.execute(CREATE_ANALYSIS_CACHE_TABLE)
        cursor.execute(CREATE_FILE_HASH_MAPPING_TABLE)

        # v0.9: EXIF Smart Grouping tables
        cursor.execute(CREATE_GEO_GROUPS_TABLE)
        cursor.execute(CREATE_GEO_GROUP_IMAGES_TABLE)
        cursor.execute(CREATE_GEOCODING_CACHE_TABLE)
        cursor.execute(CREATE_GROUPING_FALLBACK_LOG_TABLE)

        # Backwards-compatible migration: ensure optional columns exist on older DBs
        try:
            cursor.execute("PRAGMA table_info(files)")
            cols = [r[1] for r in cursor.fetchall()]
            if "is_keeper" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN is_keeper BOOLEAN DEFAULT 0")
            if "is_deleted" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN is_deleted BOOLEAN DEFAULT 0")
            if "trash_path" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN trash_path TEXT")
            if "deleted_at" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN deleted_at REAL")
            if "file_status" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN file_status TEXT NOT NULL DEFAULT 'UNDECIDED'")
            if "is_locked" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN is_locked BOOLEAN NOT NULL DEFAULT 0")
            if "decided_at" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN decided_at REAL")
            if "is_recommended" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN is_recommended BOOLEAN DEFAULT 0")
            if "keeper_source" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN keeper_source TEXT DEFAULT 'undecided'")
            if "quality_score" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN quality_score REAL")
            if "capture_time" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN capture_time REAL")
            if "exif_location_name" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN exif_location_name TEXT")
            # NEW: Quality score components
            if "sharpness_component" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN sharpness_component REAL")
            if "lighting_component" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN lighting_component REAL")
            if "resolution_component" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN resolution_component REAL")
            if "face_quality_component" not in cols:
                cursor.execute("ALTER TABLE files ADD COLUMN face_quality_component REAL")
            # status_history columns handled by CREATE_STATUS_HISTORY_TABLE
        except sqlite3.Error:
            # If anything goes wrong, continue—new DBs will have the columns from CREATE_FILES_TABLE
            logger.debug("Could not add optional columns to files table", exc_info=True)

        # Create indexes
        for index_sql in CREATE_INDEXES:
            cursor.execute(index_sql)

        # Store schema version
        cursor.execute(
            "INSERT OR REPLACE INTO metadata (key, value) VALUES (?, ?)",
            ("schema_version", str(SCHEMA_VERSION)),
        )

        self.conn.commit()
        logger.info("Database schema initialized")


    def close(self) -> None:
        """Close database connection."""
        if self.conn:
            try:
                self.conn.close()
                self.conn = None
                logger.info("Database connection closed")
            except Exception as e:
                # P1.4: Connection might already be closed, just log and continue
                logger.debug(f"Error closing database connection (may already be closed): {e}")
                self.conn = None

    def __enter__(self) -> "Database":
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()