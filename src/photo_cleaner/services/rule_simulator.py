from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, List, Optional

from photo_cleaner.models.mode import AppMode
from photo_cleaner.models.status import FileStatus
from photo_cleaner.repositories.file_repository import FileRepository


@dataclass
class RuleResult:
    path: Path
    suggested_status: Optional[FileStatus]
    reason: str
    skip_reason: Optional[str] = None  # e.g., "SKIPPED_LOCKED", "SAFE_MODE_BLOCKED"


class RuleSimulator:
    """Runs non-destructive rules and returns proposed changes respecting mode and locks."""

    def __init__(
        self,
        files_repo: FileRepository,
        image_meta_loader: Callable[[Path], dict],
        mode_getter: Callable[[], AppMode],
        is_exact_duplicate: Callable[[Path], bool] | None = None,
    ):
        self.files_repo = files_repo
        self.image_meta_loader = image_meta_loader
        self.mode_getter = mode_getter
        self.is_exact_duplicate = is_exact_duplicate or (lambda _p: False)

    def simulate(self, rules: Iterable[Callable[[Path, dict], Optional[RuleResult]]]) -> List[RuleResult]:
        cur = self.files_repo.conn.execute(
            "SELECT path FROM files WHERE is_deleted = 0"
        )
        results: List[RuleResult] = []
        mode = self.mode_getter()
        for row in cur.fetchall():
            p = Path(row[0])
            meta = self.image_meta_loader(p)
            for rule in rules:
                res = rule(p, meta)
                if not res:
                    continue
                status, is_locked = self.files_repo.get_status(p)
                if is_locked:
                    results.append(RuleResult(path=p, suggested_status=None, reason=res.reason, skip_reason="SKIPPED_LOCKED"))
                    continue
                if mode == AppMode.SAFE_MODE and res.suggested_status == FileStatus.DELETE:
                    if not self.is_exact_duplicate(p):
                        results.append(RuleResult(path=p, suggested_status=None, reason=res.reason, skip_reason="SAFE_MODE_BLOCKED"))
                        continue
                results.append(res)
        return results

    def apply_simulation(self, sim_results: List[RuleResult], *, reason: str = "rule-simulation-apply", action_id: str = "RULE_APPLY") -> None:
        """Apply simulated results; decided_at only set for KEEP/DELETE via FileRepository rules."""
        for res in sim_results:
            if res.skip_reason or not res.suggested_status:
                continue
            self.files_repo.set_status(res.path, res.suggested_status, reason=reason, action_id=action_id)
