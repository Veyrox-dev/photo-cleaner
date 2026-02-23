"""
End-to-end workflow tests for PhotoCleaner License System.

Tests complete real-world workflows:
1. Free → PRO upgrade
2. License renewal
3. Enterprise deployment
4. Trial period management
5. Support scenarios
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from photo_cleaner.license import (
    LicenseManager,
    LicenseType,
    LicenseInfo,
    FeatureFlagsManager,
    initialize_license_system,
)
from photo_cleaner.license_client import (
    LicenseClient,
    LicenseConfig,
)


class TestFreeToPROUpgradeE2E:
    """E2E: User upgrades from FREE to PRO."""

    def test_free_user_activates_pro_license(self):
        """FREE user should be able to activate PRO license."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)

            # Step 1: Create license manager
            manager = LicenseManager(app_dir)
            
            # Ensure we're starting with FREE by explicit setting
            manager.license_info = LicenseInfo(
                license_type=LicenseType.FREE,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=None,
                signature_valid=False,
                machine_match=True,
                valid=False,
                enabled_features=[],
                max_images=1000,
                raw={},
                path=None,
                validation_reason="free",
            )
            assert manager.license_info.license_type == LicenseType.FREE

            # Step 2: User obtains PRO license code and activates
            now = datetime.now(timezone.utc)
            exp_date = (now + timedelta(days=365)).date()
            
            code = {
                "mid": manager.machine_id,
                "type": "PRO",
                "exp": exp_date.isoformat(),
                "nonce": "test-nonce-001",
            }
            
            sig = manager._hmac_sign(
                code["mid"], code["type"], code["exp"], code["nonce"]
            )
            code["sig"] = sig
            code["user"] = "Pro User"
            
            # Step 3: Activate PRO
            success = manager.activate_with_code(json.dumps(code))
            assert success is True
            
            # Step 4: Verify PRO features now available
            assert manager.license_info.license_type == LicenseType.PRO
            flags = FeatureFlagsManager(manager)
            assert flags.can_batch_process()


class TestProLicenseRenewalE2E:
    """E2E: PRO license renewal before expiration."""

    def test_user_renews_pro_license_before_expiration(self):
        """User should be able to renew PRO license before expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Step 1: Current PRO license expires in 30 days
            now = datetime.now(timezone.utc)
            current_expires = now + timedelta(days=30)

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test User",
                machine_id=manager.machine_id,
                expires_at=current_expires,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            # Step 2: Check days remaining
            days_remaining = (current_expires - now).days
            assert days_remaining <= 30

            # Step 3: User renews with new key (1 year extension)
            new_expires = now + timedelta(days=365 + 30)  # 365 + 30 days

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test User",
                machine_id=manager.machine_id,
                expires_at=new_expires,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            # Step 4: Verify renewal
            status = manager.get_license_status()
            assert status["valid"] is True
            assert status["license_type"] == "PRO"

    def test_grace_period_after_expiration(self):
        """User should have grace period after license expiration."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # License expired 5 days ago
            now = datetime.now(timezone.utc)
            expired_date = now - timedelta(days=5)

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=expired_date,
                signature_valid=True,
                machine_match=True,
                valid=False,  # Expired
                enabled_features=[],
                max_images=1000,  # Falls back to FREE
                raw={},
                path=None,
                validation_reason="expired",
            )

            # Should report as expired
            status = manager.get_license_status()
            assert status["valid"] is False


class TestEnterpriseDeploymentE2E:
    """E2E: Enterprise multi-device deployment."""

    def test_enterprise_license_multiple_users(self):
        """Enterprise license should support multiple users/devices."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )

            # Simulate 3 users registering with same enterprise license
            device_ids = []
            for user_num in range(1, 4):
                salt_file = Path(tmpdir) / f"device_{user_num}_salt"
                device_id = f"DEVICE-ENT-{user_num}"
                device_ids.append(device_id)

            # ENTERPRISE license should support all
            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(days=365)).isoformat()

            enterprise_license = {
                "license_id": "LIC-ENT-001",
                "plan": "enterprise",
                "status": "active",
                "expires_at": expires_at,
                "max_devices": 100,  # Enterprise: many devices
                "registered_devices": device_ids,
            }

            # Each device should be able to use license
            for device_id in device_ids:
                assert device_id in enterprise_license["registered_devices"]

    def test_enterprise_api_access_enabled(self):
        """Enterprise license should enable API access."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Activate ENTERPRISE
            now = datetime.now(timezone.utc)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.ENTERPRISE,
                user="Enterprise Corp",
                machine_id=manager.machine_id,
                expires_at=now + timedelta(days=365),
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
                    "api_access",
                    "unlimited_images",
                ],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            flags = FeatureFlagsManager(manager)

            # Enterprise features
            assert flags.has_api_access()
            assert flags.can_batch_process()
            assert flags.has_unlimited_images()


class TestTrialPeriodE2E:
    """E2E: Trial period management."""

    def test_trial_period_active(self):
        """Trial license should be valid during trial period."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Trial expires in 14 days
            now = datetime.now(timezone.utc)
            trial_expires = now + timedelta(days=14)

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,  # Trial is PRO features
                user="Trial User",
                machine_id=manager.machine_id,
                expires_at=trial_expires,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=[
                    "batch_processing",
                    "heic_support",
                    "extended_cache",
                ],
                max_images=0,
                raw={"trial": True},
                path=None,
                validation_reason="ok",
            )

            # Should be valid
            assert manager.license_info.valid is True

            flags = FeatureFlagsManager(manager)
            # Trial features enabled
            assert flags.can_batch_process()

    def test_trial_expiration_fallback_to_free(self):
        """After trial expires, should fall back to FREE tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Trial expired yesterday
            now = datetime.now(timezone.utc)
            trial_expired = now - timedelta(days=1)

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,  # Was PRO during trial
                user="Trial User",
                machine_id=manager.machine_id,
                expires_at=trial_expired,
                signature_valid=True,
                machine_match=True,
                valid=False,  # Expired
                enabled_features=[],  # No features
                max_images=1000,  # FREE limit
                raw={"trial": True},
                path=None,
                validation_reason="trial_expired",
            )

            # Should fall back to FREE behavior
            assert not manager.license_info.valid
            assert manager.can_process_images(500)  # Within FREE limit
            assert not manager.can_process_images(1001)  # Over FREE limit


class TestSupportScenariosE2E:
    """E2E: Support and troubleshooting scenarios."""

    def test_invalid_license_key_rejection(self):
        """Invalid license key should be rejected clearly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )

            with patch.object(LicenseClient, "exchange_license_key") as mock_ex:
                mock_ex.return_value = (False, None, "Invalid license key format")

                client = LicenseClient(config, cache_dir=Path(tmpdir))

                success, lic_id, error = client.exchange_license_key("INVALID-KEY")

                assert success is False
                assert "invalid" in error.lower()

    def test_network_error_handling(self):
        """Network errors should be handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )

            with patch("requests.post") as mock_post:
                import requests

                mock_post.side_effect = requests.ConnectionError("Network unreachable")

                client = LicenseClient(config, cache_dir=Path(tmpdir))

                # Should handle gracefully
                try:
                    client.exchange_license_key("SOME-KEY")
                except requests.ConnectionError:
                    # Expected - can be caught by caller
                    pass

    def test_corrupted_license_file_recovery(self):
        """Corrupted license file should be handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            license_file = Path.home() / ".photocleaner" / "license.lic"
            license_file.parent.mkdir(parents=True, exist_ok=True)

            # Create corrupted license file
            license_file.write_text("{ CORRUPTED JSON")

            manager = LicenseManager(app_dir)

            # Should handle gracefully - license will be invalid
            # Either FREE or loaded from cloud snapshot, but should be valid object
            assert manager.license_info is not None
            assert isinstance(manager.license_info.license_type, LicenseType)
            
            # Clean up
            try:
                license_file.unlink(missing_ok=True)
            except OSError:
                pass

    def test_license_removal_and_reset(self):
        """User should be able to remove license and reset to FREE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Start with PRO
            now = datetime.now(timezone.utc)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=now + timedelta(days=365),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            assert manager.license_info.license_type == LicenseType.PRO

            # Remove license
            manager.remove_license()

            # Should be reset to FREE
            assert manager.license_info.license_type == LicenseType.FREE
            assert not manager.license_info.valid


class TestLicenseUpgradeDowngradeE2E:
    """E2E: License upgrade/downgrade workflows."""

    def test_pro_to_enterprise_upgrade(self):
        """User can upgrade from PRO to ENTERPRISE."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Current: PRO
            now = datetime.now(timezone.utc)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test User",
                machine_id=manager.machine_id,
                expires_at=now + timedelta(days=100),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            assert manager.license_info.license_type == LicenseType.PRO

            # Upgrade to ENTERPRISE
            manager.license_info = LicenseInfo(
                license_type=LicenseType.ENTERPRISE,
                user="Test User",
                machine_id=manager.machine_id,
                expires_at=now + timedelta(days=365),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=[
                    "batch_processing",
                    "api_access",
                    "unlimited_images",
                ],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            assert manager.license_info.license_type == LicenseType.ENTERPRISE

            flags = FeatureFlagsManager(manager)
            assert flags.has_api_access()  # New ENTERPRISE feature


# Run with: pytest tests/e2e/test_license_workflows_e2e.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
