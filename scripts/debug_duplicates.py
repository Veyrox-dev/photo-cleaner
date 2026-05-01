"""Debug-Script: Analysiert die DB auf Duplikat-Erkennung."""
import sqlite3
import os
from pathlib import Path

DB_PATH = Path(os.environ.get("APPDATA", "")) / "PhotoCleaner" / "db" / "photo_cleaner.db"

if not DB_PATH.exists():
    print(f"DB nicht gefunden: {DB_PATH}")
    exit(1)

print(f"DB: {DB_PATH}")
conn = sqlite3.connect(str(DB_PATH))
conn.row_factory = sqlite3.Row

total = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
phash_count = conn.execute("SELECT COUNT(*) FROM files WHERE phash IS NOT NULL").fetchone()[0]
print(f"\nGesamt Dateien: {total}")
print(f"Dateien mit phash: {phash_count}")
print(f"Dateien OHNE phash: {total - phash_count}")

print("\nStatus-Verteilung:")
for row in conn.execute("SELECT file_status, COUNT(*) as cnt FROM files GROUP BY file_status"):
    print(f"  {row['file_status']}: {row['cnt']}")

dup_entries = conn.execute("SELECT COUNT(*) FROM duplicates").fetchone()[0]
dup_groups = conn.execute("SELECT COUNT(DISTINCT group_id) FROM duplicates").fetchone()[0]
print(f"\nDuplikat-Eintraege: {dup_entries}")
print(f"Duplikat-Gruppen: {dup_groups}")

print("\n--- Kopie-Dateien ---")
rows = conn.execute(
    "SELECT path, phash, file_status, file_hash FROM files WHERE path LIKE '%Kopie%'"
).fetchall()
if not rows:
    print("  Keine Kopie-Dateien gefunden!")
else:
    for row in rows:
        print(f"  path: {Path(row['path']).name}")
        print(f"  phash: {row['phash']}")
        print(f"  file_hash: {row['file_hash']}")
        print(f"  status: {row['file_status']}")
        # Suche Originaldatei mit gleichem phash
        if row['phash']:
            matches = conn.execute(
                "SELECT path, file_status FROM files WHERE phash = ? AND path != ?",
                (row['phash'], row['path'])
            ).fetchall()
            if matches:
                print(f"  >>> EXACT phash-Matches: {[Path(m['path']).name for m in matches]}")
            else:
                # Suche nach ähnlichen phashes (Hamming < 15)
                all_hashes = conn.execute(
                    "SELECT path, phash FROM files WHERE phash IS NOT NULL AND path != ?",
                    (row['path'],)
                ).fetchall()
                similar = []
                copy_int = int(row['phash'], 16)
                for other in all_hashes:
                    other_int = int(other['phash'], 16)
                    dist = bin(copy_int ^ other_int).count('1')
                    if dist <= 15:
                        similar.append((Path(other['path']).name, dist))
                if similar:
                    similar.sort(key=lambda x: x[1])
                    print(f"  >>> Aehnliche Dateien (Hamming<=15): {similar[:5]}")
                else:
                    print("  >>> KEINE aehnlichen Dateien gefunden!")
        print()

conn.close()
