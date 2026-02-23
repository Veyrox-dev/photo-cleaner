#!/usr/bin/env python3
"""Debug _resolve_haar_cascade_dir step by step"""

import sys
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal")
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\src")

if not hasattr(sys, '_MEIPASS'):
    sys._MEIPASS = r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal"

import cv2
from pathlib import Path

print("Step-by-step path resolution:")

meipass = Path(sys._MEIPASS)
print(f"1. sys._MEIPASS = {meipass}")

candidates = []

# Build candidates
try:
    candidates.append(meipass / "cv2" / "data" / "haarcascades")
    candidates.append(meipass / "cv2" / "data")
    print(f"2. Added {len(candidates)} candidates from sys._MEIPASS")
except Exception as e:
    print(f"2. ERROR adding candidates: {e}")

print("\n3. Checking candidates:")
for i, c in enumerate(candidates):
    exists = c.exists()
    print(f"   [{i}] {c.relative_to(Path.cwd()) if Path.cwd() in c.parents else c} -> exists={exists}")
    if exists:
        xmls = list(c.glob("haarcascade_*.xml"))
        print(f"       Found {len(xmls)} haarcascade_*.xml files")
        if xmls:
            return_val = c
            print(f"       -> Would return: {return_val}")
            break
