#!/usr/bin/env python3
"""Diagnose Supabase exchange signature compatibility.

Checks whether the deployed exchange-license-key function returns an Ed25519
signature that verifies against the app's embedded PUBLIC_KEY_PEM.

Usage (PowerShell):
  .venv\Scripts\python.exe scripts\diagnose_supabase_signature.py --license-key ENT-CHRIS-2026
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
from pathlib import Path

import requests


def _load_env_file(dotenv_path: Path) -> None:
    if not dotenv_path.exists():
        return
    for line in dotenv_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and value and key not in os.environ:
            os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Diagnose Supabase signature flow")
    parser.add_argument("--license-key", required=True, help="License key to test")
    parser.add_argument("--timeout", type=float, default=20.0, help="HTTP timeout in seconds")
    return parser.parse_args()


def _build_device_info() -> dict[str, str]:
    return {
        "machine_id": "diag-" + socket.gethostname().lower(),
        "device_id": "diag-" + socket.gethostname().lower(),
        "hostname": socket.gethostname(),
        "platform": sys.platform,
    }


def main() -> int:
    project_root = Path(__file__).resolve().parents[1]
    _load_env_file(project_root / ".env")

    args = parse_args()
    project_url = os.getenv("SUPABASE_PROJECT_URL", "").rstrip("/")
    anon_key = os.getenv("SUPABASE_ANON_KEY", "")

    if not project_url or not anon_key:
        print("ERROR: Missing SUPABASE_PROJECT_URL or SUPABASE_ANON_KEY")
        return 2

    url = f"{project_url}/functions/v1/exchange-license-key"
    headers = {
        "Authorization": f"Bearer {anon_key}",
        "apikey": anon_key,
        "Content-Type": "application/json",
    }
    payload = {
        "license_key": args.license_key,
        "device_info": _build_device_info(),
    }

    print(f"[diag] POST {url}")

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=args.timeout)
    except requests.RequestException as exc:
        print(f"[diag] NETWORK ERROR: {exc}")
        return 3

    print(f"[diag] HTTP {response.status_code}")

    try:
        data = response.json()
    except ValueError:
        print("[diag] ERROR: Response is not JSON")
        print(response.text[:1000])
        return 4

    print("[diag] Response keys:", sorted(data.keys()) if isinstance(data, dict) else type(data).__name__)

    if not isinstance(data, dict):
        print("[diag] ERROR: Unexpected response shape")
        return 5

    if not data.get("ok"):
        print("[diag] Function returned not-ok:")
        print(json.dumps(data, indent=2, ensure_ascii=True))
        if response.status_code == 500:
            print("[hint] Check function secrets: LICENSE_SIGNING_PRIVATE_KEY, SUPABASE_DB_URL")
        return 6

    license_data = data.get("license_data")
    signature = data.get("signature")

    if not isinstance(license_data, dict):
        print("[diag] ERROR: license_data missing or invalid")
        return 7

    if not isinstance(signature, str) or not signature.strip():
        print("[diag] ERROR: signature missing in exchange response")
        return 8

    print(f"[diag] signature_len={len(signature)}")
    if len(signature) < 80:
        print("[hint] Signature length is unexpectedly short for Ed25519 Base64 (~88 expected).")
        print("[hint] Likely legacy signer / wrong payload / truncated signature.")

    from photo_cleaner.license.crypto_utils import verify_ed25519_signature

    verified = verify_ed25519_signature(license_data, signature)
    print(f"[diag] verify_ed25519_signature={verified}")

    if not verified:
        print("[hint] Mismatch between server private signing key and app PUBLIC_KEY_PEM.")
        print("[hint] Ensure deployed exchange function uses LICENSE_SIGNING_PRIVATE_KEY for Ed25519 signing.")
        return 9

    print("[diag] OK: exchange signature is valid and compatible with app public key")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
