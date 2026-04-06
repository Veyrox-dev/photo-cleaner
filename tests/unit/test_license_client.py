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


class TestRequestWithRetry:
    """Tests für _request_with_retry – exponentielles Backoff + Retry-After."""

    def _make_response(self, status_code, headers=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.headers = headers or {}
        return resp

    @patch("photo_cleaner.license_client.time")
    def test_succeeds_on_first_attempt(self, mock_time):
        """Kein Retry wenn erster Request 200 zurückgibt."""
        from photo_cleaner.license_client import _request_with_retry

        ok = self._make_response(200)
        request_fn = Mock(return_value=ok)

        result = _request_with_retry(request_fn)

        assert result.status_code == 200
        request_fn.assert_called_once()
        mock_time.sleep.assert_not_called()

    @patch("photo_cleaner.license_client.time")
    def test_retries_on_503_then_succeeds(self, mock_time):
        """Erster Call liefert 503, zweiter 200 → Erfolg nach einem Retry."""
        from photo_cleaner.license_client import _request_with_retry

        responses = [self._make_response(503), self._make_response(200)]
        request_fn = Mock(side_effect=responses)

        result = _request_with_retry(request_fn)

        assert result.status_code == 200
        assert request_fn.call_count == 2
        mock_time.sleep.assert_called_once()

    @patch("photo_cleaner.license_client.time")
    def test_retries_on_502_then_succeeds(self, mock_time):
        """502 ist jetzt im Retryable-Set enthalten."""
        from photo_cleaner.license_client import _request_with_retry

        responses = [self._make_response(502), self._make_response(200)]
        request_fn = Mock(side_effect=responses)

        result = _request_with_retry(request_fn)

        assert result.status_code == 200
        assert request_fn.call_count == 2

    @patch("photo_cleaner.license_client.time")
    def test_raises_after_all_retries_fail(self, mock_time):
        """Nach allen Versuchen soll RequestException geworfen werden."""
        from photo_cleaner.license_client import _request_with_retry

        request_fn = Mock(return_value=self._make_response(503))

        with pytest.raises(requests.RequestException, match="HTTP 503"):
            _request_with_retry(request_fn, retries=3)

        assert request_fn.call_count == 3

    @patch("photo_cleaner.license_client.time")
    def test_raises_on_network_exception(self, mock_time):
        """Netzwerk-Exception soll nach allen Retries weitergereicht werden."""
        from photo_cleaner.license_client import _request_with_retry

        request_fn = Mock(side_effect=requests.ConnectionError("timeout"))

        with pytest.raises(requests.RequestException):
            _request_with_retry(request_fn, retries=2)

        assert request_fn.call_count == 2

    @patch("photo_cleaner.license_client.time")
    def test_dns_failure_does_not_retry(self, mock_time):
        """NameResolutionError / socket.gaierror soll sofort ohne Retry abbrechen."""
        import socket
        from photo_cleaner.license_client import _request_with_retry

        dns_cause = socket.gaierror(11001, "getaddrinfo failed")
        conn_err = requests.ConnectionError("DNS failed")
        conn_err.__cause__ = dns_cause
        request_fn = Mock(side_effect=conn_err)

        with pytest.raises(requests.ConnectionError):
            _request_with_retry(request_fn, retries=4)

        # Must NOT retry – only one call allowed
        request_fn.assert_called_once()
        mock_time.sleep.assert_not_called()

    @patch("photo_cleaner.license_client.time")
    def test_honours_retry_after_integer_header(self, mock_time):
        """Retry-After-Header als Integer soll als Wartezeit genutzt werden."""
        from photo_cleaner.license_client import _request_with_retry

        resp_503 = self._make_response(503, headers={"Retry-After": "5"})
        resp_200 = self._make_response(200)
        request_fn = Mock(side_effect=[resp_503, resp_200])

        _request_with_retry(request_fn, retries=4, max_backoff=10.0)

        mock_time.sleep.assert_called_once()
        actual_delay = mock_time.sleep.call_args[0][0]
        # Retry-After=5 capped at max_backoff=10 → delay == 5.0
        assert actual_delay == pytest.approx(5.0)

    @patch("photo_cleaner.license_client.time")
    def test_retry_after_capped_at_max_backoff(self, mock_time):
        """Retry-After-Wert größer als max_backoff soll auf max_backoff gecappt werden."""
        from photo_cleaner.license_client import _request_with_retry

        resp_503 = self._make_response(503, headers={"Retry-After": "60"})
        resp_200 = self._make_response(200)
        request_fn = Mock(side_effect=[resp_503, resp_200])

        _request_with_retry(request_fn, retries=4, max_backoff=10.0)

        actual_delay = mock_time.sleep.call_args[0][0]
        assert actual_delay == pytest.approx(10.0)

    @patch("photo_cleaner.license_client.time")
    def test_retry_after_zero_uses_minimum_delay(self, mock_time):
        """Retry-After=0 darf keinen 0.0s-Tight-Loop erzeugen."""
        from photo_cleaner.license_client import _request_with_retry

        resp_503 = self._make_response(503, headers={"Retry-After": "0"})
        resp_200 = self._make_response(200)
        request_fn = Mock(side_effect=[resp_503, resp_200])

        _request_with_retry(request_fn, retries=4, max_backoff=10.0)

        actual_delay = mock_time.sleep.call_args[0][0]
        assert actual_delay >= 0.25

    @patch("photo_cleaner.license_client.time")
    def test_budget_exhausted_stops_retrying(self, mock_time):
        """Wenn Retry-After > Budget-Rest: kein weiterer Retry."""
        from photo_cleaner.license_client import _request_with_retry

        # All calls return 503 so we track how many were made.
        request_fn = Mock(return_value=self._make_response(503))

        # base_backoff=40 with max_backoff=100: first raw delay ≈ 40s which
        # already exceeds the 30s budget → loop breaks after the first attempt.
        with pytest.raises(requests.RequestException):
            _request_with_retry(request_fn, retries=4, base_backoff=40.0, max_backoff=100.0)

        # Should not have made all 4 attempts because budget is exhausted.
        assert request_fn.call_count < 4

    @patch("photo_cleaner.license_client.time")
    def test_exponential_backoff_increases(self, mock_time):
        """Backoff soll zwischen Retries steigen (grob exponentiell)."""
        from photo_cleaner.license_client import _request_with_retry

        request_fn = Mock(return_value=self._make_response(503))

        with pytest.raises(requests.RequestException):
            _request_with_retry(request_fn, retries=4, base_backoff=1.0, max_backoff=100.0)

        sleep_calls = [c[0][0] for c in mock_time.sleep.call_args_list]
        # Each successive delay should be >= the previous (ignoring jitter noise)
        # base_backoff * 2^0 = 1, * 2^1 = 2, * 2^2 = 4 — allow ±30 % for jitter
        for i in range(1, len(sleep_calls)):
            assert sleep_calls[i] >= sleep_calls[i - 1] * 0.7

    @patch("photo_cleaner.license_client.time")
    def test_exchange_license_key_retries_on_503(self, mock_time):
        """exchange_license_key soll bei transientem 503 automatisch retrien."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_anon_key",
            )
            client = LicenseClient(config, cache_dir=Path(tmpdir))

            resp_503 = self._make_response(503)
            resp_503.headers = {}
            payload = {
                "ok": True,
                "license_id": "TEST-001",
                "license_data": {
                    "license_id": "TEST-001",
                    "status": "active",
                    "plan": "basic",
                    "expires_at": (
                        datetime.now(timezone.utc) + timedelta(days=30)
                    ).isoformat(),
                },
                "signature": "sig",
            }
            resp_200 = self._make_response(200)
            resp_200.json = Mock(return_value=payload)

            with patch("photo_cleaner.license_client.requests") as mock_req:
                mock_req.post.side_effect = [resp_503, resp_200]
                mock_req.RequestException = requests.RequestException

                success, license_id, error = client.exchange_license_key("TEST-KEY")

            assert success is True
            assert license_id == "TEST-001"
            assert mock_req.post.call_count == 2

    @patch("photo_cleaner.license_client.time")
    def test_exchange_license_key_dns_error_returns_actionable_message(self, mock_time):
        """DNS-Fehler sollen als klare User-Meldung zurückgegeben werden."""
        import socket

        with tempfile.TemporaryDirectory() as tmpdir:
            config = LicenseConfig(
                project_url="https://test.supabase.co",
                anon_key="test_anon_key",
            )
            client = LicenseClient(config, cache_dir=Path(tmpdir))

            dns_cause = socket.gaierror(11001, "getaddrinfo failed")
            conn_err = requests.ConnectionError("DNS failed")
            conn_err.__cause__ = dns_cause

            with patch("photo_cleaner.license_client.requests") as mock_req:
                mock_req.post.side_effect = conn_err
                mock_req.RequestException = requests.RequestException
                mock_req.Timeout = requests.Timeout
                mock_req.ConnectionError = requests.ConnectionError

                success, license_id, error = client.exchange_license_key("TEST-KEY")

            assert success is False
            assert license_id is None
            assert "DNS lookup failed" in error
            assert "exchange-license-key" in error
            request_calls = mock_req.post.call_count
            assert request_calls == 1
            mock_time.sleep.assert_not_called()
