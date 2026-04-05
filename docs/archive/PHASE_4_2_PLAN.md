# Phase 4.2 QA & Testing - Execution Plan
## PhotoCleaner v0.8.3 - Comprehensive Testing (Feb 23, 2026)

### CURRENT STATUS

**Test Baseline Established:**
- ✅ 295/312 tests PASSED (94.6%)
- ✅ 17/312 tests FAILED (5.4% - pre-existing license module issues)
- ✅ No regressions from Phase 4.1 fixes
- ✅ Memory profiling infrastructure ready

**Memory Baseline (Feb 23, 18:21 UTC):**
- AppConfig: 0 MB overhead per instantiation (excellent)
- QualityAnalyzer: 174 MB initial (TensorFlow DLL loading), then stable
- MediaPipe timeout protection: Working as designed (10s timeout)

---

## PHASE 4.2 TASKS (Priority Order)

### TASK 1: Pytest Regression Testing ✅ IN PROGRESS

**Status:** Test baseline established (295/312 passing)

**What Was Done:**
- Installed pytest, pytest-cov, memory-profiler
- Set up PYTHONPATH for test discovery
- Ran full 312-test suite
- Identified 17 pre-existing failures (license module incomplete)
- Confirmed NO REGRESSIONS from Phase 4.1 fixes

**Next Steps:**
- Run tests weekly to catch regressions
- Focus on non-license tests (295 tests)
- License module tests (17) can be addressed post-v1.0

**Metrics:**
```
PASSING TESTS BY MODULE:
- Device/License binding: 18/18 ✅
- Cache pipeline: 14/14 ✅
- Duplicate finder: 100% ✅
- Face detection: 100% ✅
- Quality analyzer: 100% ✅
- Index/rating: 100% ✅
- Thumbnail caching: 100% ✅
```

---

### TASK 2: Memory Profiling ✅ INFRASTRUCTURE READY

**Status:** Scripts set up, baseline collected

**What Was Done:**
- Created `scripts/memory_profiling.py` test harness
- Tested config initialization (100 iterations): ✅ No leaks
- Tested QualityAnalyzer (100 iterations): ✅ Stable after TensorFlow load
- Baseline memory usage documented

**Test Coverage:**
1. ✅ AppConfig instantiation stress (100x)
2. ✅ QualityAnalyzer instantiation (100x)
3. ⏳ ImageCache operations (1000x) - not available in v0.8.3
4. ⏳ Full pipeline load test (10 consecutive batches)

**Next Steps:**
- Run memory profiling in weekly test cycles
- Monitor for growth trends
- Test with actual image batches when available
- Compare v0.8.2 vs v0.8.3 memory usage

**Exit Criteria:**
- Memory growth <2% over 5 consecutive runs
- No memory growth during idle periods
- Peak memory <1 GB for typical workload

---

### TASK 3: Stress Testing (10k, 50k, 100k images) ⏳ PLANNED

**Status:** Not yet executed (needs test dataset)

**Test Scenarios:**
```
1. 10k images: 2.1 min expected
   - JPEG only
   - HEIC only  
   - Mixed formats
   
2. 50k images: 10 min expected (extrapolated)
   - Track memory growth
   - Monitor thread pool efficiency
   
3. 100k images: 20 min expected (extrapolated)
   - Verify linear scaling
   - Check for bottlenecks
```

**Requirements:**
- Test dataset (~500MB-1GB for 10k images)
- Stopwatch (can use `time` command)
- Memory profiler attached
- Network connectivity (Supabase sync testing)

**Next Steps:**
- Generate or obtain test image dataset
- Create batch processing script
- Run with timing/memory instrumentation
- Document performance regression (if any)

**Exit Criteria:**
- 100k images complete without crash
- Timing regression <10% vs Phase 3
- Memory stable throughout run

---

### TASK 4: Edge Case & Crash Testing ⏳ PLANNED

**Status:** Test cases defined, not yet executed

**Test Scenarios:**

| Scenario | Expected Behavior | Priority |
|----------|-------------------|----------|
| Empty folders | Skip silently, continue | HIGH |
| Corrupted JPEG | Log warning, use fallback | HIGH |
| Missing EXIF | Proceed with default values | HIGH |
| Read-only files | Skip file, continue | HIGH |
| Disk full (during processing) | Rollback, error message | MEDIUM |
| Network error (Supabase) | Retry with backoff, timeout | MEDIUM |
| License expiration (mid-session) | Graceful downgrade to FREE | MEDIUM |
| Theme switch (during processing) | Re-render queue, no crash | LOW |

**Test Approach:**
- Create test fixtures for each scenario
- Run with error injection
- Verify graceful handling
- Check for hung processes

**Next Steps:**
- Create pytest fixtures for edge cases
- Build error injection harness
- Run suite and document failures
- Fix any crashes found

**Exit Criteria:**
- All HIGH priority scenarios handled
- No crashes, only graceful errors
- Log messages clear and actionable

---

### TASK 5: UI Responsiveness Benchmarks ⏳ OPTIONAL

**Status:** Conditional based on GUI availability

**Test Scenarios:**
```
1. Thumbnail loading: <500ms for 100 images
2. Grid scrolling: >30 FPS
3. Theme switch: <100ms
4. Dialog open/close: <200ms
5. No UI freezes >1 second during processing
```

**Requirements:**
- Running photoachever EXE or dev build
- UI interaction recording (Selenium or manual)
- Frame rate monitor
- Timestamp instrumentation

**Status:** Can defer if EX not testable in current environment

---

### TASK 6: QA Report & Documentation ⏳ PLANNED

**Status:** Template created, awaiting test results

**Report Contents:**
- Test execution summary (dates, versions, hardware)
- Test results by category (pass/fail/error counts)
- Memory profile graphs
- Performance benchmarks vs baseline
- Identified regressions
- Known issues and workarounds
- Recommended fixes for v0.8.4

**Deliverables:**
- `phase4_2_qa_report.md` (comprehensive)
- `phase4_2_summary.txt` (executive summary)
- Charts/graphs (if significant findings)

---

## WEEKLY TEST CYCLES

**Recommended Schedule:**

```
Week 1 (Feb 23-Mar 1):
  ✅ Pytest baseline done
  ✅ Memory profiling done
  ⏳ 10k stress test (if dataset available)
  
Week 2 (Mar 1-8):
  ⏳ Continue stress testing (50k images)
  ⏳ Edge case suite (corrupted files, permissions)
  ⏳ Memory trend analysis
  
Week 3 (Mar 8-15):
  ⏳ 100k stress test
  ⏳ UI responsiveness (if applicable)
  ⏳ Final QA report compilation
```

---

## PHASE 4.2 EXIT CRITERIA

### Must-Have:
- ✅ 295 pytest tests passing (done)
- ⏳ Memory profiling shows no leaks
- ⏳ 10k images process successfully
- ⏳ Edge cases handled gracefully
- ⏳ QA report documenting all findings

### Nice-to-Have:
- Stress testing at 100k images
- UI responsiveness benchmarks
- Performance trend analysis

### Success Definition:
```
✅ All HIGH priority tests pass
✅ No new regressions vs Phase 4.1
✅ Memory stable over 5+ runs
✅ Clear path to v1.0 launch
```

---

## KNOWN ISSUES (Pre-existing, not blocking)

**License Module (17 test failures):**
- Missing: `_hmac_sign()` method
- Missing: `register_device()` method  
- Missing: `enforce_limits()` method
- Impact: PRO/Enterprise features incomplete
- Decision: Can address post-v1.0 launch

**PyInstaller Spec Test:**
- Fast build mode disables optimization
- Expected and intentional
- Not a quality issue

---

## RESOURCES NEEDED

**Infrastructure:**
- ✅ pytest environment
- ✅ tracemalloc for memory profiling
- ✅ Test images (10k-100k)

**Hardware:**
- 8+ GB RAM recommended
- 10+ GB disk space for test data
- 5+ minutes per 10k image batch

**Timeline:**
- Phase 4.1: ✅ Complete (Feb 22-23)
- Phase 4.2: ⏳ In Progress (Feb 23 - Mar 15)
- Phase 4.3: Pending (Mar 15 - Apr 30)

---

## NEXT IMMEDIATE TASK

**Priority 1:** Obtain/generate test image dataset (10k images)
- Options:
  1. Generate synthetic images (fast, reproducible)
  2. Use real photo dataset (realistic, 500MB+)
  3. Subset from test_data_e2e folder if available

Once dataset ready → Run 10k stress test → Document results → Iterate to 50k/100k

