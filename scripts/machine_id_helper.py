"""
Machine ID Helper for PhotoCleaner licensing.

Run this on the target Windows PC to print the stable machine fingerprint
used by the offline license system. Use the printed `machine_id` when
creating a license file via `create_license.py`.

Usage:
    python scripts/machine_id_helper.py
"""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure src/ is on sys.path for imports
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from photo_cleaner.license.license_manager import compute_machine_id, _get_cpu_id, _get_baseboard_id  # type: ignore


def main() -> None:
    print("PhotoCleaner Machine ID Helper")
    print("-------------------------------")
    print(f"Platform: {sys.platform}")

    machine_id = compute_machine_id()
    print(f"Machine ID (SHA256): {machine_id}")

    # Extra diagnostics (Windows only)
    if sys.platform == "win32":
        try:
            cpu = _get_cpu_id()
            base = _get_baseboard_id()
            print(f"CPU ID: {cpu or 'unknown'}")
            print(f"Baseboard Serial: {base or 'unknown'}")
        except (OSError, subprocess.CalledProcessError):
            pass  # Diagnostic tools not available on this system


    print("\nUse this Machine ID when generating the .lic file.")


if __name__ == "__main__":
    main()
