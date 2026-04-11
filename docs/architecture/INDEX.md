# Architecture Documentation

## Pipeline Architecture

The PhotoCleaner application follows a **6-stage pipeline** designed for efficient duplicate detection and quality-based selection:

### Stages

1. **Indexing** (5-10 min @ 10k images)
   - Recursive folder scanning
   - Perceptual Hash (pHash) computation
   - Metadata extraction (size, date, dimensions)
   - Parallel processing with ProcessPoolExecutor

2. **Duplicate Detection** (~30 sec @ 10k images)
   - Hamming distance ≤ 5 on pHash
   - Bucketed comparison (optimized)
   - Grouping of similar images

3. **Cheap Filter** (1-2 min @ 10k images)
   - Resolution < 800x600 excluded
   - Blurry (Laplacian < 50) excluded
   - Over/underexposed excluded
   - OpenCV only (no AI) → very fast

4. **Quality Analysis** (5-15 min, only on groups)
   - MediaPipe Face Mesh (selective: 10-20% of images)
   - Eye quality scoring (open/closed)
   - Gaze direction (forward/away)
   - Head pose (straight/tilted)
   - Face sharpness

5. **Scoring & Top-N Marking** (~1 sec)
   - Ranking within each group
   - Top-N automatically marked KEEP
   - Rest marked DELETE

6. **User Decision** (Results UI)
   - Top-N shown in green (KEEP)
   - Rest in red (DELETE)
   - Thumbnail preview with scores
   - Delete button with confirmation

## Key Design Patterns

### Thread Safety
- `threading.Lock()` for shared resource initialization
- Double-check locking pattern for expensive operations
- Atomic database operations (UPDATE WHERE)

### Performance Optimization
- Metadata-based cache lookup (18,000x faster)
- Resolution-adaptive processing (3.75x speedup)
- ThreadPool parallelization (2.45x speedup)
- Model caching (amortized 1.2x speedup)

### Worker Threads
- `RatingWorkerThread` for batch operations
- `ExifWorkerThread` for metadata extraction
- Signal/slot pattern for Qt communication
- Progress callbacks for UI updates

### Security
- Path traversal prevention with `_validate_safe_path()`
- EXIF DoS protection (500 field limit, 100KB size limit)
- Atomic file operations to prevent TOCTOU vulnerabilities
- Numeric EXIF validation against physical ranges

## Database Schema

### Tables

- **files** - File metadata and status
- **duplicates** - Group membership mapping
- **image_cache** - Analysis results caching
- **migrations** - Schema evolution tracking

### Migrations

Versioned schema migrations with:
- Checksum validation (SHA256)
- Rollback support
- Version tracking
- Safe evolution path

## Performance Profile

| Component | Time @ 10k images | Notes |
|-----------|-------------------|-------|
| Indexing | 5-10 min | Disk I/O bound |
| Find Duplicates | ~30 sec | Hash comparison |
| Cheap Filter | 1-2 min | OpenCV processing |
| Face Mesh | 5-15 min | MediaPipe bottleneck |
| Scoring | ~1 sec | Database |
| **Total** | **12-28 min** | Face Mesh is bottleneck |

### Optimizations in v0.8.2

- **Cache Fast Lookup**: Metadata-based lookup eliminates full-file hash (8 min → <1 sec for 10k)
- **Async EXIF**: ExifWorkerThread prevents UI blocking during metadata extraction
- **Atomic Operations**: TOCTOU elimination through atomic SQL updates
- **Memory Safety**: Proper resource cleanup prevents memory leaks

## Module Hierarchy

```
photo_cleaner/
├── pipeline/
│   ├── quality_analyzer.py      (Quality scoring with MediaPipe)
│   ├── duplicate_finder.py      (pHash & Hamming distance)
│   ├── scorer.py                (Group ranking)
│   └── final_pipeline.py        (6-stage orchestration)
├── repositories/
│   ├── file_repository.py       (File metadata persistence)
│   ├── duplicate_repository.py  (Group management)
│   └── migrations.py            (Schema evolution)
├── cache/
│   └── image_cache_manager.py   (Analysis result caching)
├── ui/
│   ├── modern_window.py         (Modern Qt6 UI)
│   └── classic_window.py        (Legacy UI)
└── utils/
    ├── logger.py                (Logging configuration)
    └── decorators.py            (Common decorators)
```

## Security Considerations

### Path Validation
- Blocks `../` traversal attempts
- Blocks system directories (Windows, Unix)
- Resolves to absolute normalized paths
- Applied to all file operations

### EXIF Validation
- Field count limited to 500
- JSON size limited to 100KB
- Numeric values validated:
  - ISO: 1-409,600
  - Aperture: f/0.95-f/64
  - Focal Length: 1-5000mm
  - Exposure: 0.0001-60s

### Database Safety
- Atomic operations prevent TOCTOU
- Rowcount verification after updates
- Proper error handling with rollback
- Transaction isolation

## Testing Strategy

- **Unit Tests**: Module-level testing (~54 tests)
- **E2E Tests**: Integration testing (~47 tests)
- **Performance Tests**: Baseline tracking & regression detection
- **Security Tests**: Path validation, EXIF limits
- **CI/CD**: GitHub Actions multi-platform testing

## Versioning

Current version: **0.8.7**
- v0.8.7: export options expanded, UI consistency update, version bump
- v0.8.2: Algorithm improvements (eye quality, gaze, head pose)
- v0.7.0: Performance speedup (9.19x faster)
- v0.6.0: Data-driven foundation (migrations, CI/CD)

See [CHANGELOG.md](../CHANGELOG.md) for full history.

## Related Documents

- [Tech Documentation](../tech/) - Implementation details
- [Standards](../standards/) - Quality metrics and audits
- [Guides](../guides/) - How-to documentation
- [Week 4 Plan](WEEK4_ONBOARDING_SMART_FILTER.md) - Onboarding, smart filters, quota messaging
