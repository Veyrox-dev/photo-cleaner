# PhotoCleaner API Reference

**Version:** 0.8.2 (Feb 2026)

This document lists the supported entry points and stable APIs for developers.

---

## Python API

### Pipeline

```python
from pathlib import Path
from photo_cleaner.pipeline import run_final_pipeline

stats = run_final_pipeline(
    folder_path=Path("/path/to/photos"),
    db_path=Path("photo_cleaner.db"),
    top_n=3,
    hash_dist=5,
    use_face_mesh=True,
)

print(stats.duplicate_groups)
print(stats.marked_delete)
```

Notes:
- `run_final_pipeline` is the primary programmatic entry point.
- For performance-sensitive runs, set `use_face_mesh=False`.

### Cheap Filter (optional)

```python
from photo_cleaner.pipeline import CheapFilter

cheap = CheapFilter()
result = cheap.analyze_image("/path/to/image.jpg")
print(result.is_rejected)
```

### Quality Analyzer (lazy import)

```python
from photo_cleaner.pipeline import QualityAnalyzer

analyzer = QualityAnalyzer(use_face_mesh=False)
result = analyzer.analyze_image(Path("/path/to/image.jpg"))
print(result.quality_score)
```

---

## CLI

The CLI is implemented in `photo_cleaner.cli` and uses Click.

```bash
# Index a folder
python -m photo_cleaner.cli index /path/to/photos

# Show stats
python -m photo_cleaner.cli stats
```

---

## UI Entry Points

### Modern UI

```bash
python -m photo_cleaner.ui.modern_window
```

Programmatic launch:

```python
from photo_cleaner.ui.modern_window import run_modern_ui

run_modern_ui("photo_cleaner.db")
```

### Classic UI

```bash
python run_ui.py
```

---

## License System API

```python
from photo_cleaner.license import (
    LicenseManager,
    LicenseType,
    FeatureFlagsManager,
    initialize_license_system,
    get_license_manager,
    get_feature_flags,
)

initialize_license_system()
manager = get_license_manager()
flags = get_feature_flags()

if manager.is_feature_enabled(flags.BATCH_PROCESSING):
    pass
```

Details:
- See [docs/guides/LICENSE_SYSTEM.md](../guides/LICENSE_SYSTEM.md)
- See [docs/guides/LICENSE_SIGNATURES.md](../guides/LICENSE_SIGNATURES.md)

---

## Stability Notes

- The APIs above are considered stable for internal use.
- Internal modules may change without notice.
- For deeper internals, see [docs/architecture/INDEX.md](../architecture/INDEX.md).
