from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from photo_cleaner.config import AppConfig
from photo_cleaner.license_client import LicenseConfig as CloudLicenseConfig

logger = logging.getLogger(__name__)


def _parse_dotenv_line(line: str) -> tuple[str, str] | None:
    """Parse a KEY=VALUE line from a dotenv file."""
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in stripped:
        return None

    key, value = stripped.split("=", 1)
    key = key.strip()
    value = value.strip().strip('"').strip("'")
    if not key:
        return None
    return key, value


def _get_dotenv_value(key: str) -> str | None:
    """Read a variable from common .env locations if not present in process env."""
    project_root = Path(__file__).resolve().parents[3]
    exe_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else None

    candidates: list[Path] = [
        Path.cwd() / ".env",
        project_root / ".env",
        AppConfig.get_user_data_dir() / ".env",
        AppConfig.get_user_data_dir() / "cloud.env",
    ]

    if exe_dir is not None:
        candidates.extend([
            exe_dir / ".env",
            exe_dir / "_internal" / ".env",
        ])

    program_data = Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "PhotoCleaner"
    candidates.extend([
        program_data / ".env",
        program_data / "cloud.env",
    ])

    # Keep order stable while removing duplicates.
    unique_candidates = list(dict.fromkeys(candidates))

    for dotenv_path in unique_candidates:
        if not dotenv_path.exists():
            continue
        try:
            for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                parsed = _parse_dotenv_line(line)
                if parsed is None:
                    continue
                parsed_key, parsed_value = parsed
                if parsed_key == key and parsed_value:
                    return parsed_value
        except (OSError, UnicodeDecodeError):
            logger.debug("Could not read .env file: %s", dotenv_path, exc_info=True)
    return None


def _get_required_env_value(key: str) -> str | None:
    """Resolve required value from process environment first, then .env fallback."""
    value = os.getenv(key)
    if value:
        return value
    return _get_dotenv_value(key)


def get_cloud_license_config(*, missing_message: str, error_message: str) -> CloudLicenseConfig | None:
    """Create cloud license config from environment variables.

    Returns None if required variables are missing or invalid.
    """
    project_url = _get_required_env_value("SUPABASE_PROJECT_URL")
    anon_key = _get_required_env_value("SUPABASE_ANON_KEY")

    if not project_url or not anon_key:
        logger.warning(missing_message)
        return None

    try:
        return CloudLicenseConfig(project_url=project_url, anon_key=anon_key)
    except (ImportError, AttributeError, ValueError, OSError) as e:
        logger.warning(error_message, e, exc_info=True)
        return None
