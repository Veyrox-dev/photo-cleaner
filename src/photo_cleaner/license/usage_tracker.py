"""Lifetime image quota tracker for the Free license.

Strategy (defense-in-depth):
1. Local HMAC-signed counter  – works offline, tamper-evident.
2. Supabase sync              – authoritative cloud record; survives local
                                 file deletion / reset attempts.

On each scan:
  a) Pre-check:  local remaining >= requested count  → allow or block.
  b) Post-scan:  call Supabase consume_free_images() to deduct count,
                 then persist the updated local counter.

If the local counter file is missing or has an invalid signature, the tracker
falls back to Supabase to retrieve the true value.  If Supabase is also
unreachable, the local counter is reset to 0 (conservative: allows scan, but
will be corrected on next online sync).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple

from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)

_COUNTER_FILENAME = "usage_counter.json"
_LIMIT = 250


def _sign(machine_id: str, total_used: int) -> str:
    """Return HMAC-SHA256 hex digest of machine_id + total_used."""
    key = machine_id.encode("utf-8")
    msg = f"{machine_id}:{total_used}".encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


class UsageTracker:
    """Thread-safe lifetime image quota tracker for Free licenses."""

    def __init__(self, machine_id: str):
        self._machine_id = machine_id
        self._lock = threading.Lock()
        self._counter_path: Path = AppConfig.get_user_data_dir() / _COUNTER_FILENAME

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def limit(self) -> int:
        return _LIMIT

    def get_total_used(self) -> int:
        """Return locally tracked total images used (0 if counter unreadable)."""
        return self._read_local()

    def get_remaining(self) -> int:
        return max(0, _LIMIT - self.get_total_used())

    def can_scan(self, image_count: int) -> Tuple[bool, int]:
        """
        Check whether *image_count* new images fit within the remaining quota.

        Returns:
            (allowed, remaining_after_scan)
        """
        used = self.get_total_used()
        remaining = max(0, _LIMIT - used)
        if image_count > remaining:
            return False, remaining
        return True, remaining - image_count

    def record_scan(self, image_count: int) -> Tuple[bool, int, str]:
        """
        Record that *image_count* images were successfully scanned.

        Steps:
          1. Increment local signed counter.
          2. Async call to Supabase consume_free_images().

        Returns:
            (allowed, remaining, error_message)
            ``allowed`` is False only when the Supabase call explicitly denied
            the quota (meaning the cloud total was already exceeded).
        """
        with self._lock:
            used = self._read_local()
            new_total = used + image_count
            if new_total > _LIMIT:
                new_total = _LIMIT  # clamp; Supabase will be authoritative
            self._write_local(new_total)

        # Supabase sync in background thread so the UI is not blocked
        threading.Thread(
            target=self._sync_supabase,
            args=(image_count,),
            daemon=True,
            name="UsageTracker-SupabaseSync",
        ).start()

        remaining = max(0, _LIMIT - new_total)
        return True, remaining, ""

    def sync_from_supabase(self) -> Optional[int]:
        """
        Query Supabase for the authoritative total_used (read-only, p_amount=0).
        Updates the local counter if the value is higher than what we have.
        Returns the authoritative total_used, or None on failure.
        """
        try:
            client = self._get_client()
            if client is None:
                return None
            machine_id = self._machine_id
            allowed, remaining, err = client.consume_free_images(machine_id, 0)
            if err:
                logger.warning("Supabase usage query failed: %s", err)
                return None
            cloud_used = max(0, _LIMIT - (remaining or 0))
            with self._lock:
                local_used = self._read_local()
                if cloud_used > local_used:
                    logger.info(
                        "UsageTracker: cloud total (%d) > local (%d); updating local.",
                        cloud_used, local_used,
                    )
                    self._write_local(cloud_used)
            return cloud_used
        except Exception as e:
            logger.warning("UsageTracker.sync_from_supabase failed: %s", e)
            return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _read_local(self) -> int:
        """Read and verify local counter. Returns 0 on any error."""
        try:
            if not self._counter_path.exists():
                return 0
            raw = self._counter_path.read_text(encoding="utf-8")
            data = json.loads(raw)
            total_used = int(data.get("total_used", 0))
            stored_sig = data.get("sig", "")
            expected_sig = _sign(self._machine_id, total_used)
            if not hmac.compare_digest(stored_sig, expected_sig):
                logger.warning(
                    "UsageTracker: local counter signature mismatch – counter may have been tampered with. "
                    "Falling back to Supabase."
                )
                cloud = self.sync_from_supabase()
                if cloud is not None:
                    return cloud
                # Cannot verify – be conservative: return 0 so the user can
                # still scan; the next online sync will correct the value.
                return 0
            return max(0, total_used)
        except Exception as e:
            logger.warning("UsageTracker: could not read local counter: %s", e)
            return 0

    def _write_local(self, total_used: int) -> None:
        """Persist signed counter to disk."""
        try:
            self._counter_path.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "total_used": total_used,
                "sig": _sign(self._machine_id, total_used),
            }
            self._counter_path.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
        except Exception as e:
            logger.warning("UsageTracker: could not write local counter: %s", e)

    def _sync_supabase(self, image_count: int) -> None:
        """Background: deduct *image_count* from Supabase quota."""
        try:
            client = self._get_client()
            if client is None:
                return
            allowed, remaining, err = client.consume_free_images(self._machine_id, image_count)
            if err:
                logger.warning("Supabase consume_free_images error: %s", err)
                return
            # Reconcile local counter with Supabase truth
            cloud_used = max(0, _LIMIT - (remaining or 0))
            with self._lock:
                local_used = self._read_local()
                if cloud_used > local_used:
                    self._write_local(cloud_used)
            logger.info(
                "UsageTracker: Supabase sync OK – remaining=%s, cloud_used=%d",
                remaining, cloud_used,
            )
        except Exception as e:
            logger.warning("UsageTracker: Supabase sync failed (will retry next scan): %s", e)

    @staticmethod
    def _get_client():
        """Return a LicenseClient instance or None if not configured."""
        try:
            from photo_cleaner.license.cloud_config import get_cloud_license_config
            from photo_cleaner.license_client import LicenseClient
            config = get_cloud_license_config(
                missing_message="UsageTracker: Supabase not configured",
                error_message="UsageTracker: cloud config error: %s",
            )
            if config is None:
                return None
            return LicenseClient(config)
        except Exception as e:
            logger.warning("UsageTracker: could not create LicenseClient: %s", e)
            return None


# ---------------------------------------------------------------------------
# Module-level singleton (lazily initialised)
# ---------------------------------------------------------------------------

_tracker: Optional[UsageTracker] = None
_tracker_lock = threading.Lock()


def get_usage_tracker() -> UsageTracker:
    """Return the process-wide UsageTracker instance."""
    global _tracker
    if _tracker is None:
        with _tracker_lock:
            if _tracker is None:
                from photo_cleaner.license.license_manager import compute_machine_id
                _tracker = UsageTracker(compute_machine_id())
    return _tracker
