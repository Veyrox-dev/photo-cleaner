#!/usr/bin/env python3
"""Strict preflight checks for Windows freeze builds.

Exit code:
  0 - All checks passed
  1 - One or more checks failed
"""
from __future__ import annotations

import argparse
import os
import sys
import warnings
from pathlib import Path


def _win_dll_ok(name: str) -> tuple[bool, str]:
    if sys.platform != "win32":
        return False, "Not running on Windows"
    try:
        import ctypes

        ctypes.WinDLL(name, use_last_error=True)
        return True, "loaded"
    except OSError as exc:
        try:
            import ctypes

            last_error = ctypes.get_last_error()
            win_error = ctypes.WinError(last_error) if last_error else None
            return False, f"{exc} (last_error={last_error}, win_error={win_error})"
        except Exception:
            return False, str(exc)


def _check(name: str, ok: bool, details: str, results: list[tuple[str, bool, str]]) -> None:
    results.append((name, ok, details))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    results: list[tuple[str, bool, str]] = []

    # Python version and ABI
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    _check("python_version", py_version == "3.11.9", f"sys.version={sys.version}", results)
    abiflags = getattr(sys, "abiflags", None)
    if abiflags is None:
        _check("sys_abiflags", True, "sys.abiflags not available on this platform", results)
    else:
        _check("sys_abiflags", abiflags == "", f"sys.abiflags={abiflags!r}", results)

    # Python DLL
    py_exe_dir = Path(sys.executable).resolve().parent
    base_dir = Path(sys.base_prefix).resolve()
    py_dll_candidates = [
        py_exe_dir / "python311.dll",
        base_dir / "python311.dll",
    ]
    py_dll_found = next((p for p in py_dll_candidates if p.exists()), None)
    _check(
        "python311.dll_exists",
        py_dll_found is not None,
        str(py_dll_found) if py_dll_found else "; ".join(str(p) for p in py_dll_candidates),
        results,
    )
    if py_dll_found is not None:
        ok, detail = _win_dll_ok(str(py_dll_found))
        _check("python311.dll_load", ok, detail, results)
    else:
        _check("python311.dll_load", False, "python311.dll not found", results)

    # PATH hygiene
    path_lower = os.environ.get("PATH", "").lower()
    has_py312 = "python312" in path_lower or "python 3.12" in path_lower
    _check("path_no_python312", not has_py312, "PATH contains Python 3.12" if has_py312 else "ok", results)

    # PyInstaller version
    try:
        import PyInstaller  # type: ignore

        pi_version = getattr(PyInstaller, "__version__", "unknown")
        ok = pi_version.startswith("6.7.") or pi_version.startswith("6.8.")
        _check("pyinstaller_version", ok, f"PyInstaller {pi_version}", results)
    except Exception as exc:
        _check("pyinstaller_version", False, f"import failed: {exc}", results)

    # TensorFlow imports with warnings as errors
    try:
        warnings.simplefilter("error")
        import tensorflow as tf  # type: ignore

        tf_version = getattr(tf, "__version__", None)
        tf_file = getattr(tf, "__file__", None)
        if tf_version is None:
            _check("tensorflow_version", False, f"__version__ missing (module={tf_file})", results)
        else:
            _check("tensorflow_version", tf_version == "2.16.2", f"tf.__version__={tf_version}", results)
        try:
            from tensorflow.python import _pywrap_tensorflow_internal  # noqa: F401
            _check("pywrap_internal_import", True, "ok", results)
        except Warning as exc:
            _check("pywrap_internal_import", False, f"warning: {exc}", results)
        except Exception as exc:
            _check("pywrap_internal_import", False, f"error: {exc}", results)
    except Warning as exc:
        _check("tensorflow_import", False, f"warning: {exc}", results)
    except Exception as exc:
        _check("tensorflow_import", False, f"error: {exc}", results)

    # Native runtime dependencies
    for dll_name in (
        "VCRUNTIME140.dll",
        "VCRUNTIME140_1.dll",
        "MSVCP140.dll",
        "MSVCP140_1.dll",
        "MSVCP140_2.dll",
        "concrt140.dll",
    ):
        ok, detail = _win_dll_ok(dll_name)
        _check(f"dll_{dll_name}", ok, detail, results)

    # TensorFlow DLLs in venv
    try:
        import sysconfig

        purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
        tf_dir = purelib / "tensorflow"
        _check("tf_dir_exists", tf_dir.exists(), str(tf_dir), results)
        dlls = list(purelib.rglob("tensorflow*.dll"))
        stray = [p for p in dlls if tf_dir not in p.parents]
        _check(
            "tf_dlls_stray",
            not stray,
            "stray: " + "; ".join(str(p) for p in stray) if stray else "ok",
            results,
        )
    except Exception as exc:
        _check("tf_dlls_stray", False, f"scan failed: {exc}", results)

    # Spec sanity check
    spec_path = Path("PhotoCleaner.spec")
    if not spec_path.exists():
        _check("spec_exists", False, "PhotoCleaner.spec missing", results)
    else:
        text = spec_path.read_text(encoding="utf-8", errors="ignore")
        _check("spec_onedir", "COLLECT(" in text and "exclude_binaries=True" in text, "onedir markers", results)
        _check("spec_no_runtime_hooks", "runtime_hooks=[]" in text.replace(" ", ""), "runtime_hooks empty", results)

    # Report
    print("\nPreflight report:\n")
    failed = False
    for name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"- {name}: {status} | {detail}")
        if not ok:
            failed = True

    if failed:
        print("\nPreflight result: FAIL")
        return 1
    print("\nPreflight result: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
