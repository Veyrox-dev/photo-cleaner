# -*- mode: python ; coding: utf-8 -*-
"""
PhotoCleaner v0.8.2 - PyInstaller Spec

CRITICAL FIX for numpy docstring error:
- NO runtime hooks (they cause numpy initialization to fail in frozen app)
- Using --onedir mode (no temp extraction, better for antivirus compatibility)
- Explicit comprehensive hiddenimports list
- All binaries and datas properly collected

ONEDIR mode avoids:
- Antivirus blocking temp extraction
- TEMP directory permission issues
- Decompression errors (PySide6\QtGui.pyd)
"""

import os
import sys
from pathlib import Path
from PyInstaller.utils.hooks import (
    collect_all,
    collect_submodules,
    collect_data_files,
    collect_dynamic_libs,
    get_package_paths,
)

sys.setrecursionlimit(5000)

# Faster dev builds: set PHOTOCLEANER_FAST=1 to skip archive and optimizations
FAST_BUILD = os.environ.get("PHOTOCLEANER_FAST", "0") == "1"

block_cipher = None

tf_binaries = collect_dynamic_libs('tensorflow') + collect_dynamic_libs('tensorflow.python')
tf_extra_binaries = []
try:
    _, tf_pkg_dir = get_package_paths('tensorflow')
    tf_root = Path(tf_pkg_dir)
    for name in ("tensorflow_framework.2.dll", "tensorflow_cc.2.dll"):
        dll_path = tf_root / name
        if dll_path.exists():
            # Place TF core DLLs next to _pywrap_tensorflow_internal.pyd
            tf_extra_binaries.append((str(dll_path), "tensorflow/python"))
except Exception:
    tf_extra_binaries = []

scipy_datas, scipy_binaries, scipy_hiddenimports = collect_all('scipy')
mediapipe_datas, mediapipe_binaries, mediapipe_hiddenimports = collect_all('mediapipe')

# Explicitly collect Haar Cascade XMLs from cv2 (collect_data_files() can miss these)
haar_xml_files = []
try:
    _, cv2_pkg_dir = get_package_paths('cv2')
    cv2_data_path = Path(cv2_pkg_dir) / 'data' / 'haarcascades'
    if cv2_data_path.exists():
        haar_xml_files = [(str(xml_file), 'cv2/data/haarcascades') 
                          for xml_file in cv2_data_path.glob('*.xml')]
        print(f"[BUILD] Found {len(haar_xml_files)} Haar Cascade XML files in {cv2_data_path}")
    else:
        print(f"[BUILD] WARNING: Haar Cascade directory not found: {cv2_data_path}")
except Exception as e:
    print(f"[BUILD] WARNING: Failed to collect Haar Cascades: {e}")
    haar_xml_files = []

# Collect photo_cleaner package data from src/
try:
    photo_cleaner_datas = [(str(p), str(p.parent.relative_to('src'))) 
                            for p in Path('src').rglob('photo_cleaner/**/*') 
                            if p.is_file() and not p.suffix == '.pyc']
except Exception:
    photo_cleaner_datas = []

a = Analysis(
    ['run_ui.py'],
    pathex=['.', 'src'],
    binaries=tf_binaries + tf_extra_binaries + scipy_binaries + mediapipe_binaries,
    datas=[
        # Assets (Icons, Splash Screen)
        ('assets/*.ico', 'assets'),
        ('assets/*.png', 'assets'),
        ('assets/third_party/vc_runtime/*.dll', '.'),
    ] + photo_cleaner_datas + collect_data_files('mtcnn', includes=['data/*.npy']) + haar_xml_files + scipy_datas + mediapipe_datas,
    hiddenimports=[
        # === NUMPY (MUST BE FIRST - Critical for proper initialization) ===
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'numpy.core.multiarray',
        'numpy.core.umath',
        'numpy.core.overrides',
        'numpy.core._methods',
        'numpy.core._internal',
        'numpy.lib',
        'numpy.lib.stride_tricks',
        'numpy.lib.format',
        'numpy.polynomial',
        'numpy.random',
        'numpy.linalg',
        'numpy.fft',
        'numpy.ma',
        
        # === IMAGE PROCESSING ===
        'cv2',
        'PIL',
        'PIL.Image',
        'PIL._imaging',
        'imagehash',
        'pillow_heif',
        
        # === ML/DEEP LEARNING ===
        'tensorflow',
        'tensorflow.python',
        'mediapipe',
        
        # === UI FRAMEWORK ===
        'PySide6',
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtNetwork',
        'shiboken6',
        
        # === CRYPTO ===
        'cryptography',
        'cryptography.hazmat',
        'cryptography.hazmat.primitives',
        
        # === PHOTOCLEANER MODULES ===
        'photo_cleaner',
        'photo_cleaner.ui',
        'photo_cleaner.ui.splash_screen',
        'photo_cleaner.ui.dark_theme',
        'photo_cleaner.ui.modern_window',
        'photo_cleaner.core',
        'photo_cleaner.services',
        'photo_cleaner.license',
        'photo_cleaner.cache',
        'photo_cleaner.pipeline',
        'photo_cleaner.db',
        'photo_cleaner.ml',
        
        # === UTILITIES ===
        'send2trash',
        'click',
        'pathlib',
        'sqlite3',
        
        # === SETUPTOOLS/PKG_RESOURCES (optional - only if needed) ===
        # Note: jaraco modules are vendored inside pkg_resources, not standalone
        'setuptools',
        'pkg_resources',
    ] + collect_submodules('photo_cleaner') + scipy_hiddenimports + mediapipe_hiddenimports,
    hookspath=['build_hooks'],
    hooksconfig={},
    runtime_hooks=[],  # REMOVED - runtime hooks cause numpy import failures
    excludes=[
        # Exclude unnecessary modules for faster startup
        'tkinter',
        'matplotlib',
        'pandas',
        'IPython',
        'notebook',
        'jupyter',
        'pytz',
        'pytest',
        'testing',
        # Exclude Keras torch backend (we use TensorFlow only)
        'torch',
        'torchvision',
        'keras.src.backend.torch',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=FAST_BUILD,
    optimize=0 if FAST_BUILD else 2,  # Optimize bytecode
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Using --onedir mode (directory with exe + libraries)
# This avoids temp extraction issues that trigger antivirus and decompression errors
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,  # Keep binaries separate (onedir mode)
    name='PhotoCleaner',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='PhotoCleaner',
)

# Output: dist/PhotoCleaner/ directory with PhotoCleaner.exe inside
