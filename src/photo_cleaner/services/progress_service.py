from __future__ import annotations

from photo_cleaner.repositories.file_repository import FileRepository


class ProgressService:
    """Aggregates lightweight progress metrics without full scans."""

    def __init__(self, files: FileRepository) -> None:
        self.files = files

    def snapshot(self) -> dict:
        agg = self.files.aggregates()
        decided = agg["keep"] + agg["delete"]
        open_cnt = agg["undecided"] + agg["unsure"]
        groups = self.files.group_progress()
        return {
            "files_total": agg["total"],
            "files_decided": decided,
            "files_open": open_cnt,
            "files_unsure": agg["unsure"],
            "reclaim_bytes": agg["reclaim_bytes"],
            "groups_total": groups.get("groups_total"),
            "groups_done": groups.get("groups_done"),
        }
