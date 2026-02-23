"""Offline, PC-bound license management for PhotoCleaner.

This module verifies signed, machine-bound licenses fully offline. A license is valid if:
- The Ed25519 signature matches the payload (public key bundled with the app)
- The machine_id inside the license matches the current device fingerprint
- The license is not expired
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from photo_cleaner.license.crypto_utils import CRYPTOGRAPHY_AVAILABLE, verify_ed25519_signature
from photo_cleaner.license_client import LicenseClient as CloudLicenseClient, LicenseConfig as CloudLicenseConfig

from photo_cleaner.config import AppConfig

logger = logging.getLogger(__name__)

if not CRYPTOGRAPHY_AVAILABLE:
    logger.warning("cryptography module not available - license verification will be disabled")
    logging.getLogger(__name__).setLevel(logging.ERROR)

LICENSE_FILENAME = "license.lic"
ACTIVATION_CODE_FILENAME = "activation_code.txt"
ACTIVATION_MARKER_FILENAME = "activation.ok"
LICENSE_REQUIRED_FIELDS = ("user", "license_type", "machine_id")
CLOUD_SNAPSHOT_FILENAME = "license_snapshot.json"
CLOUD_SIGNATURE_FILENAME = "license_signature"
CLOUD_DEFAULT_GRACE_DAYS = 7


class LicenseType(Enum):
    FREE = "FREE"
    PRO = "PRO"
    ENTERPRISE = "ENTERPRISE"


FEATURES_MAP: Dict[LicenseType, List[str]] = {
    LicenseType.FREE: [],
    LicenseType.PRO: [
        "batch_processing",
        "heic_support",
        "extended_cache",
        "advanced_quality_analysis",
        "bulk_delete",
        "export_formats",
    ],
    LicenseType.ENTERPRISE: [
        "batch_processing",
        "heic_support",
        "extended_cache",
        "advanced_quality_analysis",
        "bulk_delete",
        "export_formats",
        "api_access",
        "unlimited_images",
    ],
}


@dataclass
class LicenseInfo:
    license_type: LicenseType
    user: str
    machine_id: str
    expires_at: Optional[datetime]
    signature_valid: bool
    machine_match: bool
    valid: bool
    enabled_features: List[str]
    max_images: int
    raw: Dict
    path: Optional[Path]
    validation_reason: str


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="ignore")).hexdigest()


def _safe_run(cmd: List[str]) -> str:
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=2, text=True)
        return out.strip().splitlines()[0] if out else ""
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        return ""


def _get_cpu_id() -> str:
    if sys.platform == "win32":
        val = _safe_run(["wmic", "cpu", "get", "ProcessorId"])
        if val:
            parts = val.split()
            if len(parts) >= 2:
                return parts[1]
            return parts[0]
    return ""


def _get_baseboard_id() -> str:
    if sys.platform == "win32":
        val = _safe_run(["wmic", "baseboard", "get", "SerialNumber"])
        if val:
            parts = val.split()
            if len(parts) >= 2:
                return parts[1]
            return parts[0]
    return ""


def _get_machine_guid() -> str:
    if sys.platform != "win32":
        return ""
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Microsoft\\Cryptography") as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return str(guid)
    except (OSError, ImportError):
        return ""


def compute_machine_id() -> str:
    """Compute stable machine fingerprint using CPU ID, baseboard serial, and Machine GUID."""
    cpu_id = _get_cpu_id() or "cpu-unknown"
    board_id = _get_baseboard_id() or "board-unknown"
    machine_guid = _get_machine_guid() or "guid-unknown"
    fingerprint = f"{cpu_id}|{board_id}|{machine_guid}"
    return _sha256_hex(fingerprint)


class LicenseManager:
    """Offline license manager bound to a specific machine."""

    def __init__(self, app_dir: Path):
        self.app_dir = app_dir
        self.user_data_dir = AppConfig.get_user_data_dir()
        self.license_file = self.user_data_dir / LICENSE_FILENAME
        self.activation_marker = self.user_data_dir / ACTIVATION_MARKER_FILENAME
        self.machine_id = compute_machine_id()
        self.license_info: LicenseInfo = self._create_free_license("missing license")
        
        # DEBUG: Log license file locations for troubleshooting
        logger.info("=" * 60)
        logger.info("LICENSE SYSTEM INITIALIZATION")
        logger.info("=" * 60)
        logger.info(f"User Data Directory: {self.user_data_dir}")
        logger.info(f"License File: {self.license_file}")
        logger.info(f"  -> Exists: {self.license_file.exists()}")
        logger.info(f"Activation Marker: {self.activation_marker}")
        logger.info(f"  -> Exists: {self.activation_marker.exists()}")
        logger.info(f"Machine ID: {self.machine_id}")
        logger.info("=" * 60)
        
        # Auto-import license file from app directory if present
        try:
            self._auto_import_app_license()
        except (OSError, IOError, ValueError):
            logger.warning("Auto-import of app license failed; continuing", exc_info=True)
        # Consume activation code if present next to EXE
        try:
            self._consume_activation_code_if_present()
        except (OSError, IOError, ValueError):
            logger.warning("Activation code processing failed; continuing", exc_info=True)
        # If activation marker exists and is valid, prefer it over license file
        if self._load_cloud_snapshot():
            logger.info("Activated via cloud snapshot")
        elif self._load_activation_marker():
            logger.info("Activated via one-time code (marker present)")
        else:
            self._load_license()

    def refresh(self) -> None:
        """Reload license status from all sources (cloud snapshot, activation marker, license file)."""
        if self._load_cloud_snapshot():
            return
        if self._load_activation_marker():
            return
        self._load_license()

    def _get_cloud_usage_client(self) -> CloudLicenseClient | None:
        project_url = os.getenv("SUPABASE_PROJECT_URL")
        anon_key = os.getenv("SUPABASE_ANON_KEY")

        if not project_url or not anon_key:
            logger.info("Using embedded Supabase credentials for production deployment")
            project_url = "https://uxkbolrinptxyullfowo.supabase.co"
            anon_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4a2JvbHJpbnB0eHl1bGxmb3dvIiwicm9sZSI6ImFub24iLCJpYXQiOjE3Njk0NDIyNTksImV4cCI6MjA4NTAxODI1OX0.Q5oGEihWIrcEWykA08r0TYN-Xc7gxklvFUP5YOuCtOg"

        try:
            config = CloudLicenseConfig(project_url=project_url, anon_key=anon_key)
            return CloudLicenseClient(config)
        except (ValueError, OSError, ImportError) as e:
            logger.warning("Could not init cloud license client: %s", e, exc_info=True)
            return None

    def _load_cloud_snapshot(self) -> bool:
        """Load online license snapshot (if present) and map to local license info.

        This enables the Supabase-based license to override legacy offline licenses.
        """
        snapshot_paths = [
            Path.home() / ".photocleaner" / CLOUD_SNAPSHOT_FILENAME,
            self.user_data_dir / CLOUD_SNAPSHOT_FILENAME,
        ]

        snapshot_path = next((p for p in snapshot_paths if p.exists()), None)
        if not snapshot_path:
            return False

        signature_path = snapshot_path.parent / CLOUD_SIGNATURE_FILENAME
        if not signature_path.exists():
            logger.warning("Cloud snapshot signature missing: %s", signature_path)
            return False

        try:
            signature = signature_path.read_text(encoding="utf-8").strip()
        except Exception as e:
            logger.warning("Failed to read cloud snapshot signature (%s): %s", signature_path, e)
            return False

        try:
            snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.warning("Failed to read cloud snapshot (%s): %s", snapshot_path, e)
            return False

        fetched_at_str = snapshot.get("fetched_at")
        if fetched_at_str:
            try:
                fetched_at = datetime.fromisoformat(fetched_at_str)
                if fetched_at.tzinfo is None:
                    fetched_at = fetched_at.replace(tzinfo=timezone.utc)
                age = datetime.now(timezone.utc) - fetched_at
                if age > timedelta(days=CLOUD_DEFAULT_GRACE_DAYS):
                    logger.warning("Cloud snapshot too old (%s days)", age.days)
                    return False
            except Exception as e:
                logger.warning("Invalid fetched_at in snapshot: %s", e)

        license_data = snapshot.get("data") or {}
        if not verify_ed25519_signature(license_data, signature):
            logger.warning("Cloud snapshot signature invalid: %s", snapshot_path)
            return False
        plan = str(license_data.get("plan", ""))
        status = str(license_data.get("status", "active")).lower()
        expires_at_str = license_data.get("expires_at")

        expires_at = None
        if expires_at_str:
            try:
                expires_at = datetime.fromisoformat(str(expires_at_str))
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
            except (ValueError, TypeError):
                logger.debug(f"Could not parse expiration date: {expires_at_str}", exc_info=True)
                expires_at = None

        not_expired = True
        if expires_at:
            not_expired = expires_at > datetime.now(timezone.utc)

        plan_upper = plan.upper()
        if plan_upper == "ENTERPRISE":
            lic_type = LicenseType.ENTERPRISE
        elif plan_upper == "PRO":
            lic_type = LicenseType.PRO
        else:
            lic_type = LicenseType.FREE

        valid = status in ("active", "valid") and not_expired and lic_type != LicenseType.FREE
        enabled_features = FEATURES_MAP.get(lic_type, []) if valid else []
        max_images = 0 if valid and lic_type in (LicenseType.PRO, LicenseType.ENTERPRISE) else 1000

        self.license_info = LicenseInfo(
            license_type=lic_type,
            user=str(license_data.get("licensee") or license_data.get("assigned_to") or "Cloud License"),
            machine_id="cloud",
            expires_at=expires_at,
            signature_valid=True,
            machine_match=True,
            valid=valid,
            enabled_features=enabled_features,
            max_images=max_images,
            raw=snapshot,
            path=None,
            validation_reason="cloud" if valid else "cloud invalid",
        )

        if valid:
            logger.info("Cloud license loaded: %s (expires=%s)", lic_type.value, expires_at_str or "n/a")
        else:
            logger.warning("Cloud license snapshot present but invalid (plan=%s, status=%s)", plan, status)
        return valid

    def _auto_import_app_license(self) -> None:
        """If a license file exists next to the executable, import it automatically.
        
        This allows distributing a .lic file with the EXE for easy activation
        on tester machines without manual copying.
        """
        # Preferred filename
        candidate = self.app_dir / LICENSE_FILENAME
        if candidate.exists():
            shutil.copyfile(candidate, self.license_file)
            logger.info("Auto-imported license from app folder: %s", candidate)
            return

        # Fallback: any .lic file in app folder
        for lic in self.app_dir.glob("*.lic"):
            try:
                shutil.copyfile(lic, self.license_file)
                logger.info("Auto-imported license from app folder: %s", lic)
                return
            except (OSError, IOError, PermissionError):
                logger.debug(f"Could not copy license file {lic}", exc_info=True)
                continue

    def _extract_activation_signature(self, payload: Dict[str, Any]) -> tuple[Dict[str, str], str]:
        signature = str(payload.get("sig") or payload.get("signature") or "")
        signed_payload = {
            str(k): str(v)
            for k, v in payload.items()
            if k not in ("sig", "signature")
        }
        return signed_payload, signature

    def _consume_activation_code_if_present(self) -> None:
        """Consume activation code from app directory, write persistent activation marker.

        Format (single line JSON or key=value pairs):
            {"mid": "<machine_id>", "type": "PRO", "exp": "YYYY-MM-DD", "nonce": "<random>", "sig": "<b64>"}
        Signature: Ed25519 over the JSON payload without the signature field.
        """
        candidate_json = self.app_dir / "activation_code.json"
        candidate_txt = self.app_dir / ACTIVATION_CODE_FILENAME
        payload = None
        if candidate_json.exists():
            try:
                payload = json.loads(candidate_json.read_text(encoding="utf-8").strip())
            except (json.JSONDecodeError, ValueError):
                logger.debug("Could not parse activation JSON", exc_info=True)
                payload = None
        elif candidate_txt.exists():
            raw = candidate_txt.read_text(encoding="utf-8").strip()
            # Try JSON first
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                # Fallback: key=value;key=value
                try:
                    parts = dict(item.split("=", 1) for item in raw.split(";"))
                    payload = {k: v for k, v in parts.items()}
                except (ValueError, AttributeError):
                    logger.debug("Could not parse activation code format", exc_info=True)
                    payload = None

        if not payload:
            return

        signed_payload, sig = self._extract_activation_signature(payload)
        mid = str(signed_payload.get("mid", ""))
        lic_type = str(signed_payload.get("type", "")).upper()
        exp = str(signed_payload.get("exp", ""))
        nonce = str(signed_payload.get("nonce", ""))

        if not mid or not exp or not nonce or not sig:
            logger.warning("Activation code missing fields")
            return

        if lic_type not in LicenseType.__members__:
            logger.warning("Activation code has invalid license type: %s", lic_type)
            return

        # Validate signature and machine match
        if not verify_ed25519_signature(signed_payload, sig):
            logger.warning("Activation signature invalid")
            return
        if mid != self.machine_id:
            logger.warning("Activation code for different machine")
            return

        # Validate expiry
        try:
            expires_at = datetime.fromisoformat(exp)
            if datetime.utcnow() > expires_at:
                logger.warning("Activation code expired: %s", exp)
                return
        except (ValueError, TypeError):
            logger.warning("Activation expiry invalid: %s", exp)
            return

        # Persist activation marker and remove activation file(s)
        marker = {"mid": mid, "type": lic_type, "exp": exp, "nonce": nonce, "sig": sig}
        try:
            self.activation_marker.parent.mkdir(parents=True, exist_ok=True)
            self.activation_marker.write_text(json.dumps(marker), encoding="utf-8")
            logger.info("Activation marker written: %s", self.activation_marker)
            if candidate_json.exists():
                candidate_json.unlink(missing_ok=True)  # type: ignore[arg-type]
            if candidate_txt.exists():
                candidate_txt.unlink(missing_ok=True)  # type: ignore[arg-type]
        except Exception as e:
            logger.warning("Failed to persist activation marker: %s", e)

    def _load_activation_marker(self) -> bool:
        if not self.activation_marker.exists():
            return False
        try:
            data = json.loads(self.activation_marker.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, ValueError):
            logger.debug("Could not load activation marker", exc_info=True)
            return False

        signed_payload, sig = self._extract_activation_signature(data)
        mid = str(signed_payload.get("mid", ""))
        lic_type = str(signed_payload.get("type", "")).upper()
        exp = str(signed_payload.get("exp", ""))
        nonce = str(signed_payload.get("nonce", ""))

        # Validate signature and machine
        if not (mid and exp and nonce and sig):
            return False
        if lic_type not in LicenseType.__members__:
            return False
        if not verify_ed25519_signature(signed_payload, sig):
            return False
        if mid != self.machine_id:
            return False
        try:
            expires_at = datetime.fromisoformat(exp)
            if datetime.utcnow() > expires_at:
                return False
        except (ValueError, TypeError):
            logger.debug("Could not parse activation expiry", exc_info=True)
            return False

        # Set active license info (without signature verification)
        try:
            lic_enum = LicenseType(lic_type)
        except (ValueError, KeyError):
            return False

        enabled = FEATURES_MAP[lic_enum]
        self.license_info = LicenseInfo(
            license_type=lic_enum,
            user="Activated User",
            machine_id=self.machine_id,
            expires_at=expires_at,
            signature_valid=True,
            machine_match=True,
            valid=True,
            enabled_features=enabled,
            max_images=0 if lic_enum in (LicenseType.PRO, LicenseType.ENTERPRISE) else 1000,
            raw={"activation": True},
            path=self.activation_marker,
            validation_reason="ok",
        )
        return True

    # Public API: Activate using a pasted code (from UI)
    def activate_with_code(self, code: str) -> bool:
        """Activate license using a code string entered in the UI.

        Supports:
        - JSON payload same as activation_code.json
        - key=value;key=value format
        """
        code = (code or "").strip()
        if not code:
            return False

        # Try JSON
        payload: Dict[str, str] | None = None
        try:
            payload = json.loads(code)
        except json.JSONDecodeError:
            # Try key=value;key=value
            try:
                parts = dict(item.split("=", 1) for item in code.split(";"))
                payload = {k: v for k, v in parts.items()}
            except (ValueError, AttributeError):
                logger.debug("Could not parse activation code", exc_info=True)
                payload = None

        if payload is not None:
            signed_payload, sig = self._extract_activation_signature(payload)
            mid = str(signed_payload.get("mid", ""))
            lic_type = str(signed_payload.get("type", "")).upper()
            exp = str(signed_payload.get("exp", ""))
            nonce = str(signed_payload.get("nonce", ""))

            # Validate
            if not (mid and exp and nonce and sig):
                return False
            if lic_type not in LicenseType.__members__:
                return False
            if not verify_ed25519_signature(signed_payload, sig):
                return False
            if mid != self.machine_id:
                return False
            try:
                expires_at = datetime.fromisoformat(exp)
                if datetime.utcnow() > expires_at:
                    return False
            except (ValueError, TypeError):
                logger.debug("Could not parse expiration date in activate_with_code", exc_info=True)
                return False

            lic_enum = LicenseType(lic_type)
            enabled = FEATURES_MAP[lic_enum]
            marker = {
                "mid": mid,
                "type": lic_type,
                "exp": exp,
                "nonce": nonce,
                "sig": sig,
            }
            try:
                self.activation_marker.parent.mkdir(parents=True, exist_ok=True)
                self.activation_marker.write_text(json.dumps(marker), encoding="utf-8")
                self.license_info = LicenseInfo(
                    license_type=lic_enum,
                    user=str(payload.get("user", "Activated User")),
                    machine_id=self.machine_id,
                    expires_at=expires_at,
                    signature_valid=True,
                    machine_match=True,
                    valid=True,
                    enabled_features=enabled,
                    max_images=0 if lic_enum in (LicenseType.PRO, LicenseType.ENTERPRISE) else 1000,
                    raw={"activation": True},
                    path=self.activation_marker,
                    validation_reason="ok",
                )
                return True
            except (OSError, IOError, ValueError):
                logger.error("Could not save activation marker", exc_info=True)
                return False

        return False

    def _create_free_license(self, reason: str) -> LicenseInfo:
        return LicenseInfo(
            license_type=LicenseType.FREE,
            user="Free User",
            machine_id=self.machine_id,
            expires_at=None,
            signature_valid=False,
            machine_match=True,
            valid=False,
            enabled_features=FEATURES_MAP[LicenseType.FREE],
            max_images=1000,
            raw={},
            path=self.license_file if self.license_file else None,
            validation_reason=reason,
        )

    def _verify_signature(self, payload: Dict, signature_b64: str) -> bool:
        return verify_ed25519_signature(payload, signature_b64)

    def _load_license(self) -> None:
        if not self.license_file.exists():
            logger.info("No license file found, falling back to FREE tier (%s)", self.license_file)
            self.license_info = self._create_free_license("no license file")
            return

        try:
            with open(self.license_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            logger.warning("Failed to read license file: %s", e)
            self.license_info = self._create_free_license("read failure")
            return

        missing = [fld for fld in LICENSE_REQUIRED_FIELDS if fld not in data]
        if missing:
            logger.warning("License missing required fields: %s", ", ".join(missing))
            self.license_info = self._create_free_license("missing fields")
            return

        signature = data.get("signature", "")
        payload = {k: v for k, v in data.items() if k != "signature"}

        signature_valid = self._verify_signature(payload, signature)
        license_machine_id = str(payload.get("machine_id", ""))
        machine_match = license_machine_id == self.machine_id
        expires_raw = payload.get("expires")
        expires_at = None
        not_expired = True
        if expires_raw:
            try:
                expires_at = datetime.fromisoformat(expires_raw)
                not_expired = datetime.utcnow() <= expires_at
            except (ValueError, TypeError):
                logger.debug(f"Could not parse license expiry: {expires_raw}", exc_info=True)
                not_expired = False

        try:
            lic_type = LicenseType(str(payload.get("license_type", "FREE")).upper())
        except ValueError:
            lic_type = LicenseType.FREE

        valid = bool(signature_valid and machine_match and not_expired)
        enabled_features = FEATURES_MAP[lic_type] if valid else FEATURES_MAP[LicenseType.FREE]
        max_images = 0 if (lic_type in (LicenseType.PRO, LicenseType.ENTERPRISE) and valid) else 1000

        reason = "ok" if valid else self._build_reason(signature_valid, machine_match, not_expired)

        self.license_info = LicenseInfo(
            license_type=lic_type if valid else LicenseType.FREE if not signature_valid else lic_type,
            user=str(payload.get("user", "Unknown User")),
            machine_id=license_machine_id,
            expires_at=expires_at,
            signature_valid=signature_valid,
            machine_match=machine_match,
            valid=valid,
            enabled_features=enabled_features,
            max_images=max_images,
            raw=data,
            path=self.license_file,
            validation_reason=reason,
        )

        logger.info("License loaded from %s", self.license_file)
        logger.info("Signature valid: %s", signature_valid)
        if not machine_match:
            logger.warning("Machine mismatch: license=%s current=%s", license_machine_id, self.machine_id)
        if expires_at and not not_expired:
            logger.warning("License expired at %s", expires_at.isoformat())
        logger.info("License level set to %s (valid=%s)", self.license_info.license_type.value, valid)

    def _build_reason(self, signature_valid: bool, machine_match: bool, not_expired: bool) -> str:
        if not signature_valid:
            return "signature invalid"
        if not machine_match:
            return "machine mismatch"
        if not not_expired:
            return "expired"
        return "invalid"

    def import_license_file(self, source_path: Path) -> bool:
        try:
            source_path = Path(source_path)
            if not source_path.exists():
                raise FileNotFoundError(source_path)
            self.license_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source_path, self.license_file)
            logger.info("License file imported from %s", source_path)
            self._load_license()
            return True
        except Exception as e:
            logger.error("Failed to import license file: %s", e)
            return False

    def remove_license(self) -> bool:
        try:
            if self.license_file.exists():
                self.license_file.unlink()
                logger.info("License removed (%s)", self.license_file)
            # Remove cloud snapshot cache if present
            snapshot_paths = [
                Path.home() / ".photocleaner" / CLOUD_SNAPSHOT_FILENAME,
                self.user_data_dir / CLOUD_SNAPSHOT_FILENAME,
            ]
            for snapshot_path in snapshot_paths:
                try:
                    if snapshot_path.exists():
                        snapshot_path.unlink()
                        logger.info("Cloud snapshot removed (%s)", snapshot_path)
                except (OSError, PermissionError):
                    logger.debug(f"Could not remove snapshot cache {snapshot_path}", exc_info=True)
            self.license_info = self._create_free_license("removed")
            return True
        except Exception as e:
            logger.error("Failed to remove license: %s", e)
            return False

    def is_feature_enabled(self, feature: str) -> bool:
        info = self.license_info
        return bool(info.valid and feature in info.enabled_features)

    def can_process_images(self, count: int) -> bool:
        info = self.license_info
        if not info.valid:
            return count <= info.max_images
        if info.max_images == 0:
            return True
        return count <= info.max_images

    def check_and_consume_free_images(self, count: int) -> tuple[bool, str]:
        if count <= 0:
            return True, ""

        info = self.license_info
        if info.valid and info.max_images == 0:
            return True, ""

        client = self._get_cloud_usage_client()
        if not client:
            return False, "Free-Lizenz erfordert eine Online-Pruefung. Bitte Internet aktivieren oder Lizenz upgraden."

        ok, remaining, error = client.consume_free_images(self.machine_id, count)
        if ok:
            if remaining is not None:
                return True, f"Free-Kontingent verbleibend: {remaining} Bilder"
            return True, ""
        if isinstance(remaining, int):
            return False, f"Free-Limit erreicht. Verbleibend: {remaining} Bilder."
        return False, error or "Free-Limit erreicht. Bitte Upgrade auf PRO/ENTERPRISE."

    def get_license_info(self) -> LicenseInfo:
        return self.license_info

    def get_license_status(self) -> Dict[str, object]:
        info = self.license_info
        return {
            "license_type": info.license_type.value,
            "user": info.user,
            "license_file": str(info.path) if info.path else None,
            "expires_at": info.expires_at.isoformat() if info.expires_at else None,
            "machine_id_current": self.machine_id,
            "machine_id_license": info.machine_id,
            "signature_valid": info.signature_valid,
            "machine_match": info.machine_match,
            "valid": info.valid,
            "enabled_features": info.enabled_features,
            "max_images": info.max_images,
            "reason": info.validation_reason,
        }


class FeatureFlagsManager:
    def __init__(self, license_manager: LicenseManager):
        self.license_manager = license_manager

    def _valid(self) -> bool:
        return self.license_manager.get_license_info().valid

    def can_batch_process(self) -> bool:
        return self.license_manager.is_feature_enabled("batch_processing")

    def can_process_heic(self) -> bool:
        return self.license_manager.is_feature_enabled("heic_support")

    def can_use_extended_cache(self) -> bool:
        return self.license_manager.is_feature_enabled("extended_cache")

    def can_use_advanced_quality(self) -> bool:
        return self.license_manager.is_feature_enabled("advanced_quality_analysis")

    def can_bulk_delete(self) -> bool:
        return self.license_manager.is_feature_enabled("bulk_delete")

    def can_export_formats(self) -> bool:
        return self.license_manager.is_feature_enabled("export_formats")

    def has_api_access(self) -> bool:
        return self.license_manager.is_feature_enabled("api_access")

    def has_unlimited_images(self) -> bool:
        info = self.license_manager.get_license_info()
        return info.valid and info.max_images == 0

    def get_status_text(self) -> str:
        info = self.license_manager.get_license_info()
        if not info.valid:
            return f"⚠ Invalid license ({info.validation_reason})"
        if info.license_type == LicenseType.FREE:
            return "📦 FREE (Basic)"
        if info.license_type == LicenseType.PRO:
            return "⭐ PRO"
        if info.license_type == LicenseType.ENTERPRISE:
            return "🏢 ENTERPRISE"
        return "Unknown"


_license_manager: Optional[LicenseManager] = None
_feature_flags: Optional[FeatureFlagsManager] = None


def initialize_license_system(app_dir: Path) -> tuple[LicenseManager, FeatureFlagsManager]:
    global _license_manager, _feature_flags
    _license_manager = LicenseManager(app_dir)
    _feature_flags = FeatureFlagsManager(_license_manager)
    status = _license_manager.get_license_status()
    logger.info("License system initialized: %s (valid=%s)", status.get("license_type"), status.get("valid"))
    return _license_manager, _feature_flags


def get_license_manager() -> LicenseManager:
    if _license_manager is None:
        raise RuntimeError("License system not initialized. Call initialize_license_system() first")
    return _license_manager


def get_feature_flags() -> FeatureFlagsManager:
    if _feature_flags is None:
        raise RuntimeError("License system not initialized. Call initialize_license_system() first")
    return _feature_flags

