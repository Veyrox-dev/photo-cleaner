from __future__ import annotations

import pytest

from photo_cleaner.services.license_service import LicenseService


class _FakeLicenseManager:
    def __init__(self) -> None:
        self.refresh_called = 0
        self.remove_result = True
        self.status = {"license_type": "FREE", "valid": False}

    def refresh(self) -> None:
        self.refresh_called += 1

    def remove_license(self) -> bool:
        return self.remove_result

    def get_license_status(self) -> dict:
        return self.status


class _FakeCloudManager:
    def __init__(self, _config) -> None:
        self.result = (True, "ok")
        self.calls: list[str] = []

    def activate_with_key(self, license_key: str):
        self.calls.append(license_key)
        return self.result


@pytest.mark.unit
@pytest.mark.license
class TestLicenseService:
    def test_is_cloud_configured_false_when_env_missing(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: None,
        )

        service = LicenseService(_FakeLicenseManager())

        assert service.is_cloud_configured() is False

    def test_activate_with_key_raises_when_cloud_not_configured(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: None,
        )
        service = LicenseService(_FakeLicenseManager())

        with pytest.raises(RuntimeError, match="Cloud licensing not configured"):
            service.activate_with_key("TEST-KEY")

    def test_activate_success_refreshes_license_manager(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: object(),
        )
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.CloudLicenseManager",
            _FakeCloudManager,
        )

        manager = _FakeLicenseManager()
        service = LicenseService(manager)

        success, message = service.activate_with_key("TEST-KEY")

        assert success is True
        assert message == "ok"
        assert manager.refresh_called == 1

    def test_activate_failure_does_not_refresh_license_manager(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: object(),
        )
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.CloudLicenseManager",
            _FakeCloudManager,
        )

        manager = _FakeLicenseManager()
        service = LicenseService(manager)
        service.cloud_license_manager.result = (False, "invalid")

        success, message = service.activate_with_key("BAD-KEY")

        assert success is False
        assert message == "invalid"
        assert manager.refresh_called == 0

    def test_activate_success_with_refresh_error_is_graceful(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: object(),
        )
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.CloudLicenseManager",
            _FakeCloudManager,
        )

        manager = _FakeLicenseManager()

        def _refresh_raises():
            raise OSError("refresh failed")

        manager.refresh = _refresh_raises
        service = LicenseService(manager)

        success, message = service.activate_with_key("TEST-KEY")

        assert success is True
        assert message == "ok"

    def test_remove_license_passthrough(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: None,
        )
        manager = _FakeLicenseManager()
        manager.remove_result = False
        service = LicenseService(manager)

        assert service.remove_license() is False

    def test_get_license_status_passthrough(self, monkeypatch):
        monkeypatch.setattr(
            "photo_cleaner.services.license_service.get_cloud_license_config",
            lambda **_kwargs: None,
        )
        manager = _FakeLicenseManager()
        manager.status = {"license_type": "PRO", "valid": True}
        service = LicenseService(manager)

        assert service.get_license_status() == {"license_type": "PRO", "valid": True}
