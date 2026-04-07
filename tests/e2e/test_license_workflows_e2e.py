"""E2E workflow tests for the current FREE/PRO licensing model.

Slice 4 focus:
- FREE lifetime quota = 250
- PRO unlimited image processing
- Legacy ENTERPRISE inputs are accepted as PRO (compatibility)
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from photo_cleaner.license import FeatureFlagsManager, LicenseInfo, LicenseManager, LicenseType


def _build_activation_payload(machine_id: str, lic_type: str, days_valid: int = 365) -> dict:
    exp_date = (datetime.now(timezone.utc) + timedelta(days=days_valid)).date().isoformat()
    return {
        "mid": machine_id,
        "type": lic_type,
        "exp": exp_date,
        "nonce": "slice4-nonce",
        "sig": "slice4-signature",
        "user": "Slice4 User",
    }


@pytest.mark.e2e
@pytest.mark.license
class TestLicenseWorkflowsE2E:
    def test_free_to_pro_activation_flow(self, monkeypatch):
        """FREE user can activate PRO and gets unlimited processing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            monkeypatch.setattr(
                "photo_cleaner.license.license_manager.verify_ed25519_signature",
                lambda payload, sig: True,
            )

            payload = _build_activation_payload(manager.machine_id, "PRO")
            success = manager.activate_with_code(json.dumps(payload))

            assert success is True
            assert manager.license_info.license_type == LicenseType.PRO
            assert manager.license_info.valid is True
            assert manager.can_process_images(100000) is True

    def test_legacy_enterprise_activation_maps_to_pro(self, monkeypatch):
        """Regression: legacy ENTERPRISE activation payload maps to PRO."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            monkeypatch.setattr(
                "photo_cleaner.license.license_manager.verify_ed25519_signature",
                lambda payload, sig: True,
            )

            payload = _build_activation_payload(manager.machine_id, "ENTERPRISE")
            success = manager.activate_with_code(json.dumps(payload))

            assert success is True
            assert manager.license_info.license_type == LicenseType.PRO
            assert manager.license_info.max_images == 0

    def test_free_tier_limit_is_250(self):
        """Regression: FREE tier enforces the 250-image lifetime limit locally."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))
            manager.license_info = manager._create_free_license("slice4 test")

            assert manager.can_process_images(250) is True
            assert manager.can_process_images(251) is False

    def test_pro_feature_flags_expose_unlimited(self):
        """PRO feature flags should report unlimited images and no API tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Pro User",
                machine_id=manager.machine_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=[
                    "batch_processing",
                    "heic_support",
                    "extended_cache",
                    "advanced_quality_analysis",
                    "bulk_delete",
                    "export_formats",
                ],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            flags = FeatureFlagsManager(manager)
            assert flags.has_unlimited_images() is True
            assert flags.has_api_access() is False
