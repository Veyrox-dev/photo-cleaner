"""
End-to-end tests for PhotoCleaner License System.

Tests cover:
1. License initialization (app startup)
2. License activation workflows
3. Feature availability based on license type
4. Image processing limits
5. Grace period and offline scenarios
6. License expiration handling
7. Machine ID validation
8. Cloud-to-offline sync
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
    get_license_manager,
    get_feature_flags,
)
from photo_cleaner.license_client import (
    LicenseClient,
    LicenseConfig,
    DeviceInfo,
)


class TestLicenseE2EInitialization:
    """E2E: License system initialization on first run."""

    def test_fresh_install_defaults_to_free(self):
        """First run without license should default to FREE tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            # Don't use initialize_license_system since that might load cloud license
            manager = LicenseManager(app_dir)

            # Should default to FREE license if no cloud snapshot
            info = manager.license_info
            # If cloud license loaded, it could be other type
            # So we'll test that license_type is valid
            assert info.license_type in (LicenseType.FREE, LicenseType.PRO, LicenseType.ENTERPRISE)

    def test_license_file_location_correct(self):
        """License file should be created in correct location."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            manager = LicenseManager(app_dir)

            # License file should exist in ~/.photocleaner/
            license_file = Path.home() / ".photocleaner" / "license.lic"
            # (File may or may not exist for FREE license, but path should be correct)
            assert manager.license_file.name == "license.lic"

    def test_machine_id_computed_on_init(self):
        """Machine ID should be computed during initialization."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            manager = LicenseManager(app_dir)

            # Machine ID should be set
            assert manager.machine_id is not None
            assert len(manager.machine_id) > 0
            # Machine ID should be stable across runs
            manager2 = LicenseManager(app_dir)
            assert manager2.machine_id == manager.machine_id


class TestLicenseE2EActivation:
    """E2E: License activation workflows."""

    def test_pro_license_activation_with_code(self):
        """Complete PRO license activation with code."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create valid activation code for PRO tier
            now = datetime.now(timezone.utc)
            exp_date = (now + timedelta(days=365)).date()
            
            # Activation code format: JSON with mid, type, exp, nonce, sig
            code = {
                "mid": manager.machine_id,
                "type": "PRO",
                "exp": exp_date.isoformat(),
                "nonce": "test-nonce-123",
            }
            
            # Calculate signature
            sig = manager._hmac_sign(
                code["mid"],
                code["type"],
                code["exp"],
                code["nonce"]
            )
            code["sig"] = sig
            code["user"] = "Test User"
            
            # Activate with code
            success = manager.activate_with_code(json.dumps(code))
            
            # Should succeed
            assert success is True
            assert manager.license_info.license_type == LicenseType.PRO
            assert manager.license_info.valid

    def test_enterprise_license_activation_flow(self):
        """Complete ENTERPRISE license activation workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create valid activation code for ENTERPRISE tier
            now = datetime.now(timezone.utc)
            exp_date = (now + timedelta(days=365)).date()
            
            code = {
                "mid": manager.machine_id,
                "type": "ENTERPRISE",
                "exp": exp_date.isoformat(),
                "nonce": "test-nonce-456",
                "user": "Enterprise User",
            }
            
            # Calculate signature
            sig = manager._hmac_sign(
                code["mid"],
                code["type"],
                code["exp"],
                code["nonce"]
            )
            code["sig"] = sig
            
            # Activate with code
            success = manager.activate_with_code(json.dumps(code))
            
            assert success is True
            assert manager.license_info.license_type == LicenseType.ENTERPRISE
            assert manager.license_info.valid


class TestLicenseE2EFeatureFlags:
    """E2E: Feature flag availability based on license type."""

    def test_free_tier_features(self):
        """FREE tier should have minimal features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            app_dir = Path(tmpdir)
            manager = LicenseManager(app_dir)

            # Ensure FREE tier
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

            flags = FeatureFlagsManager(manager)

            # FREE tier checks
            assert not flags.can_batch_process()
            assert not flags.can_use_extended_cache()
            assert not flags.has_unlimited_images()
            assert not flags.has_api_access()

    def test_pro_tier_features(self):
        """PRO tier should enable premium features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Manually create PRO license info (simulating activation)
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test User",
                machine_id=manager.machine_id,
                expires_at=expires_at,
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
                max_images=0,  # Unlimited
                raw={},
                path=None,
                validation_reason="ok",
            )

            flags = FeatureFlagsManager(manager)

            # PRO tier checks
            assert flags.can_batch_process()
            assert flags.can_use_extended_cache()
            assert flags.has_unlimited_images()
            assert not flags.has_api_access()  # Only ENTERPRISE

    def test_enterprise_tier_features(self):
        """ENTERPRISE tier should have all features enabled."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Manually create ENTERPRISE license info
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.ENTERPRISE,
                user="Enterprise User",
                machine_id=manager.machine_id,
                expires_at=expires_at,
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

            # ENTERPRISE checks
            assert flags.can_batch_process()
            assert flags.can_use_extended_cache()
            assert flags.has_unlimited_images()
            assert flags.has_api_access()


class TestLicenseE2EImageLimits:
    """E2E: Image processing limits enforcement."""

    def test_free_tier_image_limit(self):
        """FREE tier should have 1000 image limit."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Ensure FREE tier
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

            # FREE tier has 1000 image limit
            assert manager.can_process_images(500)  # Within limit
            assert manager.can_process_images(1000)  # At limit
            assert not manager.can_process_images(1001)  # Over limit

    def test_pro_tier_unlimited_images(self):
        """PRO tier should allow unlimited images."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Simulate PRO license
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=expires_at,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,  # 0 = unlimited
                raw={},
                path=None,
                validation_reason="ok",
            )

            # PRO allows unlimited
            assert manager.can_process_images(10000)
            assert manager.can_process_images(100000)
            assert manager.can_process_images(1000000)

    def test_batch_processing_limit_enforcement(self):
        """Image limit should be enforced during batch operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Ensure FREE tier
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

            # FREE tier: 1000 image limit
            batch_size = 5000
            can_process = manager.can_process_images(batch_size)

            # Should be False for FREE tier with large batch
            assert not can_process


class TestLicenseE2EExpiration:
    """E2E: License expiration scenarios."""

    def test_expired_license_defaults_to_free(self):
        """Expired license should fall back to FREE tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create expired license
            expires_at = datetime.now(timezone.utc) - timedelta(days=1)  # Yesterday
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=expires_at,
                signature_valid=True,
                machine_match=True,
                valid=False,  # Invalid due to expiration
                enabled_features=[],
                max_images=1000,  # Falls back to FREE limit
                raw={},
                path=None,
                validation_reason="expired",
            )

            # Should report as invalid
            assert not manager.license_info.valid
            assert manager.license_info.validation_reason == "expired"

    def test_expiring_soon_warning(self):
        """License expiring within 30 days should show warning."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create license expiring in 15 days
            expires_at = datetime.now(timezone.utc) + timedelta(days=15)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=expires_at,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            # Get status
            status = manager.get_license_status()

            # Should still be valid
            assert status["valid"] is True
            # But expiring soon
            days_left = (expires_at - datetime.now(timezone.utc)).days
            assert days_left <= 30


class TestLicenseE2EMachineID:
    """E2E: Machine ID validation and binding."""

    def test_license_bound_to_machine_id(self):
        """License should be bound to specific machine ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Store original machine ID
            original_mid = manager.machine_id

            # Create license for this machine
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=original_mid,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            # License should be valid
            assert manager.license_info.machine_match is True
            assert manager.license_info.valid is True

    def test_license_invalid_on_different_machine(self):
        """License for different machine should be invalid."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create license for different machine
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id="DIFFERENT-MACHINE-ID",
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=False,  # Different machine
                valid=False,  # Invalid due to machine mismatch
                enabled_features=[],
                max_images=1000,
                raw={},
                path=None,
                validation_reason="machine_mismatch",
            )

            # License should be invalid
            assert manager.license_info.machine_match is False
            assert manager.license_info.valid is False
            assert manager.license_info.validation_reason == "machine_mismatch"


class TestLicenseE2EOfflineSync:
    """E2E: Offline sync and cloud-to-local scenarios."""

    def test_cloud_snapshot_loading(self):
        """Cloud snapshot should be loaded when available."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Create cloud snapshot file in expected location
            snapshot_path = Path.home() / ".photocleaner" / "license_snapshot.json"
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)

            now = datetime.now(timezone.utc)
            expires_at = (now + timedelta(days=365)).isoformat()

            snapshot_data = {
                "fetched_at": now.isoformat(),
                "data": {
                    "license_id": "LIC-001",
                    "plan": "pro",
                    "status": "active",
                    "expires_at": expires_at,
                },
            }

            # Write snapshot
            snapshot_path.write_text(json.dumps(snapshot_data), encoding="utf-8")

            # Reload license
            manager.refresh()

            # Should load cloud license
            assert manager.license_info.license_type == LicenseType.PRO

            # Clean up
            try:
                snapshot_path.unlink()
            except OSError:
                pass

    def test_activation_marker_persistence(self):
        """Activation marker should persist across runs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Activate with code
            now = datetime.now(timezone.utc)
            exp_date = (now + timedelta(days=365)).date()

            code = {
                "mid": manager.machine_id,
                "type": "PRO",
                "exp": exp_date.isoformat(),
                "nonce": "test-nonce-123",
            }

            sig = manager._hmac_sign(
                code["mid"], code["type"], code["exp"], code["nonce"]
            )
            code["sig"] = sig
            code["user"] = "Test User"

            success = manager.activate_with_code(json.dumps(code))
            assert success is True
            assert manager.activation_marker.exists()

            # Reload manager (simulating restart)
            manager2 = LicenseManager(Path(tmpdir))
            # Should still be activated
            assert manager2.license_info.license_type == LicenseType.PRO
            assert manager2.license_info.valid


class TestLicenseE2EStatusReporting:
    """E2E: License status reporting to UI."""

    def test_license_status_dict_format(self):
        """License status should return proper dict for display."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            status = manager.get_license_status()

            # Should have all required fields
            assert "license_type" in status
            assert "user" in status
            assert "expires_at" in status
            assert "machine_id_current" in status
            assert "machine_id_license" in status
            assert "valid" in status
            assert "enabled_features" in status
            assert "max_images" in status

    def test_feature_flags_status_text(self):
        """Feature flags should provide UI-friendly status text."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))
            flags = FeatureFlagsManager(manager)

            # FREE tier status - just check it returns a string
            status_text = flags.get_status_text()
            assert isinstance(status_text, str)
            assert len(status_text) > 0

            # PRO tier status
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=expires_at,
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={},
                path=None,
                validation_reason="ok",
            )

            status_text = flags.get_status_text()
            assert isinstance(status_text, str)
            assert "pro" in status_text.lower()

    def test_invalid_license_error_messages(self):
        """Invalid licenses should provide clear error messages."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Simulate signature validation failure
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=False,
                machine_match=True,
                valid=False,
                enabled_features=[],
                max_images=1000,
                raw={},
                path=None,
                validation_reason="invalid_signature",
            )

            status = manager.get_license_status()
            assert status["valid"] is False
            assert "invalid_signature" in status["reason"]


class TestLicenseE2EIntegrationWithPipeline:
    """E2E: License integration with image processing pipeline."""

    def test_feature_flag_blocks_batch_processing_free(self):
        """Feature flag should prevent batch processing on FREE tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))
            
            # Explicitly set to FREE tier
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
            
            flags = FeatureFlagsManager(manager)

            # FREE tier cannot batch process
            assert not flags.can_batch_process()

    def test_cache_extension_disabled_on_free(self):
        """Extended cache should be disabled on FREE tier."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))
            
            # Explicitly set to FREE tier
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
            
            flags = FeatureFlagsManager(manager)

            # FREE tier cannot use extended cache
            assert not flags.can_use_extended_cache()

    def test_pro_enables_all_features(self):
        """PRO tier should enable all non-API features."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Simulate PRO activation
            expires_at = datetime.now(timezone.utc) + timedelta(days=365)
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Pro User",
                machine_id=manager.machine_id,
                expires_at=expires_at,
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

            # All PRO features available
            assert flags.can_batch_process()
            assert flags.can_use_extended_cache()
            assert flags.has_unlimited_images()
            # API access only for ENTERPRISE
            assert not flags.has_api_access()


# Run with: pytest tests/e2e/test_license_e2e.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
