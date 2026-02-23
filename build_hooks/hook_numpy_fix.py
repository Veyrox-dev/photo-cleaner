# Hook to fix numpy compatibility issues with PyInstaller
# This fixes: TypeError: argument docstring of add_docstring should be a str

from PyInstaller.utils.hooks import collect_submodules

# Collect all numpy submodules to ensure they're available
hiddenimports = collect_submodules('numpy')

# Add common numpy submodules that might be missed
hiddenimports.extend([
    'numpy.core.multiarray',
    'numpy.core.overrides',
    'numpy.core._multiarray_umath',
    'numpy.core.multiarray_umath',
])

# Make sure numpy.lib and numpy.random are included
hiddenimports.extend([
    'numpy.lib',
    'numpy.random',
    'numpy.linalg',
    'numpy.fft',
])
