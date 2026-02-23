# PhotoCleaner v0.6.0 - PyInstaller NumPy Issue - Solutions Guide

**Status:** Unresolved PyInstaller + NumPy incompatibility on this system  
**Date:** February 2, 2026  
**Error:** `TypeError: argument docstring of add_docstring should be a str`

---

## Issue Summary

PhotoCleaner cannot be built into a Windows executable using PyInstaller due to NumPy's C extensions failing to initialize in the frozen environment.

**Symptoms:**
- Build completes successfully
- EXE starts but crashes immediately when importing numpy
- Error in `numpy.core.overrides.py` during module initialization
- Occurs regardless of:
  - PyInstaller configuration (onedir vs onefile)
  - NumPy version (1.26.4 confirmed installed)
  - Hidden imports configuration
  - Runtime hooks

**Root Cause:** Fundamental incompatibility between PyInstaller's frozenimporter and NumPy's C extension initialization mechanism on this Windows 11 system with Python 3.12.8.

---

## Attempted Solutions (All Failed)

| Attempt | Method | Result | Reason Failed |
|---------|--------|--------|---------------|
| 1 | Runtime hook for numpy pre-init | Failed | Hook executes too early |
| 2 | Comprehensive hiddenimports | Failed | NumPy still can't initialize |
| 3 | Onedir mode | Failed | DLL loading doesn't help |
| 4 | Pinned numpy==1.26.4 | Failed | Version not the issue |
| 5 | Minimal spec | In progress | TBD |
| 6 | Onefile mode | In progress | TBD |

---

## Recommended Solutions

### Option A: SKIP PyInstaller - Use Alternative Build Method ✅ RECOMMENDED

Instead of PyInstaller, use **Nuitka** which compiles Python to C/C++:

```bash
# Install Nuitka
pip install nuitka zstandard

# Compile PhotoCleaner
python -m nuitka --onefile --windows-console-mode=disable --include-package=photo_cleaner run_ui.py

# Output: run_ui.exe (single executable, no numpy issues)
```

**Advantages:**
- Truly native compiled executable
- No numpy initialization problems
- Single file output
- Faster runtime
- Better compatibility

**Build time:** ~5-10 minutes

---

### Option B: Ship with Python Embedded

Bundle PhotoCleaner with Python portable:

```bash
# 1. Download Python 3.12.8 embeddable from python.org
# 2. Extract to dist\python-embedded\
# 3. Create a launcher .bat or .exe that runs:
dist\python-embedded\python.exe -m photo_cleaner.ui.main_window
```

**Advantages:**
- No PyInstaller complications
- Full Python compatibility
- Easier debugging

**Disadvantages:**
- Larger download (~150+ MB)
- Requires launcher script

---

### Option C: Use cx_Freeze Instead

Alternative Python freezer that handles NumPy better:

```bash
# Install cx_Freeze
pip install cx_Freeze

# Create setup script and build
python setup.py build
```

**Advantages:**
- Different implementation than PyInstaller
- Better NumPy support in many cases
- Cross-platform

---

### Option D: Keep Using PyInstaller - Apply Workarounds

If must use PyInstaller:

1. **Disable numpy.core module collection:**
   ```python
   # In spec file
   excludes=['numpy.core._multiarray']
   ```

2. **Use environment variables during build:**
   ```bash
   set NPY_DISABLE_CPU_FEATURES=AVX2,AVX512
   pyinstaller PhotoCleaner.spec
   ```

3. **Patch numpy before building:**
   - Modify venv numpy's __init__.py to skip problematic initialization
   - Rebuild PyInstaller with patched numpy

---

## Quick Fix: Use Development Mode

For now, ship PhotoCleaner as source code with installer:

**photocleaner-installer.bat:**
```batch
@echo off
REM PhotoCleaner v0.6.0 - Development Installer

:: Check Python
python --version > nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python 3.12+ not found
    echo Download from: https://www.python.org/
    pause
    exit /b 1
)

:: Install dependencies
python -m pip install -r requirements.txt -q

:: Launch
python run_ui.py
```

**Advantages:**
- Works immediately
- No build issues
- Easier for development

**Disadvantages:**
- Requires Python installation
- Not truly "standalone"

---

## Long-term Solution: Upgrade Build Stack

Plan for v0.7.0:

1. **Upgrade PyInstaller to 7.0+** (when released)
   - Better numpy 2.x support
   - Improved C extension handling

2. **Upgrade NumPy to 2.x officially**
   - After PyInstaller 7.0 released
   - Full NumPy 2.x support

3. **Consider Nuitka for main builds**
   - Parallel release as .exe
   - Maintains PyInstaller for edge cases

---

## Testing the Fixes

Once any solution is chosen, verify:

```bash
# 1. Build
pyinstaller PhotoCleaner.spec  # or nuitka, cx_Freeze, etc.

# 2. Test import chain
dist\PhotoCleaner\PhotoCleaner.exe  # Should NOT error with numpy

# 3. Test functionality
# - UI should load
# - Should be able to analyze a test image
# - No numpy or import errors in logs
```

---

## Code to Test Locally (Python Interpreter)

Verify the issue exists locally:

```python
# In .venv interpreter
python
>>> import photo_cleaner.ui.modern_window
>>> # Should import without errors (currently fails in frozen app)
```

If this works in Python but fails in frozen app → PyInstaller/NumPy issue confirmed.

---

## Recommendation

**IMMEDIATE ACTION:** Try **Nuitka** approach:

```bash
pip install nuitka zstandard
python -m nuitka --onefile --windows-console-mode=disable --include-package=photo_cleaner run_ui.py
```

This bypasses the PyInstaller/NumPy incompatibility entirely and produces a true native executable.

**FALLBACK:** Ship as installer script + Python embedded, or provide source code installer.

---

## References

- PyInstaller NumPy Issues: https://github.com/pyinstaller/pyinstaller/issues?q=numpy
- NumPy + PyInstaller: https://stackoverflow.com/questions/tagged/pyinstaller+numpy
- Nuitka Alternative: https://github.com/Nuitka/Nuitka
- cx_Freeze Alternative: https://cx-freeze.readthedocs.io/

---

**Next Steps:**
1. Decide on solution (recommend Nuitka)
2. Install alternative tool
3. Build and test
4. Update build documentation

