#!/usr/bin/env python3
r"""Photo Cleaner - Moderne deutsche UI.

Startet direkt die neue moderne Oberfläche (German UI). Optional können Input- und
Output-Ordner per Argument gesetzt werden, um den Ordnerdialog zu überspringen.

Usage:
    .venv\Scripts\python.exe run_ui.py
    .venv\Scripts\python.exe run_ui.py --input C:\Photos --output C:\Sorted

Environment Variables:
    - PHOTOCLEANER_MODE=DEBUG  (DEBUG oder RELEASE, Standard: RELEASE)
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import time
from pathlib import Path

# ============================================================================
# CRITICAL: Set TensorFlow environment variables BEFORE any imports
# This prevents DLL initialization errors when Qt is loaded later
# ============================================================================
if "TF_CPP_MIN_LOG_LEVEL" not in os.environ:
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "2"  # Reduce TF logging noise
if "TF_ENABLE_ONEDNN_OPTS" not in os.environ:
    os.environ["TF_ENABLE_ONEDNN_OPTS"] = "1"  # Enable CPU optimizations

# Force TensorFlow CPU-only mode in frozen builds (avoid GPU check hang)
if getattr(sys, 'frozen', False):
    os.environ.setdefault("CUDA_VISIBLE_DEVICES", "-1")  # Disable GPU unless explicitly overridden
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"  # Suppress all TF logs in frozen build

# In frozen GUI builds, stdout/stderr can be None; make them safe early.
if sys.stdout is None:
    sys.stdout = io.StringIO()
if sys.stderr is None:
    sys.stderr = io.StringIO()

# Setup path
sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from photo_cleaner.config import AppConfig, AppMode

# Project version constant for UI/logging
VERSION = "0.8.5"
from photo_cleaner import get_logger
from photo_cleaner.i18n import t, load_language_from_settings

# Lazy imports - erst nach Splash Screen
_modern_ui_imported = False
_DLL_DIR_HANDLES = []


def parse_args():
    p = argparse.ArgumentParser(description="Photo Cleaner - Moderne deutsche UI")
    p.add_argument("--input", type=Path, help="Input-Ordner (überspringt Dialog)")
    p.add_argument("--output", type=Path, help="Output-Ordner (überspringt Dialog)")
    p.add_argument("--db", type=Path, help="Optionaler DB-Pfad (Standard: photo_cleaner.db oder Output-Ordner)")
    return p.parse_args()


def _sanitize_mtcnn_error(error: str | None) -> str | None:
    if not error:
        return error
    if "_pywrap_tensorflow_internal" in error or "dll load failed" in error.lower():
        return (
            "TensorFlow Runtime konnte nicht geladen werden (DLL-Fehler). "
            "Stelle sicher, dass die Microsoft VC++ Runtime (2015-2022) installiert ist "
            "und die mitgelieferten DLLs im Installationsordner liegen."
        )
    if "traceback" in error.lower():
        lines = [line for line in error.splitlines() if line.strip()]
        return lines[-1] if lines else error
    return error


def _prepare_windows_dll_search_paths(app_dir: Path, logger) -> None:
    if sys.platform != "win32":
        return
    exe_dir = Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False):
        base_dir = exe_dir
    else:
        base_dir = Path(getattr(sys, "_MEIPASS", app_dir))
    internal_dir = base_dir / "_internal"
    paths = [
        exe_dir,
        exe_dir / "_internal",
        base_dir,
        internal_dir,
        base_dir / "assets" / "third_party" / "vc_runtime",
        base_dir / "tensorflow",
        base_dir / "tensorflow" / "python",
        base_dir / "tensorflow" / "python" / "lib",
        internal_dir / "tensorflow",
        internal_dir / "tensorflow" / "python",
        internal_dir / "tensorflow" / "python" / "lib",
        internal_dir / "numpy.libs",
    ]
    for path in paths:
        if not path.exists():
            continue
        try:
            handle = os.add_dll_directory(str(path))
        except (FileNotFoundError, NotImplementedError, OSError) as exc:
            logger.debug(f"Could not add DLL directory {path}: {exc}")
        else:
            _DLL_DIR_HANDLES.append(handle)
            os.environ["PATH"] = f"{path}{os.pathsep}" + os.environ.get("PATH", "")
            logger.debug(f"DLL directory added: {path}")

    # Diagnostic: attempt to load critical TensorFlow DLLs explicitly
    try:
        import ctypes

        tf_dir_candidates = [
            exe_dir / "_internal" / "tensorflow",
            internal_dir / "tensorflow",
        ]
        tf_core_dlls = set()
        for tf_dir in tf_dir_candidates:
            tf_core_dlls.update(_find_tf_core_dlls(tf_dir))
        for tf_dir in tf_dir_candidates:
            for dll_name in sorted(tf_core_dlls):
                dll_path = tf_dir / dll_name
                if dll_path.exists():
                    try:
                        ctypes.WinDLL(str(dll_path), use_last_error=True)
                        logger.debug(f"Loaded DLL: {dll_path}")
                    except OSError as exc:
                        last_error = ctypes.get_last_error()
                        win_error = ctypes.WinError(last_error) if last_error else None
                        logger.error(f"Failed to load {dll_path}: {exc}")
                        logger.error(f"{dll_name} last_error: {last_error} ({win_error})")

        pywrap_candidates = [
            exe_dir / "_internal" / "tensorflow" / "python" / "_pywrap_tensorflow_internal.pyd",
            internal_dir / "tensorflow" / "python" / "_pywrap_tensorflow_internal.pyd",
        ]
        for pywrap_path in pywrap_candidates:
            if not pywrap_path.exists():
                continue
            try:
                ctypes.WinDLL(str(pywrap_path), use_last_error=True)
                logger.debug(f"Loaded DLL: {pywrap_path}")
            except OSError as exc:
                last_error = ctypes.get_last_error()
                win_error = ctypes.WinError(last_error) if last_error else None
                logger.error(f"Failed to load {pywrap_path}: {exc}")
                logger.error(f"_pywrap_tensorflow_internal last_error: {last_error} ({win_error})")
    except Exception as exc:
        logger.debug(f"TensorFlow DLL probe failed: {exc}")


def _log_tf_diagnostics(app_dir: Path, logger) -> None:
    if sys.platform != "win32":
        return
    import ctypes
    import importlib.util

    exe_dir = Path(sys.executable).resolve().parent
    if getattr(sys, "frozen", False):
        base_dir = exe_dir
    else:
        base_dir = Path(getattr(sys, "_MEIPASS", app_dir))
    internal_dir = base_dir / "_internal"
    tf_root = None
    if (internal_dir / "tensorflow").exists():
        tf_root = internal_dir / "tensorflow"
    else:
        spec = importlib.util.find_spec("tensorflow")
        if spec and spec.submodule_search_locations:
            tf_root = Path(spec.submodule_search_locations[0])
    tf_core_dlls = _find_tf_core_dlls(tf_root) if tf_root else []
    candidate_dirs = [
        exe_dir,
        exe_dir / "_internal",
        base_dir,
        internal_dir,
        base_dir / "assets" / "third_party" / "vc_runtime",
        internal_dir / "numpy.libs",
        internal_dir / "tensorflow",
        internal_dir / "tensorflow" / "python",
        internal_dir / "tensorflow" / "python" / "lib",
    ]
    logger.debug("=== TensorFlow diagnostic dump (win32) ===")
    logger.debug(f"exe_dir: {exe_dir}")
    logger.debug(f"base_dir: {base_dir}")
    logger.debug(f"internal_dir: {internal_dir}")
    logger.debug(f"dll_dir_handles: {len(_DLL_DIR_HANDLES)}")

    logger.debug(f"sys.executable: {sys.executable}")
    logger.debug(f"sys.path entries: {len(sys.path)}")
    for entry in sys.path[:10]:
        logger.debug(f"sys.path[0..9]: {entry}")

    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    logger.debug(f"PATH entries: {len(path_entries)}")
    for entry in path_entries[:10]:
        logger.debug(f"PATH[0..9]: {entry}")

    for path in candidate_dirs:
        if path.exists():
            logger.debug(f"diag dir exists: {path}")
        else:
            logger.debug(f"diag dir missing: {path}")

    # Log presence of key files
    key_files = [
        internal_dir / "python311.dll",
        internal_dir / "VCRUNTIME140.dll",
        internal_dir / "VCRUNTIME140_1.dll",
        internal_dir / "MSVCP140.dll",
        internal_dir / "MSVCP140_1.dll",
        internal_dir / "MSVCP140_2.dll",
        internal_dir / "concrt140.dll",
        internal_dir / "vcomp140.dll",
        internal_dir / "tensorflow" / "python" / "_pywrap_tensorflow_internal.pyd",
        internal_dir / "numpy.libs" / "libopenblas64__v0.3.23-293-gc2f4bdbb-gcc_10_3_0-2bde3a66a51006b2b53eb373ff767a3f.dll",
    ]
    if tf_core_dlls:
        key_files.extend(internal_dir / "tensorflow" / name for name in tf_core_dlls)
    for path in key_files:
        logger.debug(f"key file {'OK' if path.exists() else 'MISSING'}: {path}")

    # Optional: dump PE imports for _pywrap_tensorflow_internal.pyd
    try:
        import pefile
    except Exception as exc:
        logger.debug(f"pefile not available for diagnostics: {exc}")
    else:
        pe_targets = [
            internal_dir / "tensorflow" / "python" / "_pywrap_tensorflow_internal.pyd",
        ]
        if tf_core_dlls:
            pe_targets.extend(internal_dir / "tensorflow" / name for name in tf_core_dlls)
        for target in pe_targets:
            if not target.exists():
                continue
            try:
                pe = pefile.PE(str(target))
                imports = sorted({entry.dll.decode("utf-8") for entry in pe.DIRECTORY_ENTRY_IMPORT})
                logger.debug(f"PE imports for {target.name} ({len(imports)}): {', '.join(imports)}")

                delay_imports = []
                for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
                    for imp in entry.imports:
                        if imp.dll:
                            delay_imports.append(imp.dll.decode("utf-8"))
                if delay_imports:
                    logger.debug(
                        f"PE delay imports for {target.name} ({len(delay_imports)}): {', '.join(sorted(set(delay_imports)))}"
                    )

                unresolved = []
                for dll in imports:
                    found = False
                    for search_dir in candidate_dirs:
                        if (search_dir / dll).exists():
                            found = True
                            break
                    if not found:
                        unresolved.append(dll)
                if unresolved:
                    logger.debug(f"PE unresolved imports for {target.name}: {', '.join(unresolved)}")
                else:
                    logger.debug(f"PE unresolved imports for {target.name}: none")
            except Exception as exc:
                logger.debug(f"PE import scan failed for {target.name}: {exc}")

    # Try to load key DLLs in order and log WinError details
    load_targets = [
        internal_dir / "tensorflow" / "python" / "_pywrap_tensorflow_internal.pyd",
    ]
    if tf_core_dlls:
        load_targets[:0] = [internal_dir / "tensorflow" / name for name in tf_core_dlls]
    for target in load_targets:
        if not target.exists():
            logger.debug(f"ctypes load skipped (missing): {target}")
            continue
        try:
            ctypes.WinDLL(str(target), use_last_error=True)
            logger.debug(f"ctypes load OK: {target}")
        except OSError as exc:
            last_error = ctypes.get_last_error()
            win_error = ctypes.WinError(last_error) if last_error else None
            logger.error(f"ctypes load failed: {target}: {exc}")
            logger.error(f"ctypes last_error: {last_error} ({win_error})")

    logger.debug("=== End TensorFlow diagnostic dump ===")


def _log_tf_pre_import(logger) -> None:
    logger.debug("=== TensorFlow pre-import state ===")
    logger.debug(f"sys.executable: {sys.executable}")
    logger.debug(f"dll_dir_handles: {len(_DLL_DIR_HANDLES)}")
    logger.debug(f"TF_CPP_MIN_LOG_LEVEL: {os.environ.get('TF_CPP_MIN_LOG_LEVEL')}")
    logger.debug(f"TF_ENABLE_ONEDNN_OPTS: {os.environ.get('TF_ENABLE_ONEDNN_OPTS')}")
    path_entries = os.environ.get("PATH", "").split(os.pathsep)
    logger.debug(f"PATH entries: {len(path_entries)}")
    for entry in path_entries[:10]:
        logger.debug(f"PATH[0..9]: {entry}")
    logger.debug("=== End TensorFlow pre-import state ===")


def _configure_keras_logging(logger) -> None:
    # Prevent Keras progbar from writing to None in frozen windowed apps.
    if sys.stdout is None:
        sys.stdout = io.StringIO()
    if sys.stderr is None:
        sys.stderr = io.StringIO()
    try:
        import keras

        try:
            keras.utils.disable_interactive_logging()
        except Exception:
            pass
        try:
            from keras.utils import io_utils

            if io_utils.sys.stdout is None:
                io_utils.sys.stdout = sys.stdout
            if io_utils.sys.stderr is None:
                io_utils.sys.stderr = sys.stderr
        except Exception:
            pass
        try:
            import tensorflow as tf

            tf.keras.utils.disable_interactive_logging()
        except Exception:
            pass
    except Exception as exc:
        logger.debug(f"Keras logging configuration skipped: {exc}")


def _find_tf_core_dlls(tf_root: Path | None) -> list[str]:
    if not tf_root or not tf_root.exists():
        return []
    names = []
    for pattern in ("tensorflow_framework*.dll", "tensorflow_cc*.dll"):
        for path in tf_root.glob(pattern):
            if path.is_file():
                names.append(path.name)
    return sorted(set(names))


def _get_mtcnn_weights_path() -> Path | None:
    try:
        from importlib import resources
    except Exception:
        return None

    try:
        weights = resources.files("mtcnn").joinpath("data", "mtcnn_weights.npy")
    except Exception:
        return None

    try:
        with resources.as_file(weights) as real_path:
            return Path(real_path)
    except Exception:
        return None


def main():
    args = parse_args()

    # Initialize app config BEFORE other imports use it
    app_dir = Path(__file__).resolve().parent
    AppConfig.set_app_dir(app_dir)
    _default_mode = "RELEASE" if getattr(sys, "frozen", False) else "DEBUG"
    mode_str = os.environ.get("PHOTOCLEANER_MODE", _default_mode).upper()
    mode = AppMode.DEBUG if mode_str == "DEBUG" else AppMode.RELEASE
    AppConfig.set_mode(mode)

    logger = get_logger(__name__)
    logger.info(f"=== PhotoCleaner {VERSION} gestartet im {mode.value} Modus ===")

    cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES")
    if cuda_visible == "-1":
        logger.info("TensorFlow CPU-only mode enabled (CUDA_VISIBLE_DEVICES=-1)")
    elif cuda_visible is not None:
        logger.info("CUDA_VISIBLE_DEVICES=%s", cuda_visible)

    startup_t0 = time.perf_counter()

    # ====================================================================
    # PHASE 0: Argumente und Pfade sehr frueh aufloesen
    # ====================================================================
    input_path = args.input.resolve() if args.input else None
    output_path = args.output.resolve() if args.output else None
    db_path = args.db.resolve() if args.db else None

    if not db_path and output_path:
        db_path = output_path / "photo_cleaner_session.db"
    if not db_path:
        db_path = AppConfig.get_db_dir() / "photo_cleaner.db"

    # ====================================================================
    # PHASE 1: SOFORT QApplication starten (fuer fruehen Splash)
    # ====================================================================
    from PySide6.QtWidgets import QApplication, QMessageBox
    app = QApplication(sys.argv)
    
    # Windows Taskbar Integration - KRITISCH für richtiges Icon
    if sys.platform == "win32":
        try:
            import ctypes
            # AppUserModelID für Windows Taskbar-Gruppierung
            myappid = f'photocleaner.app.{VERSION}'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            logger.info(f"Windows AppUserModelID gesetzt: {myappid}")
        except Exception as e:
            logger.warning(f"Konnte AppUserModelID nicht setzen: {e}")
    
    # ====================================================================
    # PHASE 2: Dark Theme SOFORT anwenden (vor allen Fenstern)
    # ====================================================================
    from photo_cleaner.ui.dark_theme import apply_dark_theme
    apply_dark_theme(app)
    logger.info("Dark Theme angewendet")

    # Set global window icon for taskbar/task switching
    try:
        from PySide6.QtGui import QIcon
        icon_ico = app_dir / "assets" / "icon.ico"
        icon_png = app_dir / "assets" / "icon.png"
        if icon_ico.exists():
            app.setWindowIcon(QIcon(str(icon_ico)))
            logger.info(f"Global icon gesetzt: {icon_ico}")
        elif icon_png.exists():
            app.setWindowIcon(QIcon(str(icon_png)))
            logger.info(f"Global icon gesetzt: {icon_png}")
        else:
            logger.warning("Kein Icon gefunden in assets/")
    except Exception as e:
        logger.warning(f"Konnte globales Icon nicht setzen: {e}")
    
    # ====================================================================
    # PHASE 2.5: Load language preference before splash screen
    # ====================================================================
    try:
        settings_path = AppConfig.get_user_data_dir() / "settings.json"
        load_language_from_settings(settings_path)
        logger.info("Language preference loaded")
    except Exception as e:
        logger.warning(f"Could not load language preference: {e}")
    
    # ====================================================================
    # PHASE 3: Splash Screen so frueh wie moeglich anzeigen
    # ====================================================================
    from photo_cleaner.ui.splash_screen import create_splash_screen
    splash = create_splash_screen(app_dir)
    splash.show_progress(t("splash_loading_app"), 10)
    logger.info("Splash shown after %.2fs", time.perf_counter() - startup_t0)

    # ====================================================================
    # PHASE 3.2: DB beim Erststart vorbereiten (Directory + Datei + Schema)
    # ====================================================================
    splash.show_progress("Preparing database", 15)
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        from photo_cleaner.db.schema import Database

        preflight_db = Database(db_path)
        preflight_conn = preflight_db.connect()
        preflight_conn.close()
        logger.info("Database ready: %s", db_path)
    except Exception as e:
        logger.error("Database initialization failed for %s: %s", db_path, e, exc_info=True)
        splash.close()
        QMessageBox.critical(
            None,
            "Database Error",
            f"PhotoCleaner konnte die Datenbank nicht initialisieren:\n\n{db_path}\n\n{e}"
        )
        sys.exit(1)

    # Ensure DLL search paths are available before TensorFlow import in frozen builds
    _prepare_windows_dll_search_paths(app_dir, logger)
    if mode == AppMode.DEBUG:
        if "TF_CPP_MIN_LOG_LEVEL" not in os.environ or os.environ.get("TF_CPP_MIN_LOG_LEVEL") != "0":
            os.environ["TF_CPP_MIN_LOG_LEVEL"] = "0"
            logger.debug("TF_CPP_MIN_LOG_LEVEL forced to 0 for debug logging")
        if "PYTHONVERBOSE" not in os.environ:
            logger.debug("PYTHONVERBOSE not set (requires process restart to take effect)")
        _log_tf_pre_import(logger)
        _log_tf_diagnostics(app_dir, logger)

    # ====================================================================
    # PHASE 3.4: TensorFlow waehrend sichtbarem Splash laden
    # ====================================================================
    mtcnn_status = {"available": False, "error": None}
    try:
        tf_import_start = time.perf_counter()
        import tensorflow as tf
        tf_import_elapsed = time.perf_counter() - tf_import_start
        logger.info(f"TensorFlow {tf.__version__} loaded successfully in {tf_import_elapsed:.2f}s")
        if tf_import_elapsed > 2.0:
            logger.warning("TensorFlow import took %.2fs; GPU enumeration may be slow", tf_import_elapsed)
        _configure_keras_logging(logger)
    except Exception as e:
        mtcnn_status["error"] = str(e)
        mtcnn_status["error"] = _sanitize_mtcnn_error(mtcnn_status["error"])
        logger.error(f"✗ TensorFlow initialization failed: {type(e).__name__}: {e}")
        if isinstance(e, ModuleNotFoundError) and "tensorflow" in str(e).lower():
            logger.error("TensorFlow not found in this Python environment. Please run using .venv\\Scripts\\python.exe or install TensorFlow in the active environment.")
        logger.warning("⚠ Photo quality analysis will use fallback face detection (Haar Cascade)")
        logger.warning("⚠ This may reduce accuracy in detecting best photos with faces")
    
    # NOTE: Do NOT show MTCNN warning yet - MTCNN may be re-initialized below
    # Warning will only be shown if MTCNN still unavailable after splash phase
    
    # ====================================================================
    # PHASE 3.5: License System und MTCNN nach Splash initialisieren
    # ====================================================================
    # CRITICAL: Initialize License System with proper error handling
    license_mgr = None
    try:
        from photo_cleaner.license import initialize_license_system, get_license_manager

        initialize_license_system(app_dir)
        license_mgr = get_license_manager()
        status = license_mgr.get_license_status()
        logger.info(f"License System initialized: {status.get('license_type', 'FREE')}")
    except ImportError as e:
        logger.warning(f"Cryptography module not available (offline mode): {e}")
    except Exception as e:
        logger.error(f"License System initialization failed (continuing with defaults): {e}")
        import traceback
        logger.debug(traceback.format_exc())

    # MTCNN initialisieren waehrend Splash sichtbar ist
    if mtcnn_status["available"] is False and mtcnn_status["error"] is None:
        splash.show_progress(t("splash_loading_image_processing"), 20)
        logger.info("Pre-initializing MTCNN after splash...")
        weights_path = _get_mtcnn_weights_path()
        if weights_path:
            logger.info(f"MTCNN weights path: {weights_path} (exists={weights_path.exists()})")
        else:
            logger.warning("MTCNN weights path not resolved")
        try:
            from mtcnn import MTCNN
            test_detector = MTCNN()
            logger.info("✓ MTCNN successfully initialized after splash")
            mtcnn_status["available"] = True
            del test_detector
        except Exception as e:
            mtcnn_status["error"] = str(e)
            mtcnn_status["error"] = _sanitize_mtcnn_error(mtcnn_status["error"])
            logger.error(f"✗ MTCNN initialization failed: {type(e).__name__}: {e}")
    
    # NOW show warning if MTCNN still unavailable (after splash retry attempt)
    if not mtcnn_status["available"]:
        logger.warning("⚠ Photo quality analysis will use fallback face detection (Haar Cascade)")
        logger.warning("⚠ This may reduce accuracy in detecting best photos with faces")

    # ====================================================================
    # PHASE 4: Schwere Module LAZY laden (mit Progress-Anzeige)
    # ====================================================================
    splash.show_progress(t("splash_loading_ui"), 30)
    
    # CRITICAL: Delay heavy imports until after splash screen
    # This avoids numpy initialization issues in frozen PyInstaller environment
    try:
        splash.show_progress(t("splash_loading_image_processing"), 60)
        # Pre-initialize numpy in a safe context
        try:
            import numpy as np
            _ = np.array([1, 2, 3])
            logger.info("NumPy initialized successfully")
        except Exception as e:
            logger.warning(f"NumPy initialization: {e}")

        # Check pHash AFTER numpy is initialized to avoid TypeError in frozen builds
        from photo_cleaner.core.hasher import check_phash_support
        check_phash_support(logger)

        splash.show_progress(t("splash_preparing_ui"), 80)
        from photo_cleaner.ui.modern_window import run_modern_ui
        logger.info("UI module loaded successfully")
    except Exception as e:
        logger.error(f"Critical error loading UI modules: {e}")
        import traceback
        logger.error(traceback.format_exc())
        splash.close()
        QMessageBox.critical(
            None,
            "Kritischer Fehler",
            f"Konnte UI-Module nicht laden:\n\n{e}\n\nBitte überprüfen Sie die Logs."
        )
        sys.exit(1)

    # ====================================================================
    # PHASE 5: Finale Startup-Infos
    # ====================================================================
    if input_path:
        logger.info(f"Using input: {input_path}")
    if output_path:
        logger.info(f"Using output: {output_path}")
    if db_path:
        logger.info(f"Using database: {db_path}")
    logger.info(f"PhotoCleaner Version: {VERSION}")

    # ====================================================================
    # PHASE 6: Hauptfenster starten und Splash beenden
    # ====================================================================
    splash.show_progress(t("splash_starting"), 100)
    
    # run_modern_ui erstellt das Hauptfenster und gibt es zurück
    # Splash wird automatisch nach 500ms beendet
    result = run_modern_ui(
        db_path=db_path, 
        output_path=output_path, 
        input_path=input_path,
        app=app,  # Übergebe existierende App
        splash=splash,  # Übergebe Splash zum Beenden
        mtcnn_status=mtcnn_status,  # Übergebe MTCNN Status für User-Warnung
    )
    
    return result


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        # Graceful Ctrl+C handling: attempt Qt cleanup to avoid
        # "QThread: Destroyed while thread is still running" warnings.
        try:
            from PySide6.QtWidgets import QApplication

            app = QApplication.instance()
            if app is not None:
                for widget in app.topLevelWidgets():
                    try:
                        widget.close()
                    except Exception:
                        pass
                app.quit()
                app.processEvents()
        except Exception:
            pass
        sys.exit(130)

