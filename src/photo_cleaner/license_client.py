"""
Supabase-basierter Lizenz-Client für PhotoCleaner v0.5.5.

Features:
- Lizenzschlüssel-Austausch gegen Device-Token
- Geräteregistrierung mit Limit-Enforcement (maxDevices=3)
- Grace-Period: 7 Tage Offline-Nutzung mit gecachtem Snapshot
- Device-ID: Stabile Installation-UUID (Hostname + Salt)
- Snapshot-Signatur (Ed25519) gegen Manipulation
"""

import hashlib
import hmac
import json
import logging
import os
import socket
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    import requests
except ImportError:
    requests = None

logger = logging.getLogger(__name__)

# Import verify_ed25519_signature - handle potential circular imports
def _import_verify_ed25519_signature():
    try:
        from photo_cleaner.license.crypto_utils import verify_ed25519_signature as _verify
        return _verify
    except ImportError:
        logger.warning("Could not import verify_ed25519_signature")
        def _fallback(data, signature):
            return False
        return _fallback

verify_ed25519_signature = _import_verify_ed25519_signature()


class LicenseConfig:
    """Konfiguration für Supabase-Zugriff (ohne Secrets im Code)."""
    
    def __init__(
        self,
        project_url: str,
        anon_key: str,
        service_role_key: Optional[str] = None,
        grace_period_days: int = 7,
        max_devices: int = 3,
    ):
        """
        Args:
            project_url: Supabase Project URL (z.B. https://xxxxx.supabase.co)
            anon_key: Anon/Public API Key
            service_role_key: Optional für Server-Operationen
            grace_period_days: Offline-Grace-Periode (Standard: 7 Tage)
            max_devices: Max. Geräte pro Lizenz (Standard: 3)
        """
        self.project_url = project_url.rstrip("/")
        self.anon_key = anon_key
        self.service_role_key = service_role_key
        self.grace_period_days = grace_period_days
        self.max_devices = max_devices
        self.rest_url = f"{self.project_url}/rest/v1"
        self.functions_url = f"{self.project_url}/functions/v1"


class DeviceInfo:
    """Geräteinformation für Registrierung."""
    
    @staticmethod
    def get_device_id(salt_file: Optional[Path] = None) -> str:
        """
        Generiere stabile Device-ID basierend auf Hostname + optionalem Salt.
        
        Falls salt_file existiert: lade gespeicherten Salt und erzeuge ID daraus.
        Sonst: generiere neuen Salt, speichere ihn, erzeuge ID.
        
        Args:
            salt_file: Pfad zur Datei, in der der Salt gespeichert wird (z.B. ~/.photocleaner/device.salt)
        
        Returns:
            Hex-String der Device-ID
        """
        hostname = socket.gethostname()
        
        if salt_file and salt_file.exists():
            try:
                with open(salt_file, "r") as f:
                    salt = f.read().strip()
            except Exception as e:
                logger.warning(f"Could not read salt file: {e}, generating new salt")
                salt = str(uuid.uuid4())
                if salt_file:
                    try:
                        salt_file.parent.mkdir(parents=True, exist_ok=True)
                        with open(salt_file, "w") as f:
                            f.write(salt)
                    except Exception as e2:
                        logger.warning(f"Could not save salt file: {e2}")
        else:
            salt = str(uuid.uuid4())
            if salt_file:
                try:
                    salt_file.parent.mkdir(parents=True, exist_ok=True)
                    with open(salt_file, "w") as f:
                        f.write(salt)
                except Exception as e:
                    logger.warning(f"Could not save salt file: {e}")
        
        # Kombiniere Hostname + Salt für stabile, nicht-HW-sensitive ID
        combined = f"{hostname}:{salt}"
        device_id = hashlib.sha256(combined.encode()).hexdigest()[:16]
        return device_id
    
    @staticmethod
    def get_device_name() -> str:
        """Einfacher Device-Name: Hostname."""
        return socket.gethostname()
    
    @staticmethod
    def get_device_os() -> str:
        """Erkenne Betriebssystem."""
        import platform
        system = platform.system()
        if system == "Windows":
            return "Windows"
        elif system == "Darwin":
            return "macOS"
        elif system == "Linux":
            return "Linux"
        else:
            return "Unknown"


class LicenseClient:
    """Client für Supabase-basiertes Lizenzsystem."""
    
    def __init__(self, config: LicenseConfig, cache_dir: Optional[Path] = None):
        """
        Args:
            config: LicenseConfig-Instanz
            cache_dir: Verzeichnis für Snapshot-Cache (Standard: ~/.photocleaner)
        """
        self.config = config
        self.cache_dir = cache_dir or (Path.home() / ".photocleaner")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.salt_file = self.cache_dir / "device.salt"
        self.snapshot_file = self.cache_dir / "license_snapshot.json"
        self.signature_file = self.cache_dir / "license_signature"
        
        if requests is None:
            logger.warning("requests library not available; license exchange will fail")
    
    def exchange_license_key(
        self,
        license_key: str,
        device_info: Optional[Dict[str, str]] = None,
    ) -> Tuple[bool, Optional[str], str]:
        """
        Tausche Lizenzschlüssel gegen Device-Token.
        Ruft Edge Function 'exchange-license-key' auf.
        
        Args:
            license_key: Lizenzschlüssel vom Nutzer
            device_info: Optional {name, os}; wird auto-generiert, falls None
        
        Returns:
            (success, license_id, error_message)
        """
        if not requests:
            return False, None, "requests library not available"
        
        if not device_info:
            device_info = {
                "device_id": DeviceInfo.get_device_id(self.salt_file),
                "machine_id": DeviceInfo.get_device_id(self.salt_file),
                "hostname": DeviceInfo.get_device_name(),
                "platform": DeviceInfo.get_device_os(),
            }
        
        url = f"{self.config.functions_url}/exchange-license-key"
        headers = {
            "Authorization": f"Bearer {self.config.anon_key}",
            "apikey": self.config.anon_key,
            "Content-Type": "application/json",
        }
        payload = {
            "license_key": license_key,
            "device_info": device_info,
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=15)
            if resp.status_code >= 400:
                details = _safe_response_details(resp)
                logger.error("License exchange failed (%s): %s", resp.status_code, details)
                return False, None, details or f"HTTP {resp.status_code}"

            data = resp.json()
            if data.get("ok"):
                license_id = data.get("license_id")
                # Cache Snapshot lokal
                self._cache_snapshot(license_id, data.get("license_data"), data.get("signature"))
                return True, license_id, ""

            return False, None, data.get("error", "Unknown error")

        except requests.RequestException as e:
            logger.error(f"License exchange failed: {e}")
            return False, None, f"Network error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error in exchange_license_key: {e}")
            return False, None, f"Error: {str(e)}"
    
    def fetch_license(self, license_id: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Hole aktuelles Lizenzdokument aus Supabase.
        Bei Offline: Nutze gecachten Snapshot falls Grace-Period aktiv.
        
        Args:
            license_id: Lizenz-ID
        
        Returns:
            (success, license_doc, error_message)
        """
        if not requests:
            logger.warning("requests not available, trying offline cache")
            return self._load_cached_snapshot(license_id)
        
        url = f"{self.config.rest_url}/licenses?license_id=eq.{license_id}"
        headers = {
            "Authorization": f"Bearer {self.config.anon_key}",
            "apikey": self.config.anon_key,
            "Content-Type": "application/json",
        }
        
        try:
            resp = _request_with_retry(lambda: requests.get(url, headers=headers, timeout=10))
            if resp.status_code >= 400:
                details = _safe_response_details(resp)
                logger.warning("License fetch failed (%s): %s", resp.status_code, details)
                return self._load_cached_snapshot(license_id)

            data = resp.json()
            
            if data and len(data) > 0:
                license_doc = data[0]
                # Aktualisiere Cache bei erfolgreichem Online-Fetch
                self._cache_snapshot(license_id, license_doc, license_doc.get("signature"))
                return True, license_doc, ""
            else:
                # Fallback zu Cache bei No Results
                logger.debug(f"License {license_id} not found online, trying cache")
                return self._load_cached_snapshot(license_id)
        
        except Exception as e:
            # Catch both real and mocked RequestException, plus other errors
            logger.warning(f"Offline or network error fetching license: {e}, trying cache")
            return self._load_cached_snapshot(license_id)

    def consume_free_images(self, device_id: str, amount: int) -> Tuple[bool, Optional[int], str]:
        """
        Consume free image quota for a device via Supabase RPC.

        Returns:
            (allowed, remaining, error_message)
        """
        if not requests:
            return False, None, "requests library not available"

        url = f"{self.config.rest_url}/rpc/consume_free_images"
        headers = {
            "Authorization": f"Bearer {self.config.anon_key}",
            "apikey": self.config.anon_key,
            "Content-Type": "application/json",
        }
        payload = {
            "p_device_id": device_id,
            "p_amount": int(amount),
        }

        try:
            resp = _request_with_retry(lambda: requests.post(url, json=payload, headers=headers, timeout=10))
            if resp.status_code >= 400:
                details = _safe_response_details(resp)
                logger.error("Free usage RPC failed (%s): %s", resp.status_code, details)
                return False, None, details or f"HTTP {resp.status_code}"

            data = resp.json()
            row = data[0] if isinstance(data, list) and data else data
            allowed = bool(row.get("allowed", False)) if isinstance(row, dict) else False
            remaining = row.get("remaining") if isinstance(row, dict) else None
            used_total = row.get("used_total") if isinstance(row, dict) else None
            if allowed:
                return True, remaining, ""
            if remaining is None and used_total is not None:
                remaining = max(0, 1000 - int(used_total))
            return False, remaining, "Free-Limit erreicht. Bitte Upgrade auf PRO/ENTERPRISE."
        except requests.HTTPError as e:
            logger.error("Free usage RPC failed: %s", e)
            return False, None, f"Server error: {e.response.status_code}"
        except Exception as e:
            logger.error("Free usage RPC error: %s", e)
            return False, None, f"Error: {str(e)}"

    def enforce_limits(
        self,
        license_doc: Dict[str, Any],
        device_id: str,
    ) -> Tuple[bool, str]:
        """
        Prüfe Lizenz-Limits (Ablauf, Status, Geräte-Limit).
        
        Args:
            license_doc: Lizenzdokument (z.B. von fetch_license)
            device_id: Geräte-ID zur Überprüfung
        
        Returns:
            (is_valid, error_message)
        """
        if not license_doc:
            return False, "Lizenzdokument leer"
        
        # Status prüfen
        status = license_doc.get("status", "").lower()
        if status == "suspended":
            return False, "Lizenz gesperrt (suspended)"
        if status == "expired":
            return False, "Lizenz abgelaufen"
        if status not in ("active", ""):
            return False, f"Unerwarteter Status: {status}"
        
        # Ablauf prüfen
        expires_at_str = license_doc.get("expires_at")
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(expires_at_str.replace("Z", "+00:00"))
                if datetime.now(timezone.utc) > expires_at:
                    return False, f"Lizenz abgelaufen: {expires_at_str}"
            except Exception as e:
                logger.warning(f"Could not parse expires_at: {e}")
        
        # Gerätelimit prüfen (falls Geräteliste vorhanden)
        registered_devices = license_doc.get("registered_devices")
        if isinstance(registered_devices, list) and registered_devices:
            if device_id not in registered_devices:
                return False, "Geraet nicht registriert"
        
        return True, ""

    def register_device(
        self,
        license_id: str,
        device_name: Optional[str] = None,
    ) -> Tuple[bool, str]:
        """
        Registriere aktuelles Gerät bei einer Lizenz.
        
        Args:
            license_id: Lizenz-ID
            device_name: Name für dieses Gerät (Standard: Hostname)
        
        Returns:
            (success, error_message)
        """
        if not requests:
            return False, "requests library not available"
        
        device_id = DeviceInfo.get_device_id(self.salt_file)
        device_name = device_name or socket.gethostname()
        
        url = f"{self.config.rest_url}/rpc/register_device"
        headers = {
            "Authorization": f"Bearer {self.config.anon_key}",
            "apikey": self.config.anon_key,
            "Content-Type": "application/json",
        }
        payload = {
            "p_license_id": license_id,
            "p_device_id": device_id,
            "p_device_name": device_name,
            "p_device_type": DeviceInfo.get_device_type(),
        }
        
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            return True, ""
        except requests.HTTPError as e:
            if "Device limit exceeded" in str(e):
                return False, "Gerätlimit (3) erreicht. Entferne ein altes Gerät."
            return False, f"HTTP error: {e.response.status_code}"
        except Exception as e:
            logger.error(f"Error registering device: {e}")
            return False, str(e)
    
    def _cache_snapshot(
        self,
        license_id: str,
        license_data: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> None:
        """Speichere Lizenz-Snapshot lokal mit Signatur."""
        if not signature:
            logger.warning("Snapshot signature missing; skipping cache write")
            return
        if not verify_ed25519_signature(license_data, signature):
            logger.warning("Snapshot signature invalid; skipping cache write")
            return
        try:
            snapshot = {
                "license_id": license_id,
                "data": license_data,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.snapshot_file, "w") as f:
                json.dump(snapshot, f)
            
            if signature:
                with open(self.signature_file, "w") as f:
                    f.write(signature)
            
            logger.debug(f"Cached license snapshot for {license_id}")
        except Exception as e:
            logger.warning(f"Could not cache snapshot: {e}")
    
    def _load_cached_snapshot(
        self,
        license_id: str,
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """Lade gecachten Snapshot und prüfe Grace-Period."""
        try:
            if not self.snapshot_file.exists():
                return False, None, "Kein Cache vorhanden und offline"

            with open(self.snapshot_file, "r") as f:
                snapshot = json.load(f)

            signature = ""
            if self.signature_file.exists():
                signature = self.signature_file.read_text(encoding="utf-8").strip()
            else:
                # Backward compatibility: older snapshots may carry signature inline.
                embedded_signature = snapshot.get("signature")
                if isinstance(embedded_signature, str):
                    signature = embedded_signature.strip()
                    if signature:
                        try:
                            self.signature_file.write_text(signature, encoding="utf-8")
                        except Exception as e:
                            logger.debug(f"Could not persist migrated snapshot signature: {e}")

            if not signature:
                logger.warning("Cached snapshot has no signature; ignoring offline cache")
                return False, None, "Kein gueltiger Offline-Cache vorhanden"
            
            cached_license_id = snapshot.get("license_id")
            if cached_license_id != license_id:
                return False, None, f"Cache für andere Lizenz ({cached_license_id})"
            
            age = timedelta(0)
            fetched_at_str = snapshot.get("fetched_at")
            if fetched_at_str:
                fetched_at = datetime.fromisoformat(fetched_at_str)
                now = datetime.now(timezone.utc)
                age = now - fetched_at
                grace_period = timedelta(days=self.config.grace_period_days)
                
                if age > grace_period:
                    return False, None, f"Cache älter als {self.config.grace_period_days} Tage (offline zu lange)"
            
            license_data = snapshot.get("data")
            if not verify_ed25519_signature(license_data or {}, signature):
                return False, None, "Snapshot-Signatur ungueltig"
            logger.info(f"Using cached license (age: {age.days}d {age.seconds//3600}h)")
            return True, license_data, f"[Offline] Cache aktiv (Grace: {self.config.grace_period_days}d)"
        
        except Exception as e:
            logger.error(f"Error loading cached snapshot: {e}")
            return False, None, f"Cache-Fehler: {str(e)}"


def _safe_response_details(resp) -> str:
    try:
        data = resp.json()
        if isinstance(data, dict) and data.get("error"):
            return str(data.get("error"))
        return str(data)[:500]
    except Exception:
        try:
            text = resp.text
            return text[:500] if text else ""
        except Exception:
            return ""


def _request_with_retry(request_fn, retries: int = 3, backoff_seconds: float = 1.5):
    last_exc = None
    for attempt in range(retries):
        try:
            resp = request_fn()
            if resp.status_code in (429, 503, 504):
                raise requests.RequestException(f"HTTP {resp.status_code}")
            return resp
        except requests.RequestException as exc:
            last_exc = exc
            if attempt < retries - 1:
                delay = backoff_seconds * (attempt + 1)
                logger.warning("Request failed (%s); retrying in %.1fs", exc, delay)
                time.sleep(delay)
                continue
            raise
    raise last_exc if last_exc else requests.RequestException("Request failed")


class LicenseManager:
    """High-level Manager für Lizenz-Workflow."""
    
    def __init__(self, config: LicenseConfig, cache_dir: Optional[Path] = None):
        self.client = LicenseClient(config, cache_dir)
        self.current_license_id: Optional[str] = None
        self.current_license_data: Optional[Dict[str, Any]] = None
    
    def activate_with_key(self, license_key: str) -> Tuple[bool, str]:
        """
        Aktiviere Lizenz mit Schlüssel.
        
        Returns:
            (success, message)
        """
        success, license_id, error = self.client.exchange_license_key(license_key)
        
        if not success:
            return False, f"Aktivierung fehlgeschlagen: {error}"
        
        # Fetch Lizenz-Daten
        success, license_data, error = self.client.fetch_license(license_id)
        if not success:
            return False, f"Konnte Lizenzdaten nicht laden: {error}"
        
        # Enforce Limits
        device_id = DeviceInfo.get_device_id(self.client.salt_file)
        is_valid, enforce_error = self.client.enforce_limits(license_data, device_id)
        if not is_valid:
            return False, f"Lizenz-Check fehlgeschlagen: {enforce_error}"
        
        self.current_license_id = license_id
        self.current_license_data = license_data
        
        plan = license_data.get("plan", "unknown")
        expires_at = license_data.get("expires_at", "unknown")
        return True, f"Lizenz aktiviert: Plan={plan}, Ablauf={expires_at}"
    
    def get_status(self) -> str:
        """Gebe aktuellen Lizenz-Status als String."""
        if not self.current_license_id:
            return "Keine Lizenz aktiviert"
        
        plan = self.current_license_data.get("plan", "?")
        status = self.current_license_data.get("status", "?")
        expires_at = self.current_license_data.get("expires_at", "?")
        
        return f"Plan: {plan} | Status: {status} | Expires: {expires_at}"
