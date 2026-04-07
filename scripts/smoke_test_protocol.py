"""Helper script to guide the frozen-build smoke test protocol.

This does not launch the GUI. It validates expected paths and prints the
exact manual steps for the checklist.
"""

from __future__ import annotations

import argparse
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="PhotoCleaner smoke-test helper")
    parser.add_argument(
        "--exe",
        type=Path,
        default=Path("dist") / "PhotoCleaner" / "PhotoCleaner.exe",
        help="Path to PhotoCleaner.exe",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    exe_path = args.exe

    print("Smoke-Test Protocol (manual steps)")
    print("1) Build: .\\build.bat fast clean")
    print("2) Launch EXE on clean Windows VM")
    print("3) Import 20 images")
    print("4) Check logs for: [INIT], [DEPS], [WARMUP]")
    print("5) FREE-Lizenzfall pruefen: >250 Bilder blockiert mit Upgrade-Hinweis")
    print("6) PRO-Lizenzfall pruefen: gleiche Bibliothek ohne Limit verarbeitbar")
    print("7) Submit report with timestamps + any errors")
    print("")

    if exe_path.exists():
        print(f"EXE found: {exe_path}")
    else:
        print(f"EXE NOT found: {exe_path}")


if __name__ == "__main__":
    main()
