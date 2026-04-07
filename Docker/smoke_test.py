"""Headless smoke-test for PhotoCleaner Docker image.
Exit 0 = all imports and CLI startup OK.
"""
import sys

print("--- Import check ---")
try:
    from photo_cleaner.cli import cli
    from photo_cleaner.license_client import LicenseClient, LicenseConfig
    from photo_cleaner.license.crypto_utils import verify_ed25519_signature
    print("OK: alle Module importiert")
except Exception as e:
    print(f"FAIL: Import fehlgeschlagen: {e}")
    sys.exit(1)

print("--- CLI check ---")
try:
    from click.testing import CliRunner
    result = CliRunner().invoke(cli, ["--help"])
    print(result.output[:300])
    if result.exit_code != 0:
        print(f"FAIL: CLI exit_code={result.exit_code}")
        if result.exception:
            import traceback
            traceback.print_exception(type(result.exception), result.exception, result.exception.__traceback__)
        sys.exit(1)
    print("OK: CLI gestartet")
except Exception as e:
    print(f"FAIL: CLI-Check fehlgeschlagen: {e}")
    sys.exit(1)

print("--- Smoke-Test PASSED ---")
sys.exit(0)
