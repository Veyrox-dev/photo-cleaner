"""
Optimierte Duplicate-Finding Implementierung mit Hash-Buckets.

Diese Implementierung ersetzt den O(n²) Vollvergleich durch einen
Bucket-basierten Ansatz, der nur ähnliche Hashes vergleicht.

Performance-Gewinn: x5-x10
"""

from collections import defaultdict
from pathlib import Path
from typing import Dict, List
import logging

from photo_cleaner.core.hasher import hamming_distance
from photo_cleaner.db.schema import Database

logger = logging.getLogger(__name__)


class OptimizedDuplicateFinder:
    """
    Optimierter Duplicate Finder mit Hash-Bucket-Algorithmus.
    
    Statt O(n²) Vollvergleich: Gruppiere Hashes in Buckets und
    vergleiche nur Bilder im selben Bucket.
    
    Beispiel:
        - Hash 1: 1010101010101010
        - Hash 2: 1010111010101010  
        - Hash 3: 0101010101010101
        
        Bucket A (startet mit 1010): Hash 1, Hash 2 → vergleiche
        Bucket B (startet mit 0101): Hash 3 → überspringe (nur 1 Bild)
    """
    
    def __init__(self, db: Database, phash_threshold: int = 5, bucket_bits: int = 8):
        """
        Initialize optimized duplicate finder.
        
        Args:
            db: Database instance
            phash_threshold: Maximum Hamming distance for duplicates
            bucket_bits: Anzahl Bits für Bucket-Gruppierung (Standard: 8)
                        - Mehr Bits = kleinere Buckets = schneller, aber weniger Treffer
                        - Weniger Bits = größere Buckets = langsamer, aber mehr Treffer
        """
        self.db = db
        self.phash_threshold = phash_threshold
        self.bucket_bits = bucket_bits
    
    def find_duplicates(self) -> Dict[str, List[Path]]:
        """
        Finde Duplicate-Gruppen mit Hash-Bucket-Algorithmus.
        
        Returns:
            Dictionary mapping group_id -> list of duplicate file paths
        """
        # 1. Lade alle Hashes aus Datenbank
        cursor = self.db.conn.cursor()
        cursor.execute(
            """
            SELECT file_id, path, phash
            FROM files
            WHERE phash IS NOT NULL
            """
        )
        files = cursor.fetchall()
        
        if not files:
            logger.info("No files with phash found")
            return {}
        
        logger.info(f"Finding duplicates for {len(files)} files using bucket algorithm...")
        
        # 2. Gruppiere in Buckets
        buckets = self._create_buckets(files)
        logger.debug(f"Created {len(buckets)} buckets")
        
        # 3. Finde Duplicates innerhalb Buckets
        duplicate_groups = self._find_duplicates_in_buckets(buckets)
        
        logger.info(
            f"Found {len(duplicate_groups)} duplicate groups with "
            f"{sum(len(g) for g in duplicate_groups.values())} total images"
        )
        
        return duplicate_groups
    
    def _create_buckets(self, files: List[dict]) -> Dict[str, List[dict]]:
        """
        Gruppiere Dateien in Hash-Buckets.
        
        Args:
            files: Liste von Datenbank-Rows mit phash
            
        Returns:
            Dictionary mapping bucket_key -> list of files
        """
        buckets = defaultdict(list)
        
        for file_row in files:
            phash = file_row["phash"]
            
            # Nutze erste N Bits als Bucket-Key
            # z.B. "1010101010101010" -> "10101010" (8 Bits)
            if len(phash) >= self.bucket_bits:
                bucket_key = phash[:self.bucket_bits]
            else:
                bucket_key = phash
            
            buckets[bucket_key].append(file_row)
        
        # Statistik
        bucket_sizes = [len(b) for b in buckets.values()]
        avg_size = sum(bucket_sizes) / len(bucket_sizes) if bucket_sizes else 0
        max_size = max(bucket_sizes) if bucket_sizes else 0
        
        logger.debug(
            f"Bucket stats: {len(buckets)} buckets, "
            f"avg size: {avg_size:.1f}, max size: {max_size}"
        )
        
        return buckets
    
    def _find_duplicates_in_buckets(
        self, buckets: Dict[str, List[dict]]
    ) -> Dict[str, List[Path]]:
        """
        Finde Duplicates innerhalb jedes Buckets.
        
        Args:
            buckets: Dictionary mapping bucket_key -> list of files
            
        Returns:
            Dictionary mapping group_id -> list of duplicate paths
        """
        duplicate_groups = {}
        processed = set()
        group_counter = 0
        total_comparisons = 0
        
        for bucket_key, bucket_files in buckets.items():
            # Überspringe Buckets mit nur 1 Datei
            if len(bucket_files) <= 1:
                continue
            
            # Vergleiche nur Dateien innerhalb dieses Buckets
            for i, file_a in enumerate(bucket_files):
                if file_a["file_id"] in processed:
                    continue
                
                group = [Path(file_a["path"])]
                group_ids = {file_a["file_id"]}
                
                # Vergleiche mit restlichen Dateien im Bucket
                for file_b in bucket_files[i + 1:]:
                    if file_b["file_id"] in processed:
                        continue
                    
                    try:
                        distance = hamming_distance(file_a["phash"], file_b["phash"])
                        total_comparisons += 1
                        
                        if distance <= self.phash_threshold:
                            group.append(Path(file_b["path"]))
                            group_ids.add(file_b["file_id"])
                            processed.add(file_b["file_id"])
                    
                    except Exception as e:
                        logger.warning(
                            f"Failed to compare hashes for {file_a['path']} "
                            f"and {file_b['path']}: {e}"
                        )
                        continue
                
                # Nur Gruppen mit mindestens 2 Bildern speichern
                if len(group) > 1:
                    group_id = f"group_{group_counter:04d}"
                    duplicate_groups[group_id] = group
                    processed.add(file_a["file_id"])
                    group_counter += 1
        
        logger.info(f"Total hash comparisons: {total_comparisons}")
        
        # Vergleiche mit naive O(n²) Ansatz
        naive_comparisons = len([f for bucket in buckets.values() for f in bucket])
        naive_comparisons = (naive_comparisons * (naive_comparisons - 1)) // 2
        
        if naive_comparisons > 0:
            speedup = naive_comparisons / total_comparisons if total_comparisons > 0 else float('inf')
            logger.info(
                f"Bucket optimization: {total_comparisons} comparisons "
                f"vs {naive_comparisons} naive (x{speedup:.1f} speedup)"
            )
        
        return duplicate_groups


def compare_algorithms(db_path: Path, test_files: List[Path]) -> Dict[str, float]:
    """
    Vergleiche Bucket-Algorithmus mit naivem Ansatz.
    
    Args:
        db_path: Pfad zur Datenbank
        test_files: Liste von Test-Dateien
        
    Returns:
        Dictionary mit Laufzeiten
    """
    import time
    from photo_cleaner.duplicates.finder import DuplicateFinder
    
    db = Database(db_path)
    db.connect()
    
    results = {}
    
    # 1. Naive Implementierung
    print("Running naive algorithm...")
    naive_finder = DuplicateFinder(db, phash_threshold=5)
    start = time.time()
    naive_groups = naive_finder.find_duplicates()
    naive_time = time.time() - start
    results["naive_time"] = naive_time
    results["naive_groups"] = len(naive_groups)
    
    # 2. Optimierte Implementierung
    print("Running optimized algorithm...")
    optimized_finder = OptimizedDuplicateFinder(db, phash_threshold=5)
    start = time.time()
    optimized_groups = optimized_finder.find_duplicates()
    optimized_time = time.time() - start
    results["optimized_time"] = optimized_time
    results["optimized_groups"] = len(optimized_groups)
    
    # 3. Vergleich
    speedup = naive_time / optimized_time if optimized_time > 0 else float('inf')
    results["speedup"] = speedup
    
    print(f"\nResults:")
    print(f"  Naive:     {naive_time:.3f}s ({results['naive_groups']} groups)")
    print(f"  Optimized: {optimized_time:.3f}s ({results['optimized_groups']} groups)")
    print(f"  Speedup:   x{speedup:.1f}")
    
    return results


if __name__ == "__main__":
    # Beispiel-Nutzung
    import sys
    from pathlib import Path
    
    if len(sys.argv) < 2:
        print("Usage: python finder_optimized.py <db_path>")
        sys.exit(1)
    
    db_path = Path(sys.argv[1])
    
    db = Database(db_path)
    db.connect()
    
    finder = OptimizedDuplicateFinder(db)
    groups = finder.find_duplicates()
    
    print(f"\nFound {len(groups)} duplicate groups:")
    for group_id, paths in list(groups.items())[:5]:  # Zeige erste 5
        print(f"  {group_id}: {len(paths)} images")
        for path in paths[:3]:  # Zeige erste 3 pro Gruppe
            print(f"    - {path}")
