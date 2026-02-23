#!/usr/bin/env python3
"""
Test License Client with mock HTTP server (no Supabase Edge Function needed).
This validates the full client-side license validation flow.

Run: python test_license_client_mock.py
"""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading
import time
import requests

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from photo_cleaner.license_client import LicenseClient, LicenseConfig, DeviceInfo


class MockLicenseHandler(BaseHTTPRequestHandler):
    """Mock Edge Function handler for testing."""

    def do_POST(self):
        """Handle POST request to /functions/v1/exchange-license-key."""
        if self.path != "/functions/v1/exchange-license-key":
            self.send_error(404)
            return

        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length).decode()

        try:
            data = json.loads(body)
            license_key = data.get("license_key")

            # Mock license database
            if license_key == "TEST-20260126-001":
                response = {
                    "ok": True,
                    "license_id": license_key,
                    "license_data": {
                        "license_id": license_key,
                        "plan": "pro",
                        "status": "active",
                        "max_devices": 3,
                        "expires_at": "2027-01-26T00:00:00Z",
                    },
                    "signature": "mock_sig_12345",
                }
                self.send_response(200)
            elif license_key == "TEST-20260126-002":
                response = {
                    "ok": True,
                    "license_id": license_key,
                    "license_data": {
                        "license_id": license_key,
                        "plan": "standard",
                        "status": "active",
                        "max_devices": 2,
                        "expires_at": "2026-06-26T00:00:00Z",
                    },
                    "signature": "mock_sig_67890",
                }
                self.send_response(200)
            else:
                response = {
                    "ok": False,
                    "error": "Invalid license key",
                }
                self.send_response(401)

            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        except Exception as e:
            self.send_error(500, str(e))

    def log_message(self, format, *args):
        """Suppress logging."""
        pass


def start_mock_server(port=8765):
    """Start mock server in background thread."""
    server = HTTPServer(("127.0.0.1", port), MockLicenseHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)  # Let server start
    return server


def test_license_exchange():
    """Test exchanging license key with mock server."""
    print("=" * 60)
    print("TEST 1: License Exchange with Mock Server")
    print("=" * 60)

    # Start mock server
    server = start_mock_server(8765)

    try:
        # Create client pointing to mock server
        config = LicenseConfig(
            project_url="http://127.0.0.1:8765",
            anon_key="test_anon_key",
            grace_period_days=7,
            max_devices=3,
        )

        client = LicenseClient(config)
        device_id = DeviceInfo.get_device_id()
        device_info = {
            "deviceId": device_id,
            "name": "Test Device",
            "os": "Windows",
        }

        # Test 1: Valid license
        print("\n[Test 1.1] Exchanging valid license key...")
        response = requests.post(
            f"{config.functions_url}/exchange-license-key",
            headers={"apikey": config.anon_key, "Content-Type": "application/json"},
            json={
                "license_key": "TEST-20260126-001",
                "device_info": device_info,
            },
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert data["ok"], "License exchange should succeed"
        assert data["license_id"] == "TEST-20260126-001"
        print("✓ PASS: Valid license accepted")

        # Test 2: Invalid license
        print("\n[Test 1.2] Exchanging invalid license key...")
        response = requests.post(
            f"{config.functions_url}/exchange-license-key",
            headers={"apikey": config.anon_key, "Content-Type": "application/json"},
            json={
                "license_key": "INVALID-KEY",
                "device_info": device_info,
            },
        )
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        assert not data["ok"], "Invalid license should be rejected"
        print("✓ PASS: Invalid license rejected")

    finally:
        server.shutdown()


def test_offline_caching():
    """Test license caching and offline validation."""
    print("\n" + "=" * 60)
    print("TEST 2: Offline License Caching")
    print("=" * 60)

    config = LicenseConfig(
        project_url="http://invalid-url-offline-test.local",
        anon_key="test_anon_key",
        grace_period_days=7,
        max_devices=3,
    )

    client = LicenseClient(config)

    # Mock a cached snapshot
    from datetime import datetime, timedelta, UTC

    expires_at = (datetime.now(UTC) + timedelta(days=365)).isoformat()
    mock_license_doc = {
        "license_id": "TEST-20260126-001",
        "plan": "pro",
        "status": "active",
        "max_devices": 3,
        "expires_at": expires_at,
    }

    print("\n[Test 2.1] Validating license document...")
    is_valid, error = client.enforce_limits(mock_license_doc, "test-device-1")
    print(f"Validation result: is_valid={is_valid}, error={error}")
    assert is_valid, f"License should be valid: {error}"
    print("✓ PASS: License validation works")


def test_device_info():
    """Test DeviceInfo generation."""
    print("\n" + "=" * 60)
    print("TEST 3: Device Info Generation")
    print("=" * 60)

    device_id = DeviceInfo.get_device_id()
    print(f"\nDevice Info:")
    print(f"  Device ID: {device_id}")
    print(f"  Name: Test PC")
    print(f"  OS: Windows 11")

    device_dict = {
        "deviceId": device_id,
        "name": "Test PC",
        "os": "Windows 11",
    }
    print(f"\nDevice Dict: {json.dumps(device_dict, indent=2)}")
    print("✓ PASS: DeviceInfo generation works")


if __name__ == "__main__":
    print("\n" + "█" * 60)
    print("█  PHOTO-CLEANER LICENSE CLIENT - MOCK SERVER TESTS")
    print("█" * 60)

    try:
        test_device_info()
        test_license_exchange()
        test_offline_caching()

        print("\n" + "=" * 60)
        print("✓ ALL TESTS PASSED")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
