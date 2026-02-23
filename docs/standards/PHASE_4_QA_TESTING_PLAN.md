# Phase 4: QA & Testing Plan for v1.0.0 Release

**Document**: Comprehensive Testing & Quality Assurance Strategy  
**Date**: February 5, 2026  
**Timeline**: 16 weeks (Feb-Jul 2026)  
**Goal**: v0.8.2 (current) → v1.0.0 Release Candidate → v1.0.0 Final

---

## Overview: What is Phase 4?

Phase 4 is the **quality assurance and validation phase** where we transform v0.8.2 (feature-complete, performance-optimized) into v1.0.0 (production-ready, thoroughly tested).

**Current Status:**
- ✅ v0.8.2: All P0-P2 bugs fixed
- ✅ Code: 0 compilation errors
- ✅ Performance: 9.19x speedup complete
- ✅ Features: Complete (duplicate detection, quality scoring, auto-select)
- 🔄 **NOW**: Phase 4 Testing begins

---

## Phase 4 Structure: 4 Stages (16 weeks)

```
STAGE 1: Unit & Integration Testing (4 weeks)
├─ Fix failing tests
├─ Achieve 80%+ code coverage
├─ All major modules verified

STAGE 2: Security Audit (3 weeks)
├─ License key validation hardening
├─ SQL Injection prevention
├─ File permission & deletion safety
├─ Offline mode integrity

STAGE 3: Stress & Performance Testing (5 weeks)
├─ 10,000 image stress test
├─ 50,000 image stress test
├─ 100,000 image stress test
├─ Memory leak profiling
├─ CPU utilization optimization

STAGE 4: Release Build & Documentation (4 weeks)
├─ Finalize PhotoCleaner.exe
├─ Write User Manual
├─ Create API Documentation
├─ Compile Release Notes
├─ v1.0.0 Release Candidate

└─ RESULT: v1.0.0 RC ready for Phase 5 (Market Prep)
```

---

## STAGE 1: Unit & Integration Testing (4 weeks)

### Current Test Status

**What We Have:**
- 307 total tests collected
- E2E tests: License, Device Binding, Workflows ✅
- Integration tests: Cache pipeline, rule validation
- Unit tests: Session manager, guards, streaming exporter
- **1 failing test**: `test_cache_size_statistics` (top_n_entries not captured correctly)

**Test Framework:**
```
pytest 9.0.2 (with plugins: mock-3.15.1)
Python 3.14.2
Coverage target: 80%+ of codebase
```

### Stage 1 Tasks

#### Week 1: Fix Failing Tests & Improve Coverage

1. **Fix the 1 Failing Test** (IMMEDIATE)
   ```
   tests/integration/test_cache_pipeline_integration.py::TestCachePipelineIntegration::test_cache_size_statistics
   
   Issue: size_info["top_n_entries"] returns 0 instead of 1
   Cause: Query not properly counting top_n entries
   Fix: Verify cache.get_cache_size() implementation
   ```

2. **Add Missing Tests for Critical Modules**
   - [ ] `src/services/rule_simulator.py` - Rule evaluation logic
   - [ ] `src/services/progress_service.py` - Progress tracking
   - [ ] `src/database/database.py` - All CRUD operations
   - [ ] `src/pipeline/analyzer.py` - Main analysis pipeline

3. **Add Security-Focused Tests**
   - [ ] SQL Injection attempts (prepared statements)
   - [ ] Invalid file paths (path traversal)
   - [ ] Concurrent access patterns (race conditions)
   - [ ] Large batch operations (memory limits)

#### Week 2-3: Stress Testing

1. **Create Stress Test Suite**
   ```python
   # test_stress_1k_images.py
   def test_analyze_1000_images():
       """Baseline: 1,000 images should complete <30s"""
       
   # test_stress_10k_images.py
   def test_analyze_10000_images():
       """Scale up: 10,000 images should complete <5 min"""
       
   # test_stress_50k_images.py
   def test_analyze_50000_images():
       """Large: 50,000 images should complete <20 min"""
       
   # test_stress_100k_images.py
   def test_analyze_100000_images():
       """Extreme: 100,000 images should complete <45 min"""
   ```

2. **Performance Targets**
   | Scale | Time Target | Memory Target | CPU Usage |
   |-------|-------------|---------------|-----------|
   | 1k images | <30s | <100MB | <40% |
   | 10k images | <5 min | <200MB | <60% |
   | 50k images | <20 min | <500MB | <70% |
   | 100k images | <45 min | <800MB | <80% |

3. **Memory Leak Detection**
   ```python
   def test_no_memory_leak_batch_operations():
       """
       Memory should stabilize after batch completion.
       - Start memory: baseline
       - Process 5k images
       - End memory: should return to near-baseline
       """
   ```

#### Week 4: Test Coverage Analysis

1. **Generate Coverage Report**
   ```bash
   pytest tests/ --cov=src --cov-report=html
   ```

2. **Target Modules** (must reach 80%+)
   - `pipeline/quality_analyzer.py` - Core scoring
   - `database/database.py` - All CRUD
   - `services/rule_simulator.py` - Rule logic
   - `cache/image_cache_manager.py` - Cache operations
   - `ui/main_window.py` - UI logic

3. **Coverage Threshold**: 80% overall, 90% for critical modules

---

## STAGE 2: Security Audit (3 weeks)

### Security Checklist

#### License Key Validation (Week 1)
- [ ] License key format validation (regex, length)
- [ ] License key cannot be forged/modified
- [ ] Device binding prevents key sharing
- [ ] Expired licenses properly handled
- [ ] Offline mode doesn't bypass license check

**Test Case:**
```python
def test_license_key_cannot_be_forged():
    """Malformed keys should be rejected"""
    invalid_keys = [
        "12345",  # Too short
        "aaaa-bbbb-cccc-dddd",  # Invalid format
        "ZZZZ-YYYY-XXXX-WWWW",  # Invalid characters
    ]
    for key in invalid_keys:
        assert not validate_license_key(key)

def test_device_binding_prevents_key_sharing():
    """Same key on different devices should fail"""
    # Device 1: Activate key ABC123
    license1 = activate_license("ABC123", device_id_1)
    assert license1.is_valid()
    
    # Device 2: Try same key
    license2 = activate_license("ABC123", device_id_2)
    assert not license2.is_valid()
```

#### SQL Injection Prevention (Week 1-2)
- [ ] All database queries use parameterized statements
- [ ] No string concatenation in SQL
- [ ] User input sanitization
- [ ] Test with malicious input: `' OR '1'='1`

**Audit Script:**
```python
# Check all database.py queries
import re
with open("src/database/database.py") as f:
    content = f.read()
    # Find all execute() calls
    unsafe = re.findall(r'execute\(["\'].*{.*}["\']', content)
    if unsafe:
        print(f"WARNING: Found {len(unsafe)} unsafe SQL patterns")
```

#### File Permission & Deletion Safety (Week 2)
- [ ] Confirm files are marked for deletion before permanent removal
- [ ] Trash functionality prevents accidental data loss
- [ ] No directory traversal attacks possible (../../)
- [ ] Permission errors handled gracefully

**Test Cases:**
```python
def test_cannot_delete_outside_base_directory():
    """Path traversal attempt should fail"""
    base = "/home/photos"
    unsafe_path = "/home/photos/../../etc/passwd"
    assert not is_safe_to_delete(unsafe_path, base)

def test_trash_before_permanent_delete():
    """File must be in trash before actual deletion"""
    file.mark_for_deletion()
    assert file.status == "in_trash"
    # Only after user confirmation:
    file.permanently_delete()
    assert file.is_deleted()
```

#### Offline Mode Integrity (Week 3)
- [ ] License cache is tamper-proof
- [ ] Offline mode doesn't allow unlimited image processing
- [ ] Sync works correctly when device comes back online
- [ ] No feature-gate bypass in offline mode

---

## STAGE 3: Stress & Performance Testing (5 weeks)

### Test Data Preparation (Week 1)

Create realistic test image sets:
```
test_data_stress/
├─ 1k_images/       (100MB)
├─ 10k_images/      (1GB)
├─ 50k_images/      (5GB)
└─ 100k_images/     (10GB)

Each set contains:
- JPG, PNG, HEIC formats
- Various resolutions (mobile, DSLR, 4K)
- Different types (portrait, landscape, low-light)
```

### Week 2-3: Scale Testing

**Benchmark 1: 1,000 Images**
```
Time: ~20-30 seconds ✓ (baseline should be fast)
Memory: ~80-100 MB
CPU: 40-50%
```

**Benchmark 2: 10,000 Images**
```
Time: ~3-5 minutes (on i7-12700F)
Memory: ~150-200 MB
CPU: 50-60%
Expected speedup: 200x faster than v0.6.0
```

**Benchmark 3: 50,000 Images** ⚠️ Important for Phase 5 large-scale users
```
Time: ~15-20 minutes
Memory: ~400-500 MB (should not spike)
CPU: 60-70%
Check: No crashes, stable performance
```

**Benchmark 4: 100,000 Images** 🎯 Stress test limit
```
Time: ~40-45 minutes
Memory: ~700-800 MB (not exceeding 1GB)
CPU: 70-80%
Check: Absolute maximum capacity
```

### Week 4-5: Memory & Profiling

**Memory Leak Detection:**
```python
import tracemalloc

def test_no_memory_leaks_after_large_batch():
    tracemalloc.start()
    
    # Get baseline
    baseline = tracemalloc.take_snapshot()
    
    # Process 10k images
    analyzer.process_folder(large_folder)
    
    # Check memory
    current = tracemalloc.take_snapshot()
    diff = current.compare_to(baseline, 'lineno')
    
    # Should not grow by >50MB
    total_growth = sum(stat.size_diff for stat in diff[:10])
    assert total_growth < 50 * 1024 * 1024
```

**CPU Profiling:**
```python
import cProfile

profiler = cProfile.Profile()
profiler.enable()

# Run analysis on 10k images
analyzer.process_folder(medium_folder)

profiler.disable()
profiler.print_stats(10)  # Top 10 hotspots
```

**Result:** Identify and optimize top 5 performance bottlenecks

---

## STAGE 4: Release Build & Documentation (4 weeks)

### Week 1: Finalize Executable

**Current State:**
- Python source code ✅
- Unit tests ✅
- Integration tests ✅
- Dependencies: requirements.txt ✅

**Tasks:**
1. **Build PhotoCleaner.exe** using PyInstaller
   ```bash
   pyinstaller PhotoCleaner.spec --onefile
   ```

2. **Test Executable**
   - [ ] Runs on fresh Windows system (no Python installed)
   - [ ] All features work (duplicate detection, settings, export)
   - [ ] License system works
   - [ ] File associations correct
   - [ ] Uninstaller works properly

3. **Version Numbering**
   ```
   Version: 1.0.0
   Internal version (Windows): 1.0.0.0
   Build: #12345 (automatic)
   Release date: October 15, 2026
   ```

### Week 2: User Manual

**Contents:**
1. Getting Started
   - Installation (Windows 7+, 10, 11)
   - First launch
   - License activation
   - Settings configuration

2. Feature Guide
   - How duplicate detection works
   - Quality scoring explanation
   - Auto-select recommendations
   - Manual review & confirmation

3. Workflows
   - Basic workflow (import → analyze → review → delete)
   - Batch operations
   - Undo/redo
   - Exporting results

4. Troubleshooting
   - "No duplicates found" - why?
   - Performance optimization
   - Common errors
   - License issues

5. FAQ
   - Q: Will it delete my photos accidentally?
   - A: No, all deletions require manual confirmation...
   - Q: How much storage does it need?
   - A: ~500MB for 10,000 images...
   - etc.

**Format:** PDF + HTML + In-app help text

### Week 3: API Documentation

**For Future Developers:**

1. **Module Documentation**
   - `pipeline/` - Image analysis pipeline
   - `database/` - Data persistence
   - `services/` - Business logic
   - `ui/` - User interface

2. **Key Classes**
   ```python
   class ImageAnalyzer:
       """Main analysis engine"""
       def analyze(image_path: Path) -> QualityScore
       
   class Database:
       """Data persistence"""
       def query_duplicates() -> List[DuplicateGroup]
       
   class RuleSimulator:
       """Rule evaluation"""
       def should_auto_delete(image: Image, rules: List[Rule]) -> bool
   ```

3. **API Examples**
   ```python
   # How to use PhotoCleaner as a library
   from photo_cleaner.pipeline import ImageAnalyzer
   
   analyzer = ImageAnalyzer()
   score = analyzer.analyze("/path/to/image.jpg")
   print(f"Quality: {score.quality_percent}%")
   ```

### Week 4: Release Notes & RC Release

**Release Notes for v1.0.0:**

```markdown
# PhotoCleaner v1.0.0 - Release Candidate

## New Features
- ✨ Complete duplicate detection system
- ✨ AI-powered quality scoring
- ✨ Auto-select best from each group
- ✨ License system with Free/Pro/Enterprise tiers
- ✨ Batch processing for large image libraries
- ✨ Undo/redo support
- ✨ Export results as CSV/JSON
- ✨ Dark theme support

## Performance Improvements
- ⚡ 9.19x faster than v0.7.0
- ⚡ Processing 5,000 images in 2.1 minutes
- ⚡ Memory-efficient: <200MB for 10k images
- ⚡ Resolution-adaptive detection

## Bug Fixes
- 🐛 Fixed 4 P0 critical bugs (race conditions, memory leaks)
- 🐛 Fixed 8 P1 high-priority issues (thread safety, error handling)
- 🐛 Fixed 4 P2 medium issues (path validation, EXIF protection)
- 🐛 16 total bugs fixed from comprehensive audit

## Security
- 🔒 Device binding prevents license key sharing
- 🔒 SQL injection protection
- 🔒 Safe file deletion with confirmation
- 🔒 Offline mode doesn't bypass license checks

## System Requirements
- Windows 7, 10, or 11 (32-bit or 64-bit)
- 4GB RAM minimum (8GB recommended)
- 500MB disk space
- CPU: Intel/AMD with SSE4.2 support

## Known Limitations
- ⚠️ 100k+ images may take 45+ minutes
- ⚠️ Mobile app coming in 2027
- ⚠️ Database backup recommended before batch delete

## What's Next (v2.0.0 Mobile - 2027)
- 📱 iOS and Android native apps
- ☁️ Cloud-powered analysis (Premium)
- 🔄 Web dashboard for management

---

## Installation
Download: PhotoCleaner_v1.0.0.exe
Size: ~120MB

## Support
Email: support@photocleaner.local
Documentation: docs.photocleaner.local
```

**RC Status:**
- ✅ All tests passing
- ✅ Performance targets met
- ✅ Security audit complete
- ✅ Documentation complete
- 🔄 Ready for Phase 5 (Market Prep)

---

## Phase 4 Success Criteria

For Phase 4 to be **COMPLETE**, we need:

✅ **Testing:**
- [ ] 307 tests passing (100% pass rate)
- [ ] Code coverage ≥80%
- [ ] 0 critical/high-priority bugs remaining

✅ **Security:**
- [ ] License key validation hardened
- [ ] SQL injection audit passed
- [ ] File permission safety verified
- [ ] Offline mode integrity confirmed

✅ **Performance:**
- [ ] 1k images: <30 seconds
- [ ] 10k images: <5 minutes
- [ ] 50k images: <20 minutes
- [ ] 100k images: <45 minutes
- [ ] Memory: <1GB peak
- [ ] No memory leaks detected

✅ **Build & Release:**
- [ ] PhotoCleaner.exe created & tested
- [ ] User Manual complete (PDF + HTML)
- [ ] API documentation complete
- [ ] Release notes prepared
- [ ] v1.0.0 RC ready

✅ **Documentation:**
- [ ] All code documented
- [ ] Troubleshooting guide complete
- [ ] FAQ populated
- [ ] Contributing guidelines updated

---

## Timeline: 16 Weeks (Feb 5 - Jun 30, 2026)

```
WEEK 1-4:   STAGE 1 - Unit & Integration Testing
            Goal: Fix failing tests, 80%+ coverage

WEEK 5-7:   STAGE 2 - Security Audit
            Goal: Harden license, SQL, file handling

WEEK 8-12:  STAGE 3 - Stress & Performance Testing
            Goal: Validate 10k, 50k, 100k benchmarks

WEEK 13-16: STAGE 4 - Release Build & Documentation
            Goal: v1.0.0 RC ready for Phase 5
```

**Deliverable:** v1.0.0 Release Candidate (RC) ready for Phase 5 Market Preparation

---

## Next: START STAGE 1 Week 1 - Fix Failing Tests

**Immediate Action Items:**
1. [ ] Investigate `test_cache_size_statistics` failure
2. [ ] Fix cache query to properly count top_n entries
3. [ ] Run full test suite again
4. [ ] Generate coverage report
5. [ ] Identify modules below 80% coverage

**Status:** 🚀 READY TO BEGIN
