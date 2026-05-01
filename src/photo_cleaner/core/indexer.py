"""
Core indexing logic for photo collections.

Orchestrates file scanning, hashing, and database storage.

v0.5.3: Includes incremental indexing for faster re-scans.
"""

import logging
import sqlite3
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Optional

from PIL import Image, ExifTags

from photo_cleaner.core.hasher import ImageHasher
from photo_cleaner.db.schema import Database
from photo_cleaner.io.file_scanner import FileScanner

logger = logging.getLogger(__name__)


class PhotoIndexer:
    """Indexes photo collections with hashing and metadata extraction."""

    def __init__(self, db: Database, max_workers: Optional[int] = None) -> None:
        """
        Initialize photo indexer.

        Args:
            db: Database instance
            max_workers: Max parallel workers for hashing (default: CPU count - 1, min 1)
        """
        self.db = db
        
        # CRITICAL: Prevent CPU oversubscription
        # Use cpu_count() - 1 to leave headroom for UI thread
        if max_workers is None:
            import os
            cpu_count = os.cpu_count() or 4
            max_workers = max(1, cpu_count - 1)  # At least 1, but leave headroom
        
        self.max_workers = max(1, max_workers)  # Ensure at least 1
        self.hasher = ImageHasher()
        
        logger.info(f"PhotoIndexer initialized with max_workers={self.max_workers}")

    def index_folder(self, folder_path: Path, skip_existing: bool = True) -> dict[str, int]:
        """
        Index all images in a folder recursively.

        Args:
            folder_path: Root folder to index
            skip_existing: Skip files already in database

        Returns:
            Statistics dict with counts (processed, skipped, failed)
        """
        scanner = FileScanner(folder_path)
        files = list(scanner.scan())

        if not files:
            logger.warning(f"No image files found in {folder_path}")
            return {"processed": 0, "skipped": 0, "failed": 0}

        self._reactivate_scanned_files(files)

        logger.info(f"Found {len(files)} files to index")

        stats = {"processed": 0, "skipped": 0, "failed": 0}

        # Filter out already indexed files if requested
        if skip_existing:
            files = [f for f in files if not self._is_indexed(f)]
            logger.info(f"After filtering: {len(files)} new files to process")

        # Process files in parallel
        # OPTIMIZATION: ThreadPool for I/O-bound work (Phase 2 Week 2)
        # Note: Async writes tested in Week 3 showed no improvement at scale
        # Root cause: Disk I/O is the real bottleneck (~28ms/image near physical limit)
        results_to_store = []
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_file, path): path for path in files
            }

            for future in as_completed(future_to_path):
                path = future_to_path[future]
                try:
                    result = future.result()
                    if result:
                        results_to_store.append((path, result))
                        stats["processed"] += 1
                    else:
                        stats["failed"] += 1

                    if (stats["processed"] + stats["failed"]) % 50 == 0:
                        logger.info(
                            f"Progress: {stats['processed']} processed, "
                            f"{stats['failed']} failed"
                        )

                except Exception as e:
                    logger.error(f"Failed to process {path}: {e}")
                    stats["failed"] += 1
        
        # Batch insert all records at once (optimal for SQLite)
        if results_to_store:
            logger.info(f"Batch-inserting {len(results_to_store)} records into database...")
            self._batch_store_file_records(results_to_store)

        logger.info(
            f"Indexing complete: {stats['processed']} processed, "
            f"{stats['skipped']} skipped, {stats['failed']} failed"
        )
        return stats

    def _is_indexed(self, path: Path) -> bool:
        """Check if file is already in database."""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT 1 FROM files WHERE path = ?", (str(path),))
        return cursor.fetchone() is not None

    def _reactivate_scanned_files(self, files: list[Path]) -> int:
        """Clear stale deleted markers for files that are present in the current scan.

        This self-heals DB rows that were marked deleted in a previous session even
        though the underlying file still exists and is being scanned again.
        """
        if not files:
            return 0

        cursor = self.db.conn.cursor()
        restored = 0
        chunk_size = 500

        for start in range(0, len(files), chunk_size):
            chunk = files[start:start + chunk_size]
            placeholders = ",".join("?" for _ in chunk)
            params = [str(path) for path in chunk]
            cursor.execute(
                f"""
                UPDATE files
                SET is_deleted = 0,
                    deleted_at = NULL,
                    trash_path = NULL
                WHERE is_deleted = 1
                  AND path IN ({placeholders})
                """,
                params,
            )
            restored += cursor.rowcount or 0

        if restored:
            self.db.conn.commit()
            logger.info("Reactivated %d previously deleted file records from current scan", restored)

        return restored

    @staticmethod
    def _extract_capture_time(path: Path) -> Optional[float]:
        """Extract EXIF capture timestamp (DateTimeOriginal preferred)."""
        tag_name_by_id = ExifTags.TAGS
        exif_keys = ("DateTimeOriginal", "DateTime", "DateTimeDigitized")

        try:
            with Image.open(path) as img:
                exif = img.getexif()
                if not exif:
                    return None

                for wanted in exif_keys:
                    for tag_id, value in exif.items():
                        if tag_name_by_id.get(tag_id) != wanted:
                            continue
                        if not value:
                            continue
                        try:
                            dt = datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                        except ValueError:
                            continue
                        return dt.timestamp()
        except (OSError, ValueError, TypeError):
            return None

        return None

    @staticmethod
    def _process_file(path: Path) -> Optional[dict]:
        """
        Process a single file (hash computation).

        Static method for thread/process pool compatibility.
        Works with both ThreadPoolExecutor and ProcessPoolExecutor.

        OPTIMIZATION NOTE (Phase 2 Week 2):
        - Changed from ProcessPoolExecutor to ThreadPoolExecutor
        - ThreadPool is more efficient for I/O-bound work (hashing)
        - No IPC overhead, shared memory between threads
        - Stateless function design ensures thread safety

        Args:
            path: Path to image file

        Returns:
            Dict with hash data, or None on failure
        """
        try:
            # Register HEIC support in worker process/thread
            try:
                from pillow_heif import register_heif_opener
                register_heif_opener()
            except ImportError:
                pass  # pillow-heif not available, HEIC files will fail
            
            hasher = ImageHasher()
            hashes = hasher.compute_all_hashes(path)

            if hashes["phash"] is None and hashes["file_hash"] is None:
                return None

            # Keep the file indexed even when pHash is unavailable so the DB,
            # exact-duplicate fallback, and later re-analysis still have a record.
            stat = path.stat()
            capture_time = PhotoIndexer._extract_capture_time(path)

            return {
                "phash": hashes["phash"],
                "file_hash": hashes["file_hash"],
                "file_size": stat.st_size,
                "capture_time": capture_time,
                "modified_time": stat.st_mtime,
                "created_time": stat.st_ctime,
            }
        except Exception as e:
            logger.warning(f"Failed to process file {path}: {e}")
            return None

    def _store_file_record(self, path: Path, data: dict) -> None:
        """
        Store file record in database.
        
        NOTE: Prefer _batch_store_file_records() for better performance.

        Args:
            path: File path
            data: Metadata dict from _process_file
        """
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO files 
            (path, phash, file_hash, file_size, capture_time, modified_time, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(path),
                data["phash"],
                data["file_hash"],
                data["file_size"],
                data.get("capture_time"),
                data["modified_time"],
                data["created_time"],
            ),
        )
        self.db.conn.commit()
    
    def _batch_store_file_records(self, records: list[tuple[Path, dict]]) -> None:
        """
        Store multiple file records in database using batch insert.
        
        OPTIMIZED: Uses executemany() with single commit for ~2x speedup.

        Args:
            records: List of (path, data) tuples
        """
        if not records:
            return
        
        cursor = self.db.conn.cursor()
        
        # Prepare batch data
        batch_data = [
            (
                str(path),
                data["phash"],
                data["file_hash"],
                data["file_size"],
                data.get("capture_time"),
                data["modified_time"],
                data["created_time"],
            )
            for path, data in records
        ]
        
        # Batch insert with single commit
        # BUG #9 FIX: Use batch insert instead of loop for better performance
        cursor.executemany(
            """
            INSERT OR REPLACE INTO files 
            (path, phash, file_hash, file_size, capture_time, modified_time, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            batch_data,
        )
        # BUG #6 FIX: Implicit commit from isolation_level="DEFERRED"
        self.db.conn.commit()
        
        logger.debug(f"Batch-inserted {len(records)} records")

    def get_stats(self) -> dict[str, int]:
        """
        Get database statistics.

        Returns:
            Dict with total_files count
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM files")
        result = cursor.fetchone()
        return {"total_files": result["count"] if result else 0}
    # ========== v0.5.3: Incremental Indexing Methods ==========

    def index_folder_incremental(
        self, 
        folder_path: Path, 
        scan_id: Optional[str] = None,
        progress_callback=None
    ) -> dict:
        """
        Index folder incrementally: only hash new/modified files.
        
        Strategy:
        1. Scan folder for all files
        2. Check each file against file_hashes table
        3. For NEW files: hash them
        4. For MODIFIED files (size/mtime changed): re-hash
        5. For UNCHANGED files: skip (use cached hash)
        6. Store new hashes in file_hashes table
        7. Record scan in scan_history
        8. Return stats with performance improvement

        Args:
            folder_path: Root folder to scan
            scan_id: Unique scan ID (auto-generated if None)
            progress_callback: Optional callback(current, total, status_str)

        Returns:
            Dict with:
            - total_files: All files in folder
            - new_files: Files needing hashing
            - hashed_files: Actually processed
            - cached_files: Used cache (skipped)
            - duplicates_found: Number of dups
            - time_saved: Estimated seconds saved vs full scan
            - speedup_factor: Multiplier vs full indexing
        """
        if scan_id is None:
            scan_id = str(uuid.uuid4())[:8]
        
        scan_time = time.time()
        scanner = FileScanner(folder_path)
        all_files = list(scanner.scan())
        
        if not all_files:
            logger.warning(f"No image files found in {folder_path}")
            return {
                "total_files": 0,
                "new_files": 0,
                "hashed_files": 0,
                "cached_files": 0,
                "duplicates_found": 0,
                "time_saved": 0,
                "speedup_factor": 1.0,
            }
        
        logger.info(
            f"[{scan_id}] Starting incremental scan: {len(all_files)} total files"
        )

        self._reactivate_scanned_files(all_files)
        
        # Categorize files: new, modified, unchanged
        new_files, modified_files, unchanged_files = self._categorize_files(all_files)
        
        files_to_hash = new_files + modified_files
        logger.info(
            f"[{scan_id}] Categories: {len(new_files)} new, "
            f"{len(modified_files)} modified, {len(unchanged_files)} unchanged"
        )
        
        # Hash the files that need it
        # OPTIMIZATION: Changed from ProcessPool to ThreadPool (Phase 2 Week 2)
        # Same rationale: I/O-bound work, eliminates IPC overhead
        results_to_store = []
        stats = {"processed": 0, "failed": 0}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_path = {
                executor.submit(self._process_file, path): path for path in files_to_hash
            }
            
            total_to_process = len(files_to_hash)
            for idx, future in enumerate(as_completed(future_to_path)):
                path = future_to_path[future]
                try:
                    result = future.result()
                    if result:
                        results_to_store.append((path, result))
                        stats["processed"] += 1
                    else:
                        stats["failed"] += 1
                    
                    if progress_callback:
                        progress_callback(
                            idx + 1, 
                            total_to_process, 
                            f"Hashing: {path.name}"
                        )
                except Exception as e:
                    logger.error(f"Failed to process {path}: {e}")
                    stats["failed"] += 1
        
        # Store new/modified records
        if results_to_store:
            self._batch_store_incremental_records(results_to_store, scan_id)
        
        # Calculate performance metrics
        hashed_count = len(results_to_store)
        cached_count = len(unchanged_files)
        time_elapsed = time.time() - scan_time
        
        # Estimate time saved
        # Rough: ~0.2 sec per image for full hash
        # If we skipped cached_count images: time_saved = cached_count * 0.2
        time_saved = cached_count * 0.2
        speedup_factor = (cached_count + hashed_count) / max(1, hashed_count)
        
        # Find duplicates in new/modified files
        duplicates_found = self._count_new_duplicates(results_to_store)
        
        # Record scan in history
        self._record_scan_history(
            scan_id=scan_id,
            folder=str(folder_path),
            total=len(all_files),
            new=len(new_files),
            hashed=hashed_count,
            dups=duplicates_found,
        )
        
        result = {
            "total_files": len(all_files),
            "new_files": len(new_files),
            "hashed_files": hashed_count,
            "cached_files": cached_count,
            "duplicates_found": duplicates_found,
            "time_elapsed": time_elapsed,
            "time_saved": time_saved,
            "speedup_factor": round(speedup_factor, 1),
        }
        
        logger.info(
            f"[{scan_id}] Incremental scan complete: "
            f"{hashed_count} hashed, {cached_count} cached. "
            f"Speedup: {result['speedup_factor']}x (saved ~{time_saved:.1f}s)"
        )
        
        return result

    def _categorize_files(self, files: list[Path]) -> tuple[list[Path], list[Path], list[Path]]:
        """
        Categorize files as new, modified, or unchanged.

        Returns:
            Tuple of (new_files, modified_files, unchanged_files)
        """
        cursor = self.db.conn.cursor()
        new_files = []
        modified_files = []
        unchanged_files = []
        
        for file_path in files:
            # Check if file exists in file_hashes table
            cursor.execute(
                "SELECT file_size, modified_time FROM file_hashes WHERE file_path = ?",
                (str(file_path),),
            )
            row = cursor.fetchone()
            
            if row is None:
                # New file
                new_files.append(file_path)
            else:
                # Check if modified
                stat = file_path.stat()
                cached_size = row[0]
                cached_mtime = row[1]
                
                if stat.st_size != cached_size or stat.st_mtime != cached_mtime:
                    # File was modified
                    modified_files.append(file_path)
                else:
                    # File unchanged
                    unchanged_files.append(file_path)
        
        return new_files, modified_files, unchanged_files

    def _batch_store_incremental_records(self, records: list[tuple[Path, dict]], scan_id: str) -> None:
        """
        Store incremental index records (files + file_hashes).
        
        Args:
            records: List of (path, data) tuples
            scan_id: Scan ID for tracking
        """
        if not records:
            return
        
        cursor = self.db.conn.cursor()
        
        # Prepare batch data for files table
        files_batch = [
            (
                str(path),
                data["phash"],
                data["file_hash"],
                data["file_size"],
                data.get("capture_time"),
                data["modified_time"],
                data["created_time"],
            )
            for path, data in records
        ]
        
        # Batch insert into files
        cursor.executemany(
            """
            INSERT OR REPLACE INTO files 
            (path, phash, file_hash, file_size, capture_time, modified_time, created_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            files_batch,
        )
        
        # Now insert into file_hashes (for incremental tracking)
        # Get the file_id for each inserted record
        file_hashes_batch = []
        for path, data in records:
            # Get the file_id
            cursor.execute("SELECT file_id FROM files WHERE path = ?", (str(path),))
            row = cursor.fetchone()
            if row:
                file_id = row[0]
                file_hashes_batch.append((
                    file_id,  # hash_id (foreign key to files.file_id)
                    str(path),
                    data["phash"],
                    data["file_hash"],
                    data["file_size"],
                    data["modified_time"],
                ))
        
        # Batch insert into file_hashes
        cursor.executemany(
            """
            INSERT OR REPLACE INTO file_hashes
            (hash_id, file_path, phash, md5, file_size, modified_time)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            file_hashes_batch,
        )
        
        self.db.conn.commit()
        logger.debug(f"[{scan_id}] Batch-inserted {len(records)} incremental records")

    def _count_new_duplicates(self, records: list[tuple[Path, dict]]) -> int:
        """
        Count duplicates found in newly processed records.
        
        Returns:
            Number of duplicate groups found
        """
        cursor = self.db.conn.cursor()
        
        # Get pHashes from new records
        pHashes = [data.get("phash") for _, data in records if data.get("phash")]
        
        if not pHashes:
            return 0
        
        # Count how many of these pHashes match existing files
        placeholders = ",".join("?" * len(pHashes))
        cursor.execute(
            f"""
            SELECT COUNT(DISTINCT phash) FROM files 
            WHERE phash IN ({placeholders}) AND phash IS NOT NULL
            """,
            pHashes,
        )
        result = cursor.fetchone()
        return result[0] if result else 0

    def _record_scan_history(
        self,
        scan_id: str,
        folder: str,
        total: int,
        new: int,
        hashed: int,
        dups: int,
    ) -> None:
        """Record scan in scan_history table for analytics."""
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            INSERT INTO scan_history
            (scan_id, input_folder, total_files, new_files, hashed_files, duplicates_found)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (scan_id, folder, total, new, hashed, dups),
        )
        self.db.conn.commit()
        logger.debug(f"Recorded scan {scan_id} in history")