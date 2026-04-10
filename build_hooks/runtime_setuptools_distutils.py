"""Runtime hook to stabilize setuptools._distutils imports in frozen builds.

TensorFlow/MTCNN/SciPy stacks may resolve distutils compiler helpers lazily
and fail with KeyError on setuptools._distutils.compilers when module graph
is incomplete in PyInstaller builds.
"""

from __future__ import annotations

import importlib
import sys


def _safe_import(name: str) -> None:
    try:
        importlib.import_module(name)
    except Exception:
        # Best-effort preload; failures should not crash startup here.
        pass


# Ensure setuptools distutils namespace exists and has stable aliases.
_safe_import("setuptools")
_safe_import("setuptools._distutils")

try:
    import setuptools._distutils as _setuptools_distutils

    sys.modules.setdefault("distutils", _setuptools_distutils)
except Exception:
    _setuptools_distutils = None

# Preload compiler namespaces that are lazily resolved by TF/SciPy stack.
for module_name in (
    "setuptools._distutils.compilers",
    "setuptools._distutils.compilers.C",
    "setuptools._distutils.compilers.C.base",
    "setuptools._distutils.compilers.C.errors",
    "setuptools._distutils.compilers.C.msvc",
    "setuptools._distutils.compilers.C.unix",
    "setuptools._distutils.compilers.C.cygwin",
    "setuptools._distutils.ccompiler",
    "setuptools._distutils._msvccompiler",
    "setuptools._distutils.unixccompiler",
):
    _safe_import(module_name)
