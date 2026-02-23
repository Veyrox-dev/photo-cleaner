# Override pycparser hook to avoid optional lextab/ya cctab hidden imports.
# They are generated at runtime and not required for PhotoCleaner.
hiddenimports = []
