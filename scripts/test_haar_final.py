#!/usr/bin/env python3
"""Test if imports work with frozen-build paths """

import sys
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal")
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\src")

# Set MEIPASS BEFORE imports to trigger frozen-build mode
if not hasattr(sys, '_MEIPASS'):
    sys._MEIPASS = r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal"

# Now test
from pathlib import Path
print("Testing cascade resolution:")
print(f"  sys._MEIPASS = {sys._MEIPASS}")
print(f"  Checking {sys._MEIPASS}/cv2/data...")

meipass = Path(sys._MEIPASS)
target = meipass / "cv2" / "data"
if target.exists():
    xmls = list(target.glob("haarcascade_*.xml"))
    print(f"  EXISTS! Found {len(xmls)} cascades")
    if xmls:
        print(f"  Example: {xmls[0].name}")
else:
    print(f"  NOT FOUND")

# Now import and test resolver
print("\nTesting _resolve_haar_cascade_dir():")
from photo_cleaner.pipeline.quality_analyzer import _resolve_haar_cascade_dir

result = _resolve_haar_cascade_dir()
print(f"  Result: {result}")
if result:
    print(f"  SUCCESS: Found cascades at {result}")
