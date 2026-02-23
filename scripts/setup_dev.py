#!/usr/bin/env python3
"""
Quick setup script for PhotoCleaner development environment.
Installs dependencies, runs tests, and verifies installation.
"""
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(e.stdout)
        print(e.stderr)
        return False


def main():
    """Main setup routine."""
    print("\n" + "="*60)
    print("PhotoCleaner v0.5.5 - Development Setup")
    print("="*60)
    
    # Check Python version
    if sys.version_info < (3, 12):
        print("❌ Python 3.12+ required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}")
    
    # Install dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
        "Installing dependencies"
    ):
        print("\n⚠️  Dependency installation failed, but continuing...")
    
    # Install dev dependencies
    if not run_command(
        [sys.executable, "-m", "pip", "install", "pytest", "pytest-cov", "black", "ruff"],
        "Installing dev dependencies"
    ):
        print("\n⚠️  Dev dependency installation failed")
    
    # Run tests
    if not run_command(
        [sys.executable, "-m", "pytest", "tests/", "-v", "--tb=short"],
        "Running tests"
    ):
        print("\n⚠️  Some tests failed")
    
    # Verify imports
    print("\n" + "="*60)
    print("🔍 Verifying imports")
    print("="*60)
    
    try:
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        import photo_cleaner
        from photo_cleaner.license import get_license_manager, initialize_license_system
        from photo_cleaner.cache import ImageCacheManager
        print("✅ All imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
    
    # Summary
    print("\n" + "="*60)
    print("📋 Setup Complete!")
    print("="*60)
    print("\nNext steps:")
    print("1. Run UI: python run_ui.py")
    print("2. Run tests: pytest tests/ -v")
    print("3. Check coverage: pytest --cov=src --cov-report=html")
    print("4. Format code: black src/")
    print("5. Lint code: ruff check src/")
    print("\nHappy coding! 🚀")


if __name__ == "__main__":
    main()
