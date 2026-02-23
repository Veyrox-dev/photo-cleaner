#!/usr/bin/env bash
# Quick build script for PhotoCleaner executable

echo "🔨 Building PhotoCleaner v0.6.0..."

# Activate virtual environment
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

# Install PyInstaller if not present
pip install pyinstaller

# Build with spec file
if [ -f "PhotoCleaner.spec" ]; then
    echo "✅ Using existing PhotoCleaner.spec"
    pyinstaller PhotoCleaner.spec --clean --noconfirm
else
    echo "⚠️  No spec file found, creating basic build..."
    pyinstaller \
        --name=PhotoCleaner \
        --onefile \
        --windowed \
        --icon=assets/icon.ico \
        --add-data="assets:assets" \
        run_ui.py
fi

echo "✅ Build complete! Check dist/ folder"
