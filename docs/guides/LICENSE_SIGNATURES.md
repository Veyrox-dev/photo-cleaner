# License Signatures and Offline Cache (Ed25519)

## Overview
This document explains how the license signature flow works after the Ed25519 hardening.
It covers:
- Exchange flow (online)
- Offline snapshot cache
- Activation codes
- Failure modes

The goal is simple: only server-signed license payloads are accepted offline.

---

## Components

### Client (App)
- Verifies Ed25519 signatures before accepting a license payload.
- Stores a signed snapshot on disk for offline use.
- Rejects unsigned or invalid snapshots.

Key files:
- [src/photo_cleaner/license_client.py](../../src/photo_cleaner/license_client.py)
- [src/photo_cleaner/license/license_manager.py](../../src/photo_cleaner/license/license_manager.py)
- [src/photo_cleaner/license/crypto_utils.py](../../src/photo_cleaner/license/crypto_utils.py)

### Server (Supabase Edge Function)
- Signs the `license_data` payload with Ed25519.
- Returns `license_data` and `signature` to the app.

Key file:
- [supabase/functions/exchange-license-key/index.ts](../../supabase/functions/exchange-license-key/index.ts)

Required env var:
- `LICENSE_SIGNING_PRIVATE_KEY` (Base64-encoded 32-byte Ed25519 private key seed)

---

## Online Exchange Flow

1. The app sends `license_key` and `device_info` to the Edge Function.
2. The Edge Function:
   - Validates license status and expiry.
   - Registers the device.
   - Builds a `license_data` object.
   - Signs it with Ed25519.
3. The app receives:
   - `license_data`
   - `signature`
4. The app verifies the signature and, if valid, stores the snapshot to disk.

Signature payload:
- The signature is computed over the canonical JSON of `license_data`.
- Keys are sorted and JSON is normalized before signing.

---

## Offline Snapshot Cache

The app stores two files:
- `license_snapshot.json` (payload)
- `license_signature` (signature, Base64)

Offline usage rules:
- Snapshot is only accepted if the signature is valid.
- If signature is missing or invalid, the snapshot is ignored.
- Snapshot age must be within the grace period.

This prevents local tampering of cached license data.

---

## Activation Codes (Offline)

Activation codes are now Ed25519-signed as well.
The payload format is the same, but the `sig` field is an Ed25519 signature:

- `mid` (machine id)
- `type` (FREE/PRO in current docs; legacy ENTERPRISE values remain compatibility inputs)
- `exp` (YYYY-MM-DD)
- `nonce`
- `sig` (Ed25519 signature over the payload without `sig`)

Rules:
- The signature must be valid.
- The machine id must match the current device.
- The license type must be recognized.

If any check fails, activation is rejected.

---

## Failure Modes (Expected)

- Missing `cryptography` in the app: signatures are not verifiable and licenses are rejected.
- Missing `LICENSE_SIGNING_PRIVATE_KEY` on the server: exchange fails with 500.
- Tampered snapshot: rejected.
- Old snapshot (beyond grace period): rejected.

---

## Operational Notes

- The private signing key never ships in the app.
- Only the public key is embedded in the client.
- If you rotate the signing key, old snapshots become invalid.

---

## Quick Checklist

Server:
- `LICENSE_SIGNING_PRIVATE_KEY` set
- Edge Function returns `signature`

Client:
- Signature verified before caching
- Snapshot requires valid signature

---

## Glossary

- Ed25519: Fast public-key signature algorithm.
- Snapshot: Cached license payload stored for offline use.
- Signature: Base64 string verifying payload integrity.
