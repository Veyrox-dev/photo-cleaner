#!/usr/bin/env python3
"""Debug Haar cascade resolver path detection."""

import sys
import os
from pathlib import Path

# Simulate the frozen build environment
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal")
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\src")

# Add _internal to simulate frozen build
if not hasattr(sys, '_MEIPASS'):
    sys._MEIPASS = r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal"

from photo_cleaner.config import AppConfig

print("Debug Haar Cascade Path Resolution:")
print(f"  sys._MEIPASS = {sys._MEIPASS}")

app_dir = AppConfig.get_app_dir()
print(f"  AppConfig.get_app_dir() = {app_dir}")

candidates = []
try:
    meipass = Path(getattr(sys, "_MEIPASS", ""))
    if meipass:
        candidates.append(meipass / "cv2" / "data" / "haarcascades")
        candidates.append(meipass / "cv2" / "data")
        candidates.append(meipass / "_internal" / "cv2" / "data" / "haarcascades")
        candidates.append(meipass / "_internal" / "cv2" / "data")
except Exception as e:
    print(f"  ERROR: {e}")

candidates.extend([
    app_dir / "_internal" / "cv2" / "data" / "haarcascades",
    app_dir / "_internal" / "cv2" / "data",
    app_dir / "cv2" / "data" / "haarcascades",
    app_dir / "cv2" / "data",
])

print("\nCandidate paths:")
for i, cand in enumerate(candidates):
    exists = cand.exists()
    xmls = len(list(cand.glob("haarcascade_*.xml"))) if exists else 0
    print(f"  [{i}] {cand.relative_to(Path.cwd()) if Path.cwd() in cand.parents else cand}")
    print(f"      Exists: {exists}, XMLs found: {xmls}")
