"""
License module for PhotoCleaner.

Handles license management, validation, and feature flags.
"""

from photo_cleaner.license.license_manager import (
    LicenseManager,
    LicenseType,
    LicenseInfo,
    FeatureFlagsManager,
    initialize_license_system,
    get_license_manager,
    get_feature_flags,
)

__all__ = [
    "LicenseManager",
    "LicenseType",
    "LicenseInfo",
    "FeatureFlagsManager",
    "initialize_license_system",
    "get_license_manager",
    "get_feature_flags",
]
