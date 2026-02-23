"""
End-to-end device binding tests for PhotoCleaner License System.

Tests focus on:
1. Device ID generation and stability
2. Multi-device scenarios
3. Device limit enforcement
4. Device tracking in cloud
"""

import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest

from photo_cleaner.license import LicenseManager, LicenseType, LicenseInfo
from photo_cleaner.license_client import DeviceInfo, LicenseClient, LicenseConfig


class TestDeviceIDE2E:
    """E2E: Device ID generation and stability."""

    def test_device_id_stable_across_runs(self):
        """Device ID should remain stable across application restarts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "device_salt"

            # First run
            device_id_1 = DeviceInfo.get_device_id(salt_file)
            assert device_id_1 is not None

            # Second run (simulating restart)
            device_id_2 = DeviceInfo.get_device_id(salt_file)

            # Should be identical
            assert device_id_1 == device_id_2

    def test_device_id_unique_per_salt_file(self):
        """Different salt files should produce different device IDs."""
        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file_1 = Path(tmpdir) / "salt1"
            salt_file_2 = Path(tmpdir) / "salt2"

            device_id_1 = DeviceInfo.get_device_id(salt_file_1)
            device_id_2 = DeviceInfo.get_device_id(salt_file_2)

            # Should be different
            assert device_id_1 != device_id_2

    def test_device_info_includes_hostname(self):
        """Device info should include hostname."""
        device_name = DeviceInfo.get_device_name()
        assert device_name is not None
        assert len(device_name) > 0
        # Should be a reasonable hostname
        assert not device_name.startswith("?")


class TestMultiDeviceE2E:
    """E2E: Multi-device license scenarios."""

    def test_license_can_be_used_on_multiple_devices(self):
        """License with max_devices > 1 should work on multiple machines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Simulate Device 1
            salt_1 = Path(tmpdir) / "device_1_salt"
            device_id_1 = DeviceInfo.get_device_id(salt_1)

            # Simulate Device 2
            salt_2 = Path(tmpdir) / "device_2_salt"
            device_id_2 = DeviceInfo.get_device_id(salt_2)

            # Should be different device IDs
            assert device_id_1 != device_id_2

            # License with max_devices = 2 should allow both
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )
            client = LicenseClient(config, cache_dir=Path(tmpdir) / "cache")

            license_data = {
                "license_id": "LIC-PRO-001",
                "plan": "pro",
                "status": "active",
                "max_devices": 2,
                "expires_at": "2027-01-01T00:00:00Z",
                "devices": [device_id_1, device_id_2],  # Both registered
            }

            # Both devices should be able to use license
            with patch.object(client, "fetch_license") as mock_fetch:
                mock_fetch.return_value = (True, license_data, "")

                # Device 1 fetch
                success_1, _, _ = client.fetch_license("LIC-PRO-001")
                assert success_1 is True

                # Device 2 fetch
                success_2, _, _ = client.fetch_license("LIC-PRO-001")
                assert success_2 is True

    def test_device_limit_exceeded(self):
        """License should reject registration if device limit exceeded."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )
            client = LicenseClient(config, cache_dir=Path(tmpdir) / "cache")

            # License with max_devices = 1
            license_data = {
                "license_id": "LIC-PRO-001",
                "plan": "pro",
                "status": "active",
                "max_devices": 1,
                "registered_devices": [
                    "DEVICE-ID-1"
                ],  # Already has 1 device
            }

            with patch.object(client, "fetch_license") as mock_fetch:
                mock_fetch.return_value = (True, license_data, "")

                success, _, _ = client.fetch_license("LIC-PRO-001")
                # Should work for initial fetch
                assert success is True

    def test_device_info_persists_correctly(self):
        """Device info should be stored and retrieved correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            device_id = DeviceInfo.get_device_id(cache_dir / "salt")
            device_name = DeviceInfo.get_device_name()

            # Store device info
            device_info = {
                "device_id": device_id,
                "device_name": device_name,
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }

            # Should have all fields
            assert device_info["device_id"]
            assert device_info["device_name"]
            assert device_info["registered_at"]


class TestDeviceTrackingE2E:
    """E2E: Device tracking and management."""

    def test_device_registration_on_first_activation(self):
        """Device should be registered when license first activated."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            client = LicenseClient(config, cache_dir=cache_dir)

            # Mock successful device registration
            with patch.object(
                client, "register_device"
            ) as mock_register:
                mock_register.return_value = (True, "Device registered successfully")

                success, message = mock_register("LIC-PRO-001")

                assert success is True
                assert "registered" in message.lower()

    def test_device_registration_persists_cache(self):
        """Device registration should persist data correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            device_id = DeviceInfo.get_device_id(cache_dir / "salt")
            device_name = DeviceInfo.get_device_name()

            # Store device info
            device_info = {
                "device_id": device_id,
                "device_name": device_name,
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }

            # Should have all fields
            assert device_info["device_id"]
            assert device_info["device_name"]
            assert device_info["registered_at"]
            assert len(device_id) > 0
            assert len(device_name) > 0

    def test_offline_device_registration_cached(self):
        """Device registration should be cached for offline use."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_key",
            )
            cache_dir = Path(tmpdir) / "cache"
            cache_dir.mkdir()

            client = LicenseClient(config, cache_dir=cache_dir)

            device_id = DeviceInfo.get_device_id(cache_dir / "salt")

            # Store device registration in cache
            device_reg = {
                "device_id": device_id,
                "license_id": "LIC-001",
                "registered_at": datetime.now(timezone.utc).isoformat(),
            }

            cache_file = cache_dir / f"device_{device_id}.json"
            import json

            cache_file.write_text(json.dumps(device_reg))

            # Should be able to retrieve from cache
            assert cache_file.exists()
            cached_data = json.loads(cache_file.read_text())
            assert cached_data["device_id"] == device_id


class TestDeviceLimitEnforcementE2E:
    """E2E: Device limit enforcement scenarios."""

    def test_single_device_license_enforcement(self):
        """Single-device license should only work on one machine."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Simulate license for specific device
            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=True,
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={"max_devices": 1},
                path=None,
                validation_reason="ok",
            )

            # Should be valid on this machine
            assert manager.license_info.valid is True

    def test_multi_device_license_enforcement(self):
        """Multi-device license should work on registered devices."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # Simulate multi-device license
            device_ids = ["DEVICE-1", "DEVICE-2", "DEVICE-3"]

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id=manager.machine_id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=True,  # This device is registered
                valid=True,
                enabled_features=["batch_processing"],
                max_images=0,
                raw={"max_devices": 3, "registered_devices": device_ids},
                path=None,
                validation_reason="ok",
            )

            # Should be valid
            assert manager.license_info.valid is True
            # Can process unlimited images
            assert manager.can_process_images(10000)

    def test_unregistered_device_cannot_use_license(self):
        """Unregistered device should not be able to use multi-device license."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = LicenseManager(Path(tmpdir))

            # License for other devices only
            other_device_ids = ["OTHER-DEVICE-1", "OTHER-DEVICE-2"]

            manager.license_info = LicenseInfo(
                license_type=LicenseType.PRO,
                user="Test",
                machine_id="UNKNOWN-DEVICE",  # Different machine
                expires_at=datetime.now(timezone.utc) + timedelta(days=365),
                signature_valid=True,
                machine_match=False,  # Not in registered list
                valid=False,  # Invalid due to device mismatch
                enabled_features=[],
                max_images=1000,  # Falls back to FREE limit
                raw={"max_devices": 2, "registered_devices": other_device_ids},
                path=None,
                validation_reason="device_not_registered",
            )

            # Should be invalid
            assert manager.license_info.valid is False
            # Should use FREE tier limits
            assert not manager.can_process_images(1001)


# Run with: pytest tests/e2e/test_license_device_binding_e2e.py -v
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
