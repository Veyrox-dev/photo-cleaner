# photo-cleaner/src/photo_cleaner/core/duplicate_groups.py

from dataclasses import dataclass
from pathlib import Path
from typing import List, Literal
import re

@dataclass
class FileEntry:
    path: Path
    width: int
    height: int
    created: float  # Timestamp
    name: str

@dataclass
class DuplicateGroup:
    files: List[FileEntry]
    reason: Literal["exact", "similar"]
    confidence: int  # 0–100

@dataclass
class CleanupPlan:
    keep: Path
    remove: List[Path]

def normalize_name(name: str) -> str:
    """Ignoriere Kopie-Zusätze wie ' - Kopie', '(1)' etc."""
    name = re.sub(r'(\s-\sKopie|\(\d+\))', '', name)
    return name.lower().strip()

def pick_best_file(files: List[FileEntry]) -> FileEntry:
    """Heuristik: höchste Auflösung, ältestes Erstellungsdatum, kürzester bereinigter Name."""
    def score(f: FileEntry):
        res = f.width * f.height
        timestamp = -f.created  # älteste Datei bevorzugen
        name_len = len(normalize_name(f.name))
        return (res, timestamp, -name_len)
    return max(files, key=score)

def group_duplicates(file_entries: List[FileEntry], reason: Literal["exact","similar"]) -> List[DuplicateGroup]:
    """
    Gruppiert Duplikate in handhabbare Gruppen.
    """
    # Einfaches Beispiel: gruppiere nach normalisiertem Dateinamen
    groups_dict = {}
    for f in file_entries:
        key = normalize_name(f.name)
        groups_dict.setdefault(key, []).append(f)

    duplicate_groups = []
    for files in groups_dict.values():
        if len(files) > 1:
            confidence = 100 if reason == "exact" else 75
            duplicate_groups.append(DuplicateGroup(files=files, reason=reason, confidence=confidence))
    return duplicate_groups

def build_cleanup_plan(group: DuplicateGroup) -> CleanupPlan:
    best = pick_best_file(group.files)
    to_remove = [f.path for f in group.files if f.path != best.path]
    return CleanupPlan(keep=best.path, remove=to_remove)
