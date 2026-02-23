#!/usr/bin/env python3
"""Check if Haar Cascade files exist in cv2 package."""

from pathlib import Path
from PyInstaller.utils.hooks import get_package_paths

try:
    _, cv2_pkg_dir = get_package_paths('cv2')
    cv2_data_path = Path(cv2_pkg_dir) / 'data' / 'haarcascades'
    
    print(f"cv2 package dir: {cv2_pkg_dir}")
    print(f"Haar cascades path: {cv2_data_path}")
    print(f"Path exists: {cv2_data_path.exists()}")
    
    if cv2_data_path.exists():
        xml_files = list(cv2_data_path.glob('*.xml'))
        print(f"XML files found: {len(xml_files)}")
        for xml in xml_files[:5]:  # Show first 5
            print(f"  - {xml.name}")
    else:
        # Check alternate locations
        parent = Path(cv2_pkg_dir)
        print(f"\nSearching alternate locations in {parent}:")
        for p in parent.rglob('haarcascade*.xml'):
            print(f"  Found: {p.relative_to(parent)}")
            
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
