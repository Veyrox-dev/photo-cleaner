# src/photo_cleaner/duplicates/finder.py

import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path

from PIL import ExifTags, Image

from photo_cleaner.db.schema import Database
from photo_cleaner.core.hasher import hamming_distance

logger = logging.getLogger(__name__)

class DuplicateFinder:
    def __init__(self, db: Database, phash_threshold: int = 5):
        self.db = db
        self.phash_threshold = phash_threshold
        # CRITICAL: Increase prefix length to 8 hex chars (32 bits) to reduce bucket degeneration
        # and prevent O(n^2) worst-case when many hashes share short prefix
        self.phash_prefix_chars = 8  # was 4 - now more selective

        # Optional time-aware grouping (defaults tuned for burst photos).
        self.time_window_seconds = self._read_float_env(
            "PHOTOCLEANER_GROUP_TIME_WINDOW_SEC", 30.0, min_value=0.0
        )
        self.relaxed_similarity = self._read_float_env(
            "PHOTOCLEANER_GROUP_RELAXED_SIMILARITY", 0.60, min_value=0.0, max_value=1.0
        )
        self.relaxed_hamming_threshold = int(round((1.0 - self.relaxed_similarity) * 64.0))
        logger.info(f"DuplicateFinder initialized: threshold={phash_threshold}")

    @staticmethod
    def _read_float_env(
        name: str,
        default: float,
        *,
        min_value: float | None = None,
        max_value: float | None = None,
    ) -> float:
        value_raw = os.environ.get(name)
        if value_raw in (None, ""):
            return default
        try:
            value = float(value_raw)
        except ValueError:
            logger.warning("Invalid float env %s=%r, using default %.3f", name, value_raw, default)
            return default
        if min_value is not None and value < min_value:
            logger.warning("Env %s=%.3f below min %.3f, clamping", name, value, min_value)
            value = min_value
        if max_value is not None and value > max_value:
            logger.warning("Env %s=%.3f above max %.3f, clamping", name, value, max_value)
            value = max_value
        return value

    @staticmethod
    def _extract_capture_time(path: Path) -> float | None:
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
    def _effective_timestamp(row) -> float | None:
        """Return capture timestamp only (derived from EXIF during indexing)."""
        for key in ("capture_time",):
            value = row[key]
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                continue
        return None

    def build_groups(self):
        """Baue Duplikat-Gruppen aus phash-Ähnlichkeiten und schreibe in DB."""
        logger.info("=== DuplicateFinder.build_groups() STARTED ===")
        conn = self.db.connect()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT file_id, path, phash, capture_time, modified_time, created_time
            FROM files
            WHERE phash IS NOT NULL
            """
        )
        rows = cur.fetchall()
        logger.info(f"Found {len(rows)} files with phash")
        logger.info(f"Using phash_threshold={self.phash_threshold} bits (Hamming distance)")

        cur.execute("DELETE FROM duplicates")

        if not rows:
            logger.warning("No files with phash found - falling back to exact file_hash groups")
            cur.execute(
                """
                SELECT file_hash, GROUP_CONCAT(file_id) AS file_ids, COUNT(*) AS total
                FROM files
                WHERE file_hash IS NOT NULL
                GROUP BY file_hash
                HAVING COUNT(*) > 1
                ORDER BY file_hash
                """
            )
            exact_groups = cur.fetchall()
            if not exact_groups:
                logger.warning("No exact file_hash groups found either")
                conn.commit()
                return []

            group_rows = []
            for index, group in enumerate(exact_groups, start=1):
                group_id = f"G{index:06d}"
                file_ids = [int(file_id) for file_id in str(group["file_ids"]).split(",") if file_id]
                for file_id in file_ids:
                    cur.execute(
                        "INSERT INTO duplicates (group_id, file_id, similarity_score) VALUES (?,?,?)",
                        (group_id, file_id, 1.0),
                    )
                group_rows.append((group_id, len(file_ids)))

            conn.commit()
            logger.info("=== DuplicateFinder.build_groups() COMPLETED ===")
            logger.info(
                f"Created {len(group_rows)} exact-match groups with {sum(g[1] for g in group_rows)} total images"
            )
            return group_rows

        n = len(rows)
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[rj] = ri

        prefix_len = max(1, min(self.phash_prefix_chars, len(rows[0]["phash"]) if rows else 1))
        buckets: dict[str, list[int]] = {}
        for idx, r in enumerate(rows):
            phash = r["phash"]
            prefix = phash[:prefix_len]
            buckets.setdefault(prefix, []).append(idx)

        for bucket_idxs in buckets.values():
            blen = len(bucket_idxs)
            for ii in range(blen):
                a_idx = bucket_idxs[ii]
                a = rows[a_idx]
                for jj in range(ii + 1, blen):
                    b_idx = bucket_idxs[jj]
                    b = rows[b_idx]
                    try:
                        dist = hamming_distance(a["phash"], b["phash"])
                    except (TypeError, ValueError):
                        logger.debug("Error computing hamming distance in build_groups", exc_info=True)
                        continue
                    if dist <= self.phash_threshold:
                        logger.debug(f"Match: {a['path']} <==> {b['path']} (distance={dist})")
                        union(a_idx, b_idx)

        # Time-aware relaxation for burst/series photos: if timestamps are close,
        # allow a broader pHash distance (e.g. approx. 60% similarity).
        relaxed_comparisons = 0
        relaxed_joins = 0
        if (
            self.time_window_seconds > 0
            and self.relaxed_hamming_threshold > self.phash_threshold
        ):
            # Backfill missing capture times for already indexed files.
            missing_capture = [r for r in rows if self._effective_timestamp(r) is None]
            if missing_capture:
                updated = 0
                for row in missing_capture:
                    capture_ts = self._extract_capture_time(Path(row["path"]))
                    if capture_ts is None:
                        continue
                    cur.execute(
                        "UPDATE files SET capture_time = ? WHERE file_id = ?",
                        (capture_ts, row["file_id"]),
                    )
                    updated += 1
                if updated:
                    conn.commit()
                    logger.info("Backfilled EXIF capture_time for %d files", updated)

                # Reload rows so time-aware pass sees backfilled values immediately.
                cur.execute(
                    """
                    SELECT file_id, path, phash, capture_time, modified_time, created_time
                    FROM files
                    WHERE phash IS NOT NULL
                    """
                )
                rows = cur.fetchall()

            timestamped_indices = []
            for idx, row in enumerate(rows):
                ts = self._effective_timestamp(row)
                if ts is not None:
                    timestamped_indices.append((ts, idx))

            timestamped_indices.sort(key=lambda item: item[0])
            total_ts = len(timestamped_indices)
            for i in range(total_ts):
                ts_i, idx_i = timestamped_indices[i]
                j = i + 1
                while j < total_ts:
                    ts_j, idx_j = timestamped_indices[j]
                    if (ts_j - ts_i) > self.time_window_seconds:
                        break
                    if find(idx_i) != find(idx_j):
                        try:
                            dist = hamming_distance(rows[idx_i]["phash"], rows[idx_j]["phash"])
                        except (TypeError, ValueError):
                            logger.debug("Error computing hamming distance in time-aware pass", exc_info=True)
                            j += 1
                            continue
                        relaxed_comparisons += 1
                        if dist <= self.relaxed_hamming_threshold:
                            union(idx_i, idx_j)
                            relaxed_joins += 1
                    j += 1

            logger.info(
                "Time-aware grouping: window=%.1fs, relaxed_similarity>=%.2f, comparisons=%d, joins=%d",
                self.time_window_seconds,
                self.relaxed_similarity,
                relaxed_comparisons,
                relaxed_joins,
            )

        components: dict[int, list[int]] = {}
        for idx in range(n):
            root = find(idx)
            components.setdefault(root, []).append(idx)

        cur.execute("DELETE FROM duplicates")
        group_rows = []
        group_num = 1
        for members in components.values():
            if len(members) < 2:
                continue
            group_id = f"G{group_num:06d}"
            group_num += 1
            for m_idx in members:
                file_id = rows[m_idx]["file_id"]
                cur.execute(
                    "INSERT INTO duplicates (group_id, file_id, similarity_score) VALUES (?,?,?)",
                    (group_id, file_id, None),
                )
            group_rows.append((group_id, len(members)))

        conn.commit()
        logger.info(f"=== DuplicateFinder.build_groups() COMPLETED ===")
        logger.info(f"Created {len(group_rows)} groups with {sum(g[1] for g in group_rows)} total images")
        return group_rows

    def find_all_groups(self):
        """Return duplicate groups from DB if available.

        Falls back to an empty list when the duplicates table is not yet populated
        so callers do not crash during the initial pipeline run.
        """
        try:
            conn = self.db.connect()
            cur = conn.cursor()
            cur.execute(
                """
                SELECT group_id, COUNT(*) AS total
                FROM duplicates
                GROUP BY group_id
                ORDER BY group_id
                """
            )
            return cur.fetchall()
        except sqlite3.Error:
            logger.debug("Could not fetch duplicate groups from database", exc_info=True)
            return []

    def find_exact_duplicates(self):
        conn = self.db.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT file_hash, COUNT(*) AS cnt
            FROM files
            WHERE file_hash IS NOT NULL
            GROUP BY file_hash
            HAVING cnt > 1
        """)

        return cur.fetchall()

    def find_similar_duplicates(self):
        conn = self.db.connect()
        cur = conn.cursor()

        cur.execute("""
            SELECT file_id, path, phash
            FROM files
            WHERE phash IS NOT NULL
        """)
        rows = cur.fetchall()

        # Bucket rows by phash prefix to avoid O(n^2) over the entire set.
        buckets: dict[str, list] = {}
        prefix_len = max(1, min(self.phash_prefix_chars, len(rows[0]["phash"]) if rows else 1))
        for r in rows:
            phash = r["phash"]
            prefix = phash[:prefix_len]
            buckets.setdefault(prefix, []).append(r)

        results = []
        # Compare within each bucket only
        for bucket in buckets.values():
            blen = len(bucket)
            for i in range(blen):
                a = bucket[i]
                for j in range(i + 1, blen):
                    b = bucket[j]
                    try:
                        dist = hamming_distance(a["phash"], b["phash"])
                    except (TypeError, ValueError):
                        logger.debug("Error computing hamming distance in find_similar_duplicates", exc_info=True)
                        continue
                    if dist <= self.phash_threshold:
                        results.append((a["path"], b["path"], dist))

        return results
