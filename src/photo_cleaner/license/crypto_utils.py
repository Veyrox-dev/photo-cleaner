"""Shared crypto helpers for license verification."""
from __future__ import annotations

import base64
import json
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    CRYPTOGRAPHY_AVAILABLE = True
except ImportError:
    CRYPTOGRAPHY_AVAILABLE = False
    Ed25519PublicKey = None  # type: ignore


# Public key (Ed25519) used to verify license signatures. Keep private key OUT of the app.
PUBLIC_KEY_PEM = """-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEARqPms2Pt+KRiBaVh+E2Q1Q7/gF5qNsN+i3eC3FhVuEo=
-----END PUBLIC KEY-----
"""

_PUBLIC_KEY: Optional[Any] = None


def _load_public_key() -> Optional[Any]:
    if not CRYPTOGRAPHY_AVAILABLE:
        return None
    global _PUBLIC_KEY
    if _PUBLIC_KEY is None:
        try:
            key_text = (PUBLIC_KEY_PEM or "").strip()
            # Common misconfiguration: Supabase anon/service JWT pasted instead
            # of an Ed25519 public key PEM.
            if key_text.count(".") == 2 and key_text.startswith("eyJ"):
                logger.error(
                    "Embedded key looks like a JWT token, not an Ed25519 public key PEM. "
                    "Replace PUBLIC_KEY_PEM with the real signing public key."
                )
                _PUBLIC_KEY = None
                return None

            _PUBLIC_KEY = serialization.load_pem_public_key(key_text.encode("utf-8"))
        except Exception as e:
            logger.error("Failed to load embedded public key: %s", e)
            _PUBLIC_KEY = None
    return _PUBLIC_KEY


def verify_ed25519_signature(payload: Dict[str, Any], signature_b64: str) -> bool:
    if not CRYPTOGRAPHY_AVAILABLE:
        logger.warning("cryptography not available - signature verification disabled")
        return False
    if not signature_b64:
        return False
    try:
        message = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        signature = base64.b64decode(signature_b64)
        public_key = _load_public_key()
        if public_key is None:
            return False
        public_key.verify(signature, message)
        return True
    except Exception as e:
        # Invalid signatures are expected in some flows (e.g. stale/partial payloads).
        # Keep this at debug level to avoid log spam in normal runtime.
        logger.debug("Signature verification failed (%s): %s", type(e).__name__, e)
        return False
