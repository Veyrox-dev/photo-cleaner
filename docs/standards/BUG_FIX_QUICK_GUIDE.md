# ⚡ CODE AUDIT - QUICK FIX GUIDE

**Status**: 16 issues identified  
**Critical**: 4 issues  
**High Priority**: 8 issues  
**Medium**: 4 issues  

---

## 🔴 P0 - FIX IMMEDIATELY (Vor nächstem Release)

### 1️⃣ MTCNN Race Condition
- **File**: `src/photo_cleaner/pipeline/quality_analyzer.py`
- **Issue**: Multiple threads can create multiple MTCNN instances
- **Fix**: Add `threading.Lock()` to `_mtcnn_detector_cache` initialization
- **Time**: ~15 minutes
- **Impact**: Prevents memory leaks and crashes in multiprocessing

### 2️⃣ File-Lock TOCTOU Bug
- **File**: `src/photo_cleaner/repositories/file_repository.py`
- **Issue**: File can be locked between CHECK and UPDATE
- **Fix**: Use `UPDATE ... WHERE is_locked = 0` atomically
- **Time**: ~30 minutes
- **Impact**: Prevents status changes on locked files

### 3️⃣ MediaPipe Memory Leak
- **File**: `src/photo_cleaner/pipeline/quality_analyzer.py`
- **Issue**: Face Mesh model never closed, TensorFlow session stays open
- **Fix**: Implement `__del__` and `_cleanup_models()`
- **Time**: ~20 minutes
- **Impact**: Prevents ~100MB memory leak per scan

### 4️⃣ Batch Update Transaction Safety
- **File**: `src/photo_cleaner/ui_actions.py`
- **Issue**: History inserted but file status might not update (partial write)
- **Fix**: Single atomic transaction for all operations
- **Time**: ~40 minutes
- **Impact**: Prevents database inconsistency

---

## 🟠 P1 - Fix in Next Sprint

- [ ] Global module state thread safety
- [ ] Cache invalidation error handling
- [ ] SQLite rollback failure handling
- [ ] EXIF data validation (size limits)

---

## 🟡 P2 - Performance & UX

- [ ] Fast cache lookup (metadata instead of full hash)
- [ ] Async EXIF loading (background thread)
- [ ] RatingWorkerThread file verification
- [ ] Path validation framework

---

## 📊 TESTING CHECKLIST

After fixing P0 issues:

```
[ ] Run multiprocessing tests with 1000+ images
[ ] Test concurrent file locking
[ ] Verify memory usage stays stable across 10 scans
[ ] Test rating worker with deleted/locked files
[ ] Memory profiling with large image sets
[ ] Test on Windows with long file paths
```

---

## 💾 COMMIT PLAN

**P0 Fixes Branch**: `fix/p0-critical-bugs`

1. MTCNN Lock
2. File-Lock TOCTOU  
3. MediaPipe Cleanup
4. Batch Transaction Safety
5. SQLite Rollback Safety

**Expected commits**: 5-6  
**Test time**: 1-2 hours  
**Review time**: 30 minutes  

---

Generated: 5. Februar 2026
