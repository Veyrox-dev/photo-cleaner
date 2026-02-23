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
MCowBQYDK2VwAyEAYv2JpJ60sH1+4icx+XAu1KOJV8RKPnDcKvsPpEHrLpQ=
-----END PUBLIC KEY-----
"""

_PUBLIC_KEY: Optional[Any] = None


def _load_public_key() -> Optional[Any]:
    if not CRYPTOGRAPHY_AVAILABLE:
        return None
    global _PUBLIC_KEY
    if _PUBLIC_KEY is None:
        try:
            _PUBLIC_KEY = serialization.load_pem_public_key(PUBLIC_KEY_PEM.encode("utf-8"))
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
        logger.warning("Signature verification failed: %s", e)
        return False
