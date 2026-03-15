"""
Unit-Tests für photo_cleaner.license_client.

Tests für Device-ID, Grace-Period, Enforcement, Snapshot-Cache.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest
import requests

from photo_cleaner.license_client import (
    DeviceInfo,
    LicenseConfig,
    LicenseClient,
    LicenseManager,
)


@pytest.fixture
def signature_ok(monkeypatch):
    monkeypatch.setattr(
        "photo_cleaner.license_client.verify_ed25519_signature",
        lambda payload, sig: True,
    )


class TestDeviceInfo:
    """Tests für Geräte-ID und Geräte-Info."""
    
    def test_get_device_id_creates_stable_id(self):
        """Device-ID sollte stabil sein (zwei Calls mit gleicher Salt liefern gleiche ID)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file = Path(tmpdir) / "salt"
            
            id1 = DeviceInfo.get_device_id(salt_file)
            id2 = DeviceInfo.get_device_id(salt_file)
            
            assert id1 == id2, "Device-ID sollte stabil sein"
            assert salt_file.exists(), "Salt-Datei sollte erstellt sein"
    
    def test_get_device_id_different_salt_different_id(self):
        """Verschiedene Salt-Dateien sollten unterschiedliche IDs erzeugen."""
        with tempfile.TemporaryDirectory() as tmpdir:
            salt_file1 = Path(tmpdir) / "salt1"
            salt_file2 = Path(tmpdir) / "salt2"
            
            id1 = DeviceInfo.get_device_id(salt_file1)
            id2 = DeviceInfo.get_device_id(salt_file2)
            
            assert id1 != id2, "Unterschiedliche Salt sollte unterschiedliche IDs erzeugen"
    
    def test_get_device_name_returns_hostname(self):
        """Device-Name sollte Hostname zurückgeben."""
        name = DeviceInfo.get_device_name()
        assert isinstance(name, str)
        assert len(name) > 0
    
    def test_get_device_os_returns_valid_os(self):
        """Device-OS sollte gültig sein (Windows, macOS, Linux, Unknown)."""
        os_name = DeviceInfo.get_device_os()
        valid_os = ["Windows", "macOS", "Linux", "Unknown"]
        assert os_name in valid_os


class TestLicenseConfig:
    """Tests für LicenseConfig."""
    
    def test_config_init(self):
        """Config sollte URLs korrekt normalisieren."""
        config = LicenseConfig(
            project_url="https://test.supabase.co/",
            anon_key="test_key",
            grace_period_days=7,
            max_devices=3,
        )
        
        assert config.project_url == "https://test.supabase.co"
        assert config.rest_url == "https://test.supabase.co/rest/v1"
        assert config.functions_url == "https://test.supabase.co/functions/v1"
        assert config.grace_period_days == 7
        assert config.max_devices == 3


class TestLicenseClient:
    """Tests für LicenseClient."""
    
    @pytest.fixture
    def config(self):
        """Fixture: Test-LicenseConfig."""
        return LicenseConfig(
            project_url="https://test.supabase.co",
            anon_key="test_anon_key",
            grace_period_days=7,
            max_devices=3,
        )
    
    @pytest.fixture
    def client(self, config):
        """Fixture: Test-LicenseClient mit temp cache dir."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LicenseClient(config, cache_dir=Path(tmpdir))
    
    def test_client_init(self, config):
        """Client sollte initialisierbar sein."""
        with tempfile.TemporaryDirectory() as tmpdir:
            client = LicenseClient(config, cache_dir=Path(tmpdir))
            assert client.config == config
            assert client.cache_dir.exists()
    
    def test_enforce_limits_active_license(self, client):
        """Enforce sollte aktive Lizenz akzeptieren."""
        license_doc = {
            "license_id": "TEST-001",
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "max_devices": 3,
        }
        
        is_valid, error = client.enforce_limits(license_doc, "device-1")
        
        assert is_valid is True
        assert error == ""
    
    def test_enforce_limits_expired_license(self, client):
        """Enforce sollte abgelaufene Lizenz ablehnen."""
        license_doc = {
            "license_id": "TEST-001",
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "max_devices": 3,
        }
        
        is_valid, error = client.enforce_limits(license_doc, "device-1")
        
        assert is_valid is False
        assert "abgelaufen" in error.lower() or "expired" in error.lower()
    
    def test_enforce_limits_suspended_license(self, client):
        """Enforce sollte gesperrte Lizenz ablehnen."""
        license_doc = {
            "license_id": "TEST-001",
            "status": "suspended",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "max_devices": 3,
        }
        
        is_valid, error = client.enforce_limits(license_doc, "device-1")
        
        assert is_valid is False
        assert "suspended" in error.lower() or "gesperrt" in error.lower()

    def test_enforce_limits_device_not_registered(self, client):
        """Enforce sollte nicht registrierte Geraete blocken, wenn Liste vorhanden ist."""
        license_doc = {
            "license_id": "TEST-001",
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            "max_devices": 3,
            "registered_devices": ["device-2"],
        }

        is_valid, error = client.enforce_limits(license_doc, "device-1")

        assert is_valid is False
        assert "geraet" in error.lower() or "device" in error.lower()
    
    def test_cache_snapshot_and_load(self, client, signature_ok):
        """Cache sollte Snapshot speichern und laden können."""
        license_id = "TEST-001"
        license_data = {
            "license_id": license_id,
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        
        # Speichere
        client._cache_snapshot(license_id, license_data, signature="test_sig")
        
        # Lade
        success, loaded_data, error = client._load_cached_snapshot(license_id)
        
        assert success is True
        assert loaded_data is not None
        assert loaded_data["license_id"] == license_id
    
    def test_cache_expires_after_grace_period(self, client, signature_ok):
        """Cache sollte nach Grace-Period ablaufen."""
        license_id = "TEST-001"
        license_data = {
            "license_id": license_id,
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        
        # Speichere mit altem Zeitstempel
        old_time = (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()
        snapshot = {
            "license_id": license_id,
            "data": license_data,
            "fetched_at": old_time,
        }
        
        with open(client.snapshot_file, "w") as f:
            json.dump(snapshot, f)
        client.signature_file.write_text("test_sig", encoding="utf-8")
        
        # Lade
        success, loaded_data, error = client._load_cached_snapshot(license_id)
        
        # Mit grace_period=7 sollte 8 Tage alt sein → ablaufen
        assert success is False
        assert "7" in error or "days" in error.lower()
    
    @patch("photo_cleaner.license_client.requests")
    def test_fetch_license_online(self, mock_requests, client):
        """Fetch sollte Online-Lizenz abrufen."""
        # Setup mock requests module
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "license_id": "TEST-001",
                "status": "active",
                "plan": "basic",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            }
        ]
        mock_requests.get.return_value = mock_response
        # Make RequestException work with mock
        mock_requests.RequestException = requests.RequestException
        mock_requests.HTTPError = requests.HTTPError
        
        success, license_data, error = client.fetch_license("TEST-001")
        
        assert success is True
        assert license_data["license_id"] == "TEST-001"
    

    def test_load_cached_snapshot_valid_cache(self, client, signature_ok):
        """Lade gecachten Snapshot wenn gültig."""
        license_id = "TEST-001"
        license_data = {
            "license_id": license_id,
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        
        # Pre-cache mit aktuellem Zeitstempel
        client._cache_snapshot(license_id, license_data, signature="test_sig")
        
        # Lade
        success, loaded_data, error = client._load_cached_snapshot(license_id)
        
        assert success is True
        assert loaded_data["license_id"] == license_id

    def test_load_cached_snapshot_uses_embedded_signature_when_sidecar_missing(self, client, signature_ok):
        """Fallback: eingebettete Signatur im Snapshot soll weiter funktionieren."""
        license_id = "TEST-001"
        license_data = {
            "license_id": license_id,
            "status": "active",
            "plan": "basic",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }

        snapshot = {
            "license_id": license_id,
            "data": license_data,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "signature": "embedded_test_sig",
        }
        with open(client.snapshot_file, "w") as f:
            json.dump(snapshot, f)

        success, loaded_data, error = client._load_cached_snapshot(license_id)

        assert success is True
        assert loaded_data is not None
        assert loaded_data["license_id"] == license_id
        assert client.signature_file.exists()

    def test_load_cached_snapshot_missing_signature_returns_generic_cache_error(self, client):
        """Ohne Signatur soll ein allgemeiner Offline-Cache-Fehler kommen."""
        license_id = "TEST-001"
        snapshot = {
            "license_id": license_id,
            "data": {"license_id": license_id, "status": "active", "plan": "basic"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(client.snapshot_file, "w") as f:
            json.dump(snapshot, f)

        success, loaded_data, error = client._load_cached_snapshot(license_id)

        assert success is False
        assert loaded_data is None
        assert "Offline-Cache" in error

    def test_load_cached_snapshot_missing_signature_removes_orphan_snapshot(self, client):
        """Unsigned orphan snapshot should be removed to avoid repeated warning loops."""
        license_id = "TEST-001"
        snapshot = {
            "license_id": license_id,
            "data": {"license_id": license_id, "status": "active", "plan": "basic"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(client.snapshot_file, "w") as f:
            json.dump(snapshot, f)

        success, loaded_data, error = client._load_cached_snapshot(license_id)

        assert success is False
        assert loaded_data is None
        assert "Offline-Cache" in error
        assert not client.snapshot_file.exists()

    def test_load_cached_snapshot_invalid_signature_cleans_cache_pair(self, client, monkeypatch):
        """Invalid signature should clean snapshot + sidecar to avoid warning loops."""
        license_id = "TEST-001"
        snapshot = {
            "license_id": license_id,
            "data": {"license_id": license_id, "status": "active", "plan": "basic"},
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(client.snapshot_file, "w") as f:
            json.dump(snapshot, f)
        client.signature_file.write_text("invalid_sig", encoding="utf-8")

        monkeypatch.setattr(
            "photo_cleaner.license_client.verify_ed25519_signature",
            lambda payload, sig: False,
        )

        success, loaded_data, error = client._load_cached_snapshot(license_id)

        assert success is False
        assert loaded_data is None
        assert "Signatur" in error
        assert not client.snapshot_file.exists()
        assert not client.signature_file.exists()

    def test_resolve_cache_signature_prefers_existing_sidecar(self, client):
        """Wenn Payload keine Signatur hat, soll vorhandene Sidecar-Signatur genutzt werden."""
        client.signature_file.write_text("sidecar_sig", encoding="utf-8")

        resolved = client._resolve_cache_signature({"license_id": "TEST-001"})

        assert resolved == "sidecar_sig"


class TestLicenseManager:
    """Tests für High-Level LicenseManager."""
    
    @pytest.fixture
    def config(self):
        return LicenseConfig(
            project_url="https://test.supabase.co",
            anon_key="test_anon_key",
        )
    
    @pytest.fixture
    def manager(self, config):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield LicenseManager(config, cache_dir=Path(tmpdir))
    
    def test_manager_init(self, manager):
        """Manager sollte initialisierbar sein."""
        assert manager.current_license_id is None
        assert manager.current_license_data is None
    
    def test_get_status_no_license(self, manager):
        """Status sollte "keine Lizenz" anzeigen, wenn nicht aktiviert."""
        status = manager.get_status()
        assert "Keine Lizenz" in status or "No license" in status
    
    @patch.object(LicenseClient, "exchange_license_key")
    @patch.object(LicenseClient, "fetch_license")
    @patch.object(LicenseClient, "enforce_limits")
    def test_activate_with_key_success(self, mock_enforce, mock_fetch, mock_exchange, manager):
        """Aktivierung sollte erfolgreich sein bei gültiger Lizenz."""
        mock_exchange.return_value = (True, "TEST-001", "")
        mock_fetch.return_value = (
            True,
            {
                "license_id": "TEST-001",
                "status": "active",
                "plan": "pro",
                "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            },
            "",
        )
        mock_enforce.return_value = (True, "")
        
        success, message = manager.activate_with_key("TEST-KEY-001")
        
        assert success is True
        assert "aktiviert" in message.lower() or "activated" in message.lower()
        assert manager.current_license_id == "TEST-001"

    @patch.object(LicenseClient, "exchange_license_key")
    @patch.object(LicenseClient, "fetch_license")
    @patch.object(LicenseClient, "enforce_limits")
    def test_activate_with_key_uses_exchange_payload_when_fetch_fails(self, mock_enforce, mock_fetch, mock_exchange, manager, monkeypatch):
        """Aktivierung soll mit gueltigem Exchange-Payload auch ohne fetch() gelingen."""
        license_data = {
            "license_id": "TEST-001",
            "status": "active",
            "plan": "pro",
            "expires_at": (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
        }
        manager.client._last_exchange_payload = {
            "license_id": "TEST-001",
            "license_data": license_data,
            "signature": "sig",
        }

        monkeypatch.setattr(
            "photo_cleaner.license_client.verify_ed25519_signature",
            lambda payload, sig: True,
        )

        mock_exchange.return_value = (True, "TEST-001", "")
        mock_fetch.return_value = (False, None, "Kein gueltiger Offline-Cache vorhanden")
        mock_enforce.return_value = (True, "")

        success, message = manager.activate_with_key("TEST-KEY-001")

        assert success is True
        assert "aktiviert" in message.lower() or "activated" in message.lower()
        mock_fetch.assert_not_called()
    
    @patch.object(LicenseClient, "exchange_license_key")
    def test_activate_with_key_invalid_key(self, mock_exchange, manager):
        """Aktivierung sollte fehlschlagen bei ungültigem Schlüssel."""
        mock_exchange.return_value = (False, None, "Invalid license key")
        
        success, message = message = manager.activate_with_key("INVALID-KEY")
        
        assert success is False
        error_msg = message if isinstance(message, str) else str(message)
        assert "fehlgeschlagen" in error_msg.lower() or "failed" in error_msg.lower()
