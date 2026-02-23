# Hook für numpy - korrigiert das docstring Problem bei PyInstaller
from PyInstaller.utils.hooks import (
    collect_submodules, 
    collect_data_files,
    get_module_file_attribute,
)

# Alle numpy Module einsammeln
hiddenimports = collect_submodules('numpy')

# Explizit sicherstellen, dass kritische Module geladen werden
hiddenimports.extend([
    'numpy.core.multiarray',
    'numpy.core.overrides', 
    'numpy.core._methods',
    'numpy.core.umath',
    'numpy.lib',
    'numpy.random',
    'numpy.linalg',
    'numpy.fft',
    'numpy.polynomial',
])

# Daten-Dateien einsammeln
datas = collect_data_files('numpy')
