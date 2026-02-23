#!/usr/bin/env python3
"""Test Haar cascade resolver with the built EXE."""

import sys
import os

# Simulate the frozen build environment
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal")
sys.path.insert(0, r"c:\Users\chris\projects\photo-cleaner\src")

# Add _internal to simulate frozen build
if not hasattr(sys, '_MEIPASS'):
    sys._MEIPASS = r"c:\Users\chris\projects\photo-cleaner\dist\PhotoCleaner\_internal"

from photo_cleaner.pipeline.quality_analyzer import _resolve_haar_cascade_dir

print("Testing _resolve_haar_cascade_dir() in frozen-build context:")
print(f"  sys._MEIPASS = {sys._MEIPASS}")

result = _resolve_haar_cascade_dir()
print(f"  Result: {result}")

if result:
    import pathlib
    p = pathlib.Path(result)
    xml_files = list(p.glob('haarcascade_*.xml'))
    print(f"  Found {len(xml_files)} XML files in {result}")
    for xml in sorted(xml_files)[:3]:
        print(f"    - {xml.name}")
else:
    print("  WARNING: No Haar cascade directory found (fallback will be used)")
