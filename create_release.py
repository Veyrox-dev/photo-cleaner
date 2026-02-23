#!/usr/bin/env python3
"""
PhotoCleaner Release Packager

Creates a distributable ZIP file from the built application.
Usage: python create_release.py
"""
import shutil
import sys
from datetime import datetime
from pathlib import Path


def get_version():
    """Extract version from run_ui.py."""
    run_ui = Path(__file__).parent / "run_ui.py"
    if not run_ui.exists():
        return "0.8.3"
    
    with open(run_ui, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("VERSION = "):
                # Extract version string: VERSION = "0.6.0"
                version = line.split("=")[1].strip().strip('"\'')
                return version
    return "0.8.2"


def main():
    """Create release ZIP from dist/PhotoCleaner/."""
    print("=" * 50)
    print("PhotoCleaner Release Packager")
    print("=" * 50)
    print()
    
    # Paths
    root = Path(__file__).parent
    dist_dir = root / "dist" / "PhotoCleaner"
    
    # Check if build exists
    if not dist_dir.exists():
        print("❌ ERROR: dist/PhotoCleaner/ not found!")
        print("   Please run build.bat first.")
        sys.exit(1)
    
    # Get version
    version = get_version()
    print(f"📦 Version: {version}")
    
    # Create ZIP filename with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_name = f"PhotoCleaner_v{version}_{timestamp}"
    zip_path = root / "releases" / zip_name
    
    # Create releases directory
    releases_dir = root / "releases"
    releases_dir.mkdir(exist_ok=True)
    
    # Create ZIP
    print(f"📂 Source: {dist_dir}")
    print(f"💾 Creating: {zip_name}.zip")
    print()
    print("⏳ Compressing... (this may take a minute)")
    
    try:
        # shutil.make_archive creates .zip automatically
        shutil.make_archive(
            str(zip_path),
            'zip',
            dist_dir.parent,  # Base directory
            'PhotoCleaner'     # Archive from this folder
        )
        
        zip_file = Path(f"{zip_path}.zip")
        size_mb = zip_file.stat().st_size / (1024 * 1024)
        
        print()
        print("=" * 50)
        print("✅ SUCCESS!")
        print("=" * 50)
        print(f"📦 File: {zip_file.name}")
        print(f"💾 Size: {size_mb:.1f} MB")
        print(f"📁 Location: releases/")
        print()
        print("Ready for distribution! 🚀")
        
    except Exception as e:
        print()
        print("=" * 50)
        print("❌ ERROR during ZIP creation:")
        print("=" * 50)
        print(f"   {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
