# src/photo_cleaner/duplicates/finder.py

import logging
import sqlite3
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
        logger.info(f"DuplicateFinder initialized: threshold={phash_threshold}")

    def build_groups(self):
        """Baue Duplikat-Gruppen aus phash-Ähnlichkeiten und schreibe in DB."""
        logger.info("=== DuplicateFinder.build_groups() STARTED ===")
        conn = self.db.connect()
        cur = conn.cursor()

        cur.execute(
            """
            SELECT file_id, path, phash
            FROM files
            WHERE phash IS NOT NULL
            """
        )
        rows = cur.fetchall()
        logger.info(f"Found {len(rows)} files with phash")

        if not rows:
            logger.warning("No files with phash found - cannot build groups")
            cur.execute("DELETE FROM duplicates")
            conn.commit()
            return []

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
                        union(a_idx, b_idx)

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
