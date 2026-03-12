from __future__ import annotations

import logging
from typing import Any

from photo_cleaner.license import LicenseManager
from photo_cleaner.license.cloud_config import get_cloud_license_config
from photo_cleaner.license_client import LicenseManager as CloudLicenseManager

logger = logging.getLogger(__name__)


class LicenseService:
    """Service layer for cloud activation and local license state."""

    def __init__(self, license_manager: LicenseManager) -> None:
        self.license_manager = license_manager
        self.cloud_license_manager: CloudLicenseManager | None = self._create_cloud_manager()

    def _create_cloud_manager(self) -> CloudLicenseManager | None:
        config = get_cloud_license_config(
            missing_message="Cloud licensing not configured: SUPABASE_PROJECT_URL/SUPABASE_ANON_KEY missing",
            error_message="Could not init cloud license manager: %s",
        )
        if config is None:
            return None
        return CloudLicenseManager(config)

    def is_cloud_configured(self) -> bool:
        return self.cloud_license_manager is not None

    def activate_with_key(self, license_key: str) -> tuple[bool, str | None]:
        if not self.cloud_license_manager:
            raise RuntimeError("Cloud licensing not configured")

        success, message = self.cloud_license_manager.activate_with_key(license_key)
        if success:
            try:
                self.license_manager.refresh()
            except (OSError, IOError, ValueError) as e:
                logger.warning("License manager refresh failed: %s", e, exc_info=True)
        return success, message

    def remove_license(self) -> bool:
        return self.license_manager.remove_license()

    def get_license_status(self) -> dict[str, Any]:
        return self.license_manager.get_license_status()