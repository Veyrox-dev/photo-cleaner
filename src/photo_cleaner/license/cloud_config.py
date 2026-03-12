from __future__ import annotations

import logging
import os

from photo_cleaner.license_client import LicenseConfig as CloudLicenseConfig

logger = logging.getLogger(__name__)


def get_cloud_license_config(*, missing_message: str, error_message: str) -> CloudLicenseConfig | None:
    """Create cloud license config from environment variables.

    Returns None if required variables are missing or invalid.
    """
    project_url = os.getenv("SUPABASE_PROJECT_URL")
    anon_key = os.getenv("SUPABASE_ANON_KEY")

    if not project_url or not anon_key:
        logger.warning(missing_message)
        return None

    try:
        return CloudLicenseConfig(project_url=project_url, anon_key=anon_key)
    except (ImportError, AttributeError, ValueError, OSError) as e:
        logger.warning(error_message, e, exc_info=True)
        return None
