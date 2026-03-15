# PhotoCleaner - Roadmap 2026 (REVISITED)

**Aktualisiert:** 15. März 2026 (Execution Sync: Slice 5 abgeschlossen, Slice 6 vorbereitet, 503-Thema geparkt, MSI-Track ergänzt)  
**Status:** Phase 4.1 ✅ COMPLETE | Security P0 ✅ COMPLETE | Phase 4.2 QA Testing + P1 Refactor (Slice 6 als Nächstes)  
**Ziel:** v1.0.0 Launch im November 2026 (revised timing)  
**Timeline:** 9 Monate mit Fokus auf STABILITÄTSRISIKEN

---

## 🧭 EXECUTION-MODUS (ab 2026-03-04)

Aktive operative To-do-Liste: `docs/EXECUTION_BACKLOG_20260304.md`  
Roadmap bleibt strategisch; tägliche Abarbeitung erfolgt über das Backlog.

### Aktueller Sprintfokus (NOW)
- [ ] Secret Rotation (extern/manuell)
- [ ] Frozen-Build Smoke-Test auf 5+ clean Windows Maschinen (extern/manuell)
- [ ] P1 Slice #6: `modern_window.py` Refactoring starten (views/controllers/workflows, top-down)
- [ ] Distribution-Track starten: MSI-Installer-Konzept + erster Build-Pfad
- [ ] Supabase Licensing HTTP 503 Investigation bewusst verschoben (Parkplatz bis nach Slice 6 Start)
- [x] P1 Slice #1: License Service Adapter umgesetzt
- [x] P1 Slice #2: Progress-Workflow in `modern_window.py` über Service/Facade entkoppelt
- [x] Lizenz-/Activation-Regression-Checks ergänzt (7 gezielte Unit-Tests grün)
- [x] `quality_analyzer` Submodul-Split Slice 1: Datenmodelle nach `pipeline/analysis/models.py` extrahiert (36 fokussierte Tests grün)
- [x] `quality_analyzer` Submodul-Split Slice 2: Face-Detection nach `pipeline/analysis/face_detector.py` extrahiert (36 fokussierte Tests grün)
- [x] `quality_analyzer` Submodul-Split Slice 3: Scoring-Logik nach `pipeline/analysis/quality_scorer.py` extrahiert (36 fokussierte Tests grün)
- [x] `quality_analyzer` Submodul-Split Slice 4: EXIF/Metadata-Logik nach `pipeline/analysis/exif_extractor.py` extrahiert (36 fokussierte Tests grün)

---

## ✅ STATUS-UPDATE MÄRZ 2026 (Execution Sync)

### Neu abgeschlossen seit letztem Update
- [x] **Website-Struktur bereinigt:** Alle Root-HTML-Seiten nach `website/` verschoben, Asset-Pfade korrigiert
- [x] **P0 Security Hardening (Secrets):** Hardcoded Supabase-Fallbacks aus Runtime entfernt (`license_manager.py`, `license_dialog.py`)
- [x] **Repository-Hygiene:** `.env` aus Tracking entfernt, `.env.example` ergänzt, `.gitignore` gehärtet
- [x] **Guardrails:** CI Secret-Scan Workflow + lokale Pre-Commit Secret-Scans ergänzt
- [x] **Dokumentation bereinigt:** Sensitive Beispiele in Guides auf Platzhalter umgestellt
- [x] **P1 Maintainability Slice #1:** Cloud-Lizenz-Config/Activation-Logik in Service-Layer zentralisiert (`services/license_service.py`)
- [x] **P1 Architecture Slice #2:** Progress-Workflow UI→Service Adapter in `modern_window.py`
- [x] **P1 Quality Analyzer Slice #1:** DatenModelle extrahiert → `pipeline/analysis/models.py` (4 classes, reusable)
- [x] **P1 Quality Analyzer Slice #2:** Face Detection extrahiert → `pipeline/analysis/face_detector.py` (1,238 lines, FaceDetector class)
- [x] **P1 Quality Analyzer Slice #3:** Scoring Logik extrahiert → `pipeline/analysis/quality_scorer.py` (18+ methods, 660 lines)
- [x] **P1 Quality Analyzer Slice #4:** EXIF/Metadata extrahiert → `pipeline/analysis/exif_extractor.py` (ExifExtractor + Wrapper-Kompatibilität)

### Offene kritische Punkte (extern/manuell)
- [ ] **Secret Rotation durchführen:** Bereits exponierte Supabase Keys sofort rotieren (außerhalb Repo)
- [ ] **Frozen-Build Smoke-Test auf 5+ Clean Windows Maschinen** final abschließen

### Geparkte Themen (bewusst verschoben)
- [ ] **Supabase Licensing HTTP 503 / Exchange-Stabilität**
   - Status: bewusst auf später verschoben, damit der Top-Down-Roadmap-Flow nicht unterbrochen wird
   - Re-Entry: direkt nach erstem Slice-6-Paket (views/controllers/workflows)
   - Scope bei Wiederaufnahme: Edge-Function-Retry/Timeouts, DB/Policy-Diagnostik, Monitoring/Alerts

### Nächste Ziele (März, priorisiert)
1. **Sprint 1 sauber schließen (Backlog NOW):** Secret rotation + 5x clean-machine smoke-tests
2. **P1 Architektur top-down weiterführen:** Slice 6 in `modern_window.py` starten und in kleine testbare Mini-Slices schneiden
3. **Vertrauenswürdiger Release-Kanal:** MSI-Installer als zusätzliches Auslieferungsziel vorbereiten
4. **Danach Re-Entry geparkter Cloud-Themen:** HTTP 503/Supabase root-cause sprint

### Architektur-Refactoring Roadmap (Quality Analyzer Slices)
- [x] **Slice 1 (COMPLETE):** Data Models extraction → `pipeline/analysis/models.py`
- [x] **Slice 2 (COMPLETE):** Face Detection extraction → `pipeline/analysis/face_detector.py` (1,238 lines)
- [x] **Slice 3 (COMPLETE):** Scoring Logic extraction → `pipeline/analysis/quality_scorer.py` (18+ methods, 730 lines)
- [x] **Slice 4 (COMPLETE):** EXIF/Metadata extraction → `pipeline/analysis/exif_extractor.py`
- [x] **Slice 5 (COMPLETE):** remaining QualityAnalyzer compression abgeschlossen
- [ ] **Slice 6 (NEXT):** `modern_window.py` Refactoring starten (views/controllers/workflows)

#### Slice 6 Startplan (ab 2026-03-15)
- [x] 6.1: Workflow-Seams in `modern_window.py` markieren (Import, Rating, Selection, Dialog-Trigger)
- [x] 6.2: Ersten Controller-Extraktionspfad definieren (ohne UX-Änderung)
- [x] 6.3: Mini-Slice implementieren + fokussierte Regression-Tests
- [x] 6.4: Zweiten Mini-Slice implementieren (Rating-Workflow-Controller) und dokumentieren
- [ ] 6.5: Nächsten Mini-Slice planen (Selection-/Dialog-Workflow) und technische Schulden dokumentieren

#### Slice 6 Progress (2026-03-15)
- [x] Mini-slice 6.1: Workflow-Seams identifiziert (Indexing + Post-Indexing als erster Extraktionskandidat)
- [x] Mini-slice 6.2: Erster Workflow-Controller extrahiert → `ui/workflows/indexing_workflow_controller.py`
- [x] Mini-slice 6.2: `modern_window.py` delegiert Dialog- und Thread-Wiring für Indexing/Post-Indexing an Controller (ohne UX-Änderung)
- [x] Mini-slice 6.3: Fokussierte Regression-Tests ergänzt → `tests/unit/test_indexing_workflow_controller.py` (3/3 grün)
- [x] Mini-slice 6.4: Zweiter Workflow-Controller extrahiert → `ui/workflows/rating_workflow_controller.py`
- [x] Mini-slice 6.4: `modern_window.py` delegiert Rating-Thread-Wiring + Start/Dialog-Event-Flush an Controller (ohne UX-Änderung)
- [x] Validierung: Workflow-Controller fokussiert 6/6 Tests grün (`test_indexing_workflow_controller.py` + `test_rating_workflow_controller.py`)

#### Slice 5 Progress (2026-03-12)
- [x] Mini-slice 5.1: Haar cascade resolver in eigenes Modul extrahiert → `pipeline/analysis/haar_cascade_resolver.py`
- [x] Mini-slice 5.1: Doppelte Haar-Cascade-Initialisierung aus `quality_analyzer.py` entfernt (Single Source in `FaceDetector`)
- [x] Mini-slice 5.2: Face-Mesh-Resolver nach `pipeline/analysis/face_mesh_resolver.py` extrahiert und `face_detector.py` vom `quality_analyzer`-Import entkoppelt
- [x] Mini-slice 5.3: Veraltete lokale Face-Mesh-States/Wrapper aus `quality_analyzer.py` entfernt (nach Resolver-Extraktion)
- [x] Mini-slice 5.4: Lokale Face-Mesh-Cache/Config-Hash-Reste aus `quality_analyzer.py` entfernt; `warmup()` auf `FaceDetector`-Preload umgestellt
- [x] Mini-slice 5.5 (größer): Bild-Lade-/Downsampling-Block aus `analyze_image()` nach `pipeline/analysis/image_preprocessor.py` extrahiert und integriert
- [x] Mini-slice 5.6 (größer): EXIF/Orientation/Metadaten-Block aus `analyze_image()` nach `pipeline/analysis/metadata_enricher.py` extrahiert und integriert
- [x] Mini-slice 5.7 (größer): Core-Execution-Block (Gray/Scoring/Face/Total) aus `analyze_image()` nach `pipeline/analysis/analysis_executor.py` extrahiert
- [x] Mini-slice 5.8 (größer): `analyze_batch()`-Orchestrierung nach `pipeline/analysis/batch_runner.py` extrahiert und in `QualityAnalyzer` integriert
- [x] Mini-slice 5.9 (größer): Runtime-Dependency-Bootstrap/Lazy-Import-Logik nach `pipeline/analysis/runtime_dependencies.py` extrahiert
- [x] Mini-slice 5.10 (größer): Eye-Stage-/Capability-Resolver nach `pipeline/analysis/capability_resolver.py` extrahiert und in `QualityAnalyzer` verdrahtet
- [x] Validierung: 36/36 fokussierte Analyzer-Tests grün

#### Slice 4 Details: EXIF & Metadata Extractor
**Ziel:** Extrahiere EXIF-Parsing und Metadaten-Logik in dediziertes Modul
**Scope:** ~300-400 Zeilen aus quality_analyzer.py
**Expected Extraction Methods:**
- `_get_exif_orientation_from_pil()` - EXIF-Orientierungsdaten
- `_extract_exif_data_from_pil()` - Umfassende EXIF-Extraktion  
- `_rotate_image_from_exif()` - Bildrotation basierend auf EXIF
- `CameraProfile.extract_camera_model()` - Kamera-Modell-Erkennung
- Helper methods für ISO, Aperture, Focal Length, Exposure Time parsing

**Dependencies:** PIL/Pillow, numpy (optional)
**Integration:** QualityAnalyzer delegiert zu ExifExtractor für all EXIF-Operationen

**Exit Criteria:**
- ✅ 36/36 focused tests passing
- ✅ quality_analyzer.py weitere ~350 Zeilen reduziert
- ✅ ExifExtractor vollständig dokumentiert
- ✅ Lazy-Loading von PIL unterstützt

**Status:** ✅ Complete (2026-03-12) – implemented, integrated, validated with 36/36 focused tests

---

## 🚨 KRITISCHE ÄNDERUNGEN SEIT 7. FEB

### Neue Blockers (Nicht in ursprünglicher Roadmap)
1. **MediaPipe-Import Freeze (30s)** in frozen builds
   - Root cause: TensorFlow GPU enumeration + Windows Defender
   - Fix: Thread-Timeout (10s) + CUDA_VISIBLE_DEVICES=-1
   - Status: **Implementiert, NICHT YET VALIDIERT auf echtem Windows**

2. **PyInstaller Build-Warnungen** (Unterschätzt)
   - numpy.core._dtype_like not found
   - photo_cleaner data collection failing
   - pkg_resources._vendor.jaraco not found
   - Gelöst aber noch nicht auf sauberer Maschine getestet

3. **Frozen Build Smoke-Test NICHT DURCHGEFÜHRT**
   - Wir haben EXE gebaut, aber:
   - Nicht auf echter Windows 10/11 Machine getestet
   - Nicht auf Test-Maschine ohne dev environment getestet
   - Nicht auf Maschine ohne Python getestet
   - **KRITISCHES RISIKO:** EXE könnte total brechen auf Target-Plattform

4. **Config-Hash Initialisierung** könnte auch blockieren
   - hashlib.md5() in __init__ - sollte fast instant sein
   - Aber: Wenn AppConfig locked - könnte deadlock sein
   - Änderung: Try/except mit exc_info hinzugefügt

5. **Threading-Safety nicht vollständig überprüft**
   - _deps_lock ist da
   - _mtcnn_infer_lock ist da
   - Aber: Race conditions in frozen build unter Last nicht getestet
   - MediaPipe cache bei gleichzeitiger Nutzung?

### Was war optimistisch in alter Roadmap
- ❌ "DLL-Init in EXE auf manchen Systemen (Debugging via Logfile)" → War BLOCKIEREND, nicht einfach debugging
- ❌ "Oktober Launch realistisch" → Zu aggressiv, neue Risiken identifiziert
- ❌ "Phase 4 = 16 Wochen QA" → Unterschätzt Frozen-Build Komplexität
- ❌ "Keine neue Features vor v1.0" → Gut, aber nicht genug Testing geplant
- ❌ "Phase 4B Mobile" → Zu früh geplant für 15-Jährigen, erst v2.x

---

## 📊 REALISTISCHER STAND (Feb 22, 2026)

**Version 0.8.3:** State Machines fixed, Frozen-Build validation pending
**Dev-Build:** Läuft ohne Probleme ✅
**Frozen-Build (EXE):** State machine bugs fixed, ready for validation testing 🟡

**Confirmed Status:**
- ✅ Phase 2 complete (Performance 9.19x)
- ✅ Phase 3 complete (Algorithmen)
- � Phase 4.1 **CRITICAL** → State Machines fixed, Frozen-Build validation pending
  - ✅ MTCNN warning paradox FIXED (Feb 22)
  - ✅ MediaPipe warning logic FIXED (Feb 22)
  - ✅ RatingWorkerThread MTCNN validation FIXED (Feb 22)
  - ⏳ Still pending: Frozen-build validation on 5+ Windows machines
- ⏸️ Phase 4.2+ → Warten auf 4.1 frozen-build validation

---

## 🚀 NEUE PHASE STRUKTUR (Sequenziell, nicht parallel)

### PHASE 4.1: FROZEN-BUILD STABILIZATION (Feb 22 - Mar 15)
**KRITISCHER BLOCKER FÜR LAUNCH** | Est. 3-4 Wochen

#### Zi lele
- [ ] EXE läuft auf echtem Windows ohne Dev-Setup
- [ ] MediaPipe-Import blockiert max 10s (timeout greifen)
- [ ] Alle Model-Loading-Operationen haben Fallbacks
- [ ] Zero Hangs/Freezes bei normaler Nutzung
- [ ] Smoke-test auf 5+ unterschiedlichen Windows-Maschinen

#### Kritische Aufgaben
1. **MediaPipe Thread-Timeout validieren**
   - [ ] Baui & deploy mit timeout-fix
   - [ ] Test auf 3 verschiedenen Windows-Systemen
   - [ ] Varianten: Mit/ohne internet, mit/ohne dedicated GPU
   - [ ] Fallback zu MTCNN-only sollte funktionieren
   - [ ] Log-Ausgabe sollte klar sein wenn Timeout

2. **MTCNN State Machine & Initialization Fixes** (Feb 22, 2026)
   - [x] Fix MTCNN fallback warning shown prematurely
     - Problem: Warning displayed before splash-phase re-init
     - Solution: Defer warning until after retry loop
     - Status: MERGED
   - [x] Fix MediaPipe warning shown incorrectly
     - Problem: Warning on every startup even when not requested
     - Solution: Only warn when requested AND actually failed
     - Status: MERGED
   - [x] Fix RatingWorkerThread MTCNN validation
     - Problem: Clustering started without MTCNN readiness check
     - Solution: Validate MTCNN at thread start, early exit if unavailable
     - Status: MERGED & TESTED
   - Files: run_ui.py, quality_analyzer.py, modern_window.py
   - Impact: Clean logs without false warnings, correct grouping behavior

3. **Import → Rating Pipeline Reliability Fixes** (Feb 22, 2026 Evening - Critical Bug-Hunt)
   - [x] Fix RatingWorkerThread MTCNN validation **TOO STRICT**
     - Problem: Rating aborted completely if MTCNN unavailable
     - Root Cause: Forgot about Haar Cascade fallback in QualityAnalyzer
     - Solution: Changed to informational logging only; rating continues with fallback
     - Impact: **One-click import now works reliably** - no need to restart multiple times
     - Status: MERGED & TESTED
    - [x] Fix Gruppen nicht sichtbar nach Duplicate Finder
       - Problem: Gruppen wurden nach der Duplikat-Suche nicht gerendert
       - Root Cause: `refresh_groups()` fehlte vor Rating-Start
       - Solution: Gruppen sofort nach Duplicate Finder rendern
       - Impact: Gruppen sofort sichtbar, klarer Workflow
       - Status: MERGED & TESTED
    - [x] Fix Thumbnail Loading race mit Rating Progress
       - Problem: Progress-Dialog sprang zwischen "Bilder werden geladen" und "Bilder werden bewertet"
       - Root Cause: ThumbnailLoader lief waehrend Post-Indexing
       - Solution: Loader pausieren waehrend Analyse, erst nach Rating fortsetzen
       - Impact: Sequenzieller Flow, keine Progress-Flackern
       - Status: MERGED & TESTED
   - [x] Fix Missing FileRepository import
     - Problem: NameError crash in RatingWorkerThread.run()
     - Solution: Added missing imports (FileRepository, sqlite3)
     - Impact: Worker no longer crashes on rating start
     - Status: MERGED & TESTED
   - [x] Fix Insufficient Exception Handling
     - Problem: Only caught sqlite3 exceptions; others crash worker silently
     - Solution: Changed to `except Exception` with full traceback logging
     - Impact: All failures visible; UI always responsive (never hangs)
     - Status: MERGED & TESTED
   - Files: modern_window.py (RatingWorkerThread.run())
   - **Summary**: **Complete pipeline now deterministic** - Groups sichtbar nach Duplicate Finder, Rating dann Thumbnails (ONE click)
   - **User Impact**: Before: Had to click 2-3 times to get rating. After: Works first time, every time

4. **Internationalization (i18n) Improvements** (Feb 23, 2026)
   - [x] Complete License Dialog i18n
     - Added 39 new translation keys (DE + EN)
     - Replaced all hardcoded German strings in license_dialog.py
     - Includes: labels, info texts, QMessageBox messages, feature comparison table
     - Strategy: Full HTML blocks for complex structures (maintainability)
     - Impact: License dialog fully bilingual, ready for international users
     - Status: MERGED & TESTED
   - [x] Complete Selection/Comparison UI i18n
     - Added 17 new translation keys (DE + EN)
     - Replaced hardcoded strings in modern_window.py (selection state, comparison, errors)
     - Includes: selection count messages, compare button variants, error messages
     - Impact: Main window selection UI fully internationalized
     - Status: MERGED & TESTED
   - [x] Git Repository Cleanup
     - Problem: 3 large ZIP files (422 MB each) blocked push for 42 commits
     - Solution: Created orphan branch, consolidated commits, force-pushed clean history
     - Impact: Repository clean, all 42 commits successfully synced to GitHub
     - Status: RESOLVED
   - Files: i18n.py, license_dialog.py, modern_window.py
   - **User Impact**: Software now properly supports English language for international adoption

5. **Config-Hash-Deadlock diagnostizieren**
    - [x] Code-Review: _init_config_hash() kann blockieren?
       - Ergebnis: Kein Locking in AppConfig; _init_config_hash nur md5 auf kleinen Strings
       - Hinweis: AppConfig.get_mode() triggert Logging-Setup + mkdir (I/O), kein Deadlock erkennbar
    - [x] Test: 100x QualityAnalyzer creation im Loop
       - Script: scripts/test_config_hash_deadlock.py
       - Ergebnis: 100/100 OK, 2.68s, kein Hang
    - [x] Parallel-Load Test: 10 threads gleichzeitig
       - Script: scripts/test_config_hash_deadlock.py
       - Ergebnis: 10 Threads x10 OK, 0.06s, kein Hang
   - [ ] Wenn blockiert: Verschiebe init zu lazy-loading
    - Nebenbefund: Haar cascade directory not found (Fallback disabled) + TensorFlow oneDNN Hinweis

6. **Haar-Cascade Finder robuster machen**
    - [x] Test auf echtem onedir build
       - Lokal onedir build: 17 haarcascade_*.xml in dist/PhotoCleaner/_internal/cv2/data ✅
       - Bundled successfully via PyInstaller spec (corrected cv2/data path)
   - [x] 5 verschiedene Pfade checken (CV2-data, app-dir, _internal, glob-search)
     - Added env override: PHOTOCLEANER_HAAR_CASCADE_DIR / OPENCV_HAAR_CASCADE_DIR
     - Added module_dir parent fallback and caching to avoid repeated scans
     - **Fixed resolver:** Now correctly finds cascades at sys._MEIPASS/cv2/data (frozen build)
   - [x] Fallback funktioniert wenn cascades nicht found
       - Ergebnis: Resolver now returns correct path when cascades bundled; MTCNN+Haar fallback enabled
   - [x] Log clear: "Haar cascades found at X" oder "Haar cascade directory not found; face fallback disabled"
   - **Status:** ✅ COMPLETE - Frozen build now has working face detection fallback

7. **TensorFlow GPU-Check eindämmen**
   - [x] CUDA_VISIBLE_DEVICES=-1 in run_ui.py
   - [x] Test: GPU-Enumeration sollte <2s sein
     - Ergebnis: TF import 2.51s (CUDA_VISIBLE_DEVICES=-1) -> knapp drüber
   - [x] Log: "TensorFlow CPU-only mode enabled" klar sichtbar

8. **Smoke-Test Protocol (für alle Änderungen)**
   ```
   Procedure:
   1. Build mit .\build.bat fast clean
   2. Starte dist/PhotoCleaner/PhotoCleaner.exe auf sauberer Windows-VM
   3. Import 20 bilder
   4. Check Logs for: [INIT], [DEPS], [WARMUP] markers
   5. Submit report mit timestamps + any errors
   ```
   - Helper: scripts/smoke_test_protocol.py (prints checklist + EXE path check)
   - Build (fast clean) erfolgreich; EXE gefunden in dist/PhotoCleaner/PhotoCleaner.exe
   - Noch offen: Ausführung auf sauberer Windows-VM + Log-Check

9. **Debug-Log Settings für Frozen-Build**
    - [x] Env-Var: PHOTOCLEANER_DEBUG=1 für verbose logs
       - AppConfig.get_mode honors PHOTOCLEANER_DEBUG=1
    - [x] Logs always to file (%APPDATA%\PhotoCleaner\PhotoCleaner.log)
       - Implemented in AppConfig._setup_logging (file handler)
    - [x] Console-logging minimiert (frozen GUI shouldn't output)
       - Release mode logs warnings only; run_ui guards stdout/stderr in frozen

#### Exit Criteria
- ✅ EXE startet ohne Crash auf 5 verschiedenen Windows 10/11 PCs
- ✅ Model-loading blockiert max 10s
- ✅ Logs zeigen klare progression ([DEPS] → [INIT] → [WARMUP] → ready)
- ✅ Fallbacks funktionieren (MTCNN nur, Haar-fallback wenn nötig)
- ✅ Keine unerwarteten Hangs bei 100+ Bilder indexing

#### PHASE 4.1 COMPLETION STATUS ✅
**23. Februar 2026 19:30 - ALL TASKS CODE-COMPLETE**

**Completed Tasks:**
- ✅ Task 1-4: i18n (39 License keys + 17 Selection UI keys) + Git cleanup
- ✅ Task 5: Config-Hash diagnostics (stress test: 100x OK, 10 threads OK)
- ✅ Task 6: Haar-Cascade bundling FIXED
  - 17 Haar XMLs bundled in dist/PhotoCleaner/_internal/cv2/data
  - Resolver finds cascades in frozen build context
  - Face fallback (MTCNN+Haar) now functional
- ✅ Task 7: TensorFlow CPU-only (CUDA_VISIBLE_DEVICES=-1, 2.51s import)
- ✅ Task 8-9: Smoke-test protocol + Debug logs (PHOTOCLEANER_DEBUG=1)

**Build Status:**
- ✅ Fast clean build: SUCCESS at 19:30 UTC
- ✅ EXE generated: dist\PhotoCleaner\PhotoCleaner.exe
- ✅ All 310 tests ready for Phase 4.2

**Pending (Manual/External Steps):**
- ⏳ Smoke-test execution on 5+ clean Windows VMs (user task - can defer)

**Next Phase:** Phase 4.2 QA & Testing (Pytest suite, stress testing 100k images, memory profiling)

#### Deliverable
- v0.8.3 build mit allen Stabilisierungs-Fixes ✅
- Smoke-test protocol ready (manual execution pending)
- Updated architecture documentation (Haar cascade + TensorFlow CPU-only)

---

### PHASE 4.2: COMPREHENSIVE QA & TESTING (Mar 15 - Apr 15)
**Nach 4.1 erfolgreich** | Est. 4 Wochen

#### Ziele
- [ ] 100k bilder processing ohne memory leaks
- [ ] Zero crashes unter Last
- [ ] UI responsiveness auch bei großen batches
- [ ] Exception handling auf allen code paths

#### Aufgaben
1. **Pytest Suite Stabilität**
   - [ ] All 310 tests auf frozen-build geist (nicht nur dev env)
   - [ ] Memory profiling: Kein memory growth über 5 runs
   - [ ] Thread-safety: Concurrent test runners ohne race conditions
   - [ ] Timeout protections auf allen I/O operations

2. **Stress-Testing (neue Datasets)**
   - [ ] 10k images: 2.1 min expected, check for regressions
   - [ ] 50k images: Extrapolated 10min, track memory
   - [ ] 100k images: Extrapolated 20min, check if scaling linear
   - [ ] Varianten: JPEG only, HEIC only, mix, corrupted files

3. **Crash-Testing (Edge Cases)**
   - [ ] Empty folders
   - [ ] Corrupted HEIC/JPEG
   - [ ] Missing EXIF data
   - [ ] File permission errors (read-only)
   - [ ] Disk full during processing
   - [ ] Network interruption (Supabase requests)
   - [ ] License expiration during session
   - [ ] Theme switching while processing

4. **Memory-Leak Detection**
   - [ ] TraceMemorySample Profiling (python -m tracemalloc)
   - [ ] GarbageCollector tracking
   - [ ] Model caches: MediaPipe/MTCNN should not grow
   - [ ] File handles: All opened files should close
   - [ ] Database connections: Pool shouldn't leak

5. **UI Responsiveness Benchmarks**
   - [ ] Thumbnail loading: <500ms for 100 images
   - [ ] Grid scrolling: >30 FPS
   - [ ] Theme switch: <100ms
   - [ ] Dialog open/close: <200ms
   - [ ] No freezes > 1 second during processing

#### Exit Criteria
- ✅ 310 pytest all green
- ✅ 100k images complete successfully
- ✅ Zero memory growth over 10 runs
- ✅ All edge cases handled gracefully
- ✅ UI never freezes >1s

#### Deliverable
- v0.8.4 build (bug fixes from stress-testing)
- QA report (test coverage, edge cases)
- Performance benchmark report

---

### PHASE 4.3: PERFORMANCE REGRESSION TESTING (Apr 15 - Apr 30)
**Sicherstellen dass Stabilisierungs-Fixes keine Regression verursacht** | Est. 2 Wochen

#### Ziele
- [ ] Keine Performance-Regression gegenüber v0.7.0 baseline
- [ ] Model-loading nicht langsamer als 10s
- [ ] Batch processing nicht slower als 25ms/image

#### Aufgaben
1. **Baseline Comparison**
   - [ ] Create v0.8.2 baseline (before 4.1 fixes)
   - [ ] Create v0.8.4 baseline (after all fixes)
   - [ ] Run same 5k image dataset
   - [ ] Compare: Gesamtzeit, per-stage times, memory

2. **ThreadPool Benchmarking in Frozen Build**
   - [ ] Confirm 4 workers optimal (not 8, not 2)
   - [ ] Check: Thread creation overhead in frozen build
   - [ ] Validate: No deadlocks under concurrent load
   - [ ] Test: Worker thread exceptions don't crash

3. **Model-Loading Times**
   - [ ] MTCNN initialization: Target <10s (mit timeout-fallback)
   - [ ] MediaPipe initialization: Target <10s (mit timeout)
   - [ ] Haar-Cascade loading: Target <500ms
   - [ ] Total warmup(): Target <20s

#### Exit Criteria
- ✅ Keine Regression >5% gegenüber v0.7.0
- ✅ Model-loading durchschnitt <10s
- ✅ Alle baselines dokumentiert

#### Deliverable
- Performance benchmark report (v0.7.0 vs v0.8.4)
- Optimization recommendations for v1.1

---

### PHASE 4.4: LAUNCH PREPARATION (May 1 - May 15)
**Nach allen Tests grün** | Est. 2 Wochen

#### Ziele
- [ ] Final v1.0.0 build ready
- [ ] Installation procedure tested
- [ ] Release notes + known issues documented
- [ ] Support infrastructure ready

#### Aufgaben
1. **Final Build & Versioning**
   - [ ] Update version to 1.0.0
   - [ ] Tag repository: v1.0.0-rc1
   - [ ] Final test build
   - [ ] Sign EXE (if applicable)

2. **Installation Testing**
   - [ ] MSI-Installer bauen (primärer Installer-Track für mehr Trust)
   - [ ] Tooling-Entscheidung festziehen (WiX Toolset vs Inno Setup) + reproduzierbarer Build-Command
   - [ ] Test installer on virgin Windows 10
   - [ ] Test installer on virgin Windows 11
   - [ ] Test upgrade from v0.8.x to v1.0.0
   - [ ] Test uninstall/reinstall

3. **Documentation Finalization**
   - [ ] User manual (complete, all features)
   - [ ] Troubleshooting guide (common issues)
   - [ ] FAQ (most common q's)
   - [ ] Known issues (if any)
   - [ ] System requirements (Windows version, minimum specs)
   - [ ] Release notes (what changed since v0.8.2)

4. **Support Setup**
   - [ ] Email support template
   - [ ] Bug reporting form
   - [ ] Feature request process
   - [ ] FAQ system

5. **Business Readiness**
   - [ ] Stripe ready (credentials, webhook endpoints live)
   - [ ] Supabase ready (database, edge functions, monitoring)
   - [ ] License generation tested (offline + online)
   - [ ] License validation tested on locked machine
   - [ ] Payment processing full flow tested

#### Exit Criteria
- ✅ v1.0.0 builds without warnings/errors
- ✅ Installation successful on 2 fresh machines
- ✅ Documentation complete
- ✅ Support systems operational

#### Deliverable
- v1.0.0-final build
- Installation guide
- Complete documentation
- Known issues list (if any)

---

## 🎯 FEATURE PRIORITIZATION: v1.0 vs v1.1+ (Feb 22, 2026)

Based on user feedback & pragmatic portfolio analysis.

### v1.0 LAUNCH FEATURES (Critical Path)
**Status:** Planned, to-be-implemented with v1.0

#### 🎯 **MUST-HAVE (High Value, Low Effort)**

1. **Explainable Selection Scores** ⭐⭐⭐
   - User sees: "Sharpness=0.82, Eye-Quality=0.94, Lighting=0.78 → **Recommended**"
   - Builds trust in automated selection
   - Effort: 1-2 days (UI update in detail panel)
   - Impact: Massively improves confidence in auto-rating

2. **Batch Metadata Editor (EXIF/IPTC/XMP)** ⭐⭐⭐
   - Bulk-update: Copyright, Date, Keywords, Location
   - Use case: "Apply Copyright 2026 to all conference photos"
   - Effort: 3-5 days (Dialog + batch worker thread)
   - Impact: Power user feature, good feedback signal

3. **Keyboard Shortcuts & Accessibility** ⭐⭐
   - Fast workflows for power users (Tab navigation, Enter to confirm)
   - Screen reader support (WCAG basic compliance)
   - Effort: 1-2 days (shortcuts configuration + Qt accessible API)
   - Impact: Professional tooling feel

4. **Fallback Mechanisms for ML Models** ⭐⭐
   - Status: ✅ Already implemented (Haar Cascade fallback, MTCNN optional)
   - No additional work needed

#### 📌 **SHOULD-HAVE (Important but can defer to v1.1)**
- [ ] Undo/Redo with version history (2-3 weeks, important for safety)
- [ ] Enhanced logging for troubleshooting (1 week)
- [ ] Better error messages & user guidance (3-5 days)

#### ❌ **OUT OF SCOPE for v1.0**
- Non-destructive editing (Image editing = separate tool scope)
- Plugin API (Security/versioning complexity)
- Cloud sync & mobile apps (Privacy/scope creep)
- RAW format support (Complex, defer to v1.2 if demand)

---

### v1.1 ROADMAP (High-Priority, 2-3 months after v1.0)
**Status:** Planned for June-August 2026

#### 🚀 **GAME-CHANGERS (High Value, Worth the Effort)**

1. **Folder Watcher + Incremental Indexing** ⭐⭐⭐
   - Problem: Re-scanning 50k images takes 5+ minutes every time
   - Solution: Watch folder for new/moved files, only re-index delta
   - Effort: 2-3 weeks (async file watcher, DB delta logic)
   - Impact: Game-changer for large libraries (1000+ images daily)
   - Technical: Use `watchdog` library + debounce logic

2. **Burst/Keyframe Automatic Selection** ⭐⭐⭐
   - Problem: Photographers take 10+ shots per scene, want best frame auto-selected
   - Solution: Detect burst sequences by timestamp/similarity, auto-select best
   - Effort: 1-2 weeks (temporal clustering + scoring)
   - Impact: Solves ~50% of duplicate problem for photographers
   - Technical: Group by timestamp + facial/sharpness scoring

3. **Undo/Redo + Version History** ⭐⭐
   - Problem: User marks 500 images for deletion, realizes mistake
   - Solution: Maintain transaction log, allow point-in-time restore
   - Effort: 2-3 weeks (DB redesign for undo log)
   - Impact: Safety feature, reduces user anxiety

4. **Advanced Deduplication Across Formats** ⭐⭐
   - Problem: Same image as JPEG + HEIC + RAW counted as 3 duplicates
   - Solution: Flag format variants, group intelligently
   - Effort: 1-2 weeks (perceptual hashing improvement)
   - Impact: Better grouping for mixed-format libraries

5. **Export Presets & Filename Templates** ⭐⭐
   - Problem: User wants batch export with custom naming (IMG_{date}_{sequence}.jpg)
   - Solution: Configurable export profiles + template engine
   - Effort: 1 week (UI + template processor)
   - Impact: Good for workflow automation

6. **Audit Logs & Secure Deletion** ⭐⭐
   - Problem: Enterprise users need compliance trail (DSGVO)
   - Solution: Log all deletions with timestamp/user, send2trash integration
   - Effort: 1 week (logging + send2trash setup)
   - Impact: Essential for enterprise tier

#### 📌 **NICE-TO-HAVE (Lower Priority)**
- [ ] Photo similarity graph visualization (interesting but niche)
- [ ] Temporal event grouping (cool feature, low demand)
- [ ] iOS/Android mobile reviewer (separate product line)
- [ ] Database fallback to PostgreSQL (v2.0 when scaling)

---

### v1.2+ ROADMAP (Growth Features, Late 2026+)
**Status:** Proposed for future consideration

- 🔮 **RAW Format Support** (CR2, NEF, ARW, DNG) — If photographer feedback strong
- 🔮 **AI Auto-Tagging with Taxonomy** — If user demand clear
- 🔮 **Cloud Sync with End-to-End Encryption** — If SaaS planned
- 🔮 **Mobile Companion App** — Separate product, separate team
- 🔮 **Photo Similarity Graph UI** — Cool but niche demand
- 🔮 **Automated Image Enhancement** (spot removal, smart crop) — Separate tool scope

---

### DECISION SUMMARY (v1.0 Launch Strategy)

| Feature | Scope | Priority | v1.0 | v1.1 | v1.2+ | Effort |
|---------|-------|----------|------|------|-------|--------|
| **Explainable Scores** | Core | ⭐⭐⭐ | ✅ | - | - | 1-2d |
| **Batch Metadata** | Core | ⭐⭐ | ✅ | - | - | 3-5d |
| **Keyboard Shortcuts** | UX | ⭐⭐ | ✅ | - | - | 1-2d |
| **Folder Watcher** | Feature | ⭐⭐⭐ | ❌ | ✅ | - | 2-3w |
| **Burst Detection** | Feature | ⭐⭐⭐ | ❌ | ✅ | - | 1-2w |
| **Undo/History** | Safety | ⭐⭐ | ❌ | ✅ | - | 2-3w |
| **RAW Support** | Feature | ⭐⭐ | ❌ | ❌ | ✅ | 4-6w |
| **Plugin API** | Dev | ❌ | ❌ | ❌ | ? | ∞ (risk) |
| **Cloud Sync** | Infra | ❌ | ❌ | ❌ | ? | ∞ (risk) |

**Conclusion:** v1.0 focus on **trust-building features** (explainable scores, reliability). v1.1 focus on **real photographer problems** (burst detection, incremental indexing).

---

### PHASE 5: LAUNCH & POST-LAUNCH (Jun 1 - Oct 1)
**Only if Phase 4 fully green** | Est. 4 months

#### Jun 1-15: Soft Launch (Beta)
- [ ] Release to closed beta group (20-50 users)
- [ ] Collect feedback & bug reports
- [ ] Fix critical bugs (v1.0.1, v1.0.2)
- [ ] Monitor stability

#### Jul 1-31: Business Setup
- [ ] Gewerbe anmelden (legal requirement at 16)
- [ ] Geschäftskonto eröffnen
- [ ] Stripe live enablement
- [ ] Supabase monitoring + alerts setup
- [ ] Support infrastructure go-live

#### Aug 1-31: Marketing Preparation
- [ ] Finalize pricing (€59 PRO, €199 ENTERPRISE)
- [ ] Create landing page
- [ ] Prepare press kit
- [ ] Draft announcement email
- [ ] Setup social media posts

#### Sep 1-30: Final Preparation
- [ ] Public beta (wider group)
- [ ] Final UI polish
- [ ] Security audit (penetration testing)
- [ ] Performance validation on target hardware
- [ ] Customer support hiring/setup

#### Oct 1: 🚀 LAUNCH DAY
- Birthday + Gewerbe-Registration + v1.0.0 Official Release
- Go live with Stripe payments
- Announce to public
- First paying customers possible

#### Oct 2-31: Post-Launch
- [ ] Production monitoring
- [ ] Customer support live
- [ ] Hotfix releases (v1.0.3, etc.) as needed
- [ ] Gather customer feedback
- [ ] Plan v1.1 roadmap

---

## ⚠️ KRITISCHE RISIKEN & MITIGATION

| Risiko | Impact | Wahrscheinlichkeit | Mitigation |
|--------|--------|-------------------|-----------|
| **MediaPipe Thread-Timeout funktioniert nicht** | Frozen-Build unbenutzbar | HIGH (50%) | **Sofort testen auf echtem Windows** |
| **Config-Hash blockiert** | Freeze bei initialization | MEDIUM (30%) | Try/except + lazy-init |
| **EXE funktioniert nicht auf Target-Maschine** | Launch blockiert | **CRITICAL** | Smoke-test auf 5+ Maschinen wöchentlich |
| **Performance-Regression nach Fixes** | 5k bilder statt 2min dauert 5min | MEDIUM (25%) | Baseline comparison testen |
| **Memory-Leak mit Caches** | Freeze nach 1000+ bilder | MEDIUM (40%) | TraceMemorySample profiling |
| **Concurrent model loading race** | Crash unter Load | MEDIUM (35%) | Thread-safety unit tests |
| **Haar-Cascade not found in onedir** | Fallback broken | HIGH (60%) | Improve cascade finder robustness |
| **TensorFlow still tries GPU** | Blockiert 30s obwohl CUDA_VISIBLE_DEVICES=-1 | MEDIUM (40%) | Validate on real GPU system |
| **Windows Defender blocks EXE** | Can't run unnotarized EXE | MEDIUM (45%) | Code signing (if budget allows) |
| **License validation fails offline** | Users can't use app without internet | LOW (10%) | Already have offline mode |
| **Stripe webhook processing fails** | License not delivered after payment | MEDIUM (30%) | Supabase monitoring, retry logic |
| **First paying customer reports blocking bug** | Reputational damage | HIGH (70% probability if Phase 4 rushed) | Complete Phase 4 properly |

### Top 3 Mitigations
1. **Frozen-Build Smoke-Test als Gating-Kriterium** → Müss auf echtem Windows erfolgreich sein vor jeder Änderung
2. **Wöchentliche 10k-image stress runs** → Früh memory-leaks erkennen
3. **Extended Phase 4.1** (3-4 Wochen statt 2) → Lieber langsam + stabil als schnell + fragil

---

## 📈 REVIDIERTE ZEITPLANUNG

```
ORIG TIMELINE (zu optimistisch):
✅ Phase 2 (Feb 3-4)    → 9.19x speedup
✅ Phase 3 (Feb 5)      → Algorithmen
⏸️  Phase 4 (Mar-Jul)    → 16 Wochen QA
⏳ Oct 1: Launch

NEUE TIMELINE (realistisch):
✅ Phase 2-3 (Feb)      → OK, aber Frozen-Build war unterschätzt
🔴 Phase 4.1 (Feb 22 - Mar 15) → 3-4 WEEKS CRITICAL STABILIZATION
🔵 Phase 4.2 (Mar 15 - Apr 15) → 4 weeks comprehensive testing
🔵 Phase 4.3 (Apr 15 - May 1)  → 2 weeks regression testing
🔵 Phase 4.4 (May 1 - May 15)  → 2 weeks launch prep
🟢 Phase 5 (May 15 - Oct 1)    → 5 months (soft-launch, business, marketing)
🚀 Oct 1: Launch (+ Birthday + Gewerbe-Anmeldung)

Kritischer Pfad:
- Phase 4.1: BLOCKIERT, alles andere läuft darunter
- Phase 4.2-4.4: Parallel wo möglich, aber Stabilität first
- Phase 5: Nur wenn Phase 4 100% grün
```

---

## 🎯 WHAT'S CHANGED & WHY

### Entfernt (zu optimistisch)
- ❌ Phase 4B (Mobile) vor v1.0 → Zu früh, erst v2.x nach erfolgreichem v1.0 launch
- ❌ "Oktober Launch ist realistisch" → Neue Risiken identifiziert
- ❌ "16 Wochen Phase 4" → Besser strukturiert in 4.1/4.2/4.3/4.4

### Hinzugefügt (kritisch unterschätzt)
- ✅ Phase 4.1: Frozen-Build Stabilization (BLOCKER)
- ✅ Smoke-Test Protocol (gefehlt in ursprünglicher Roadmap)
- ✅ MediaPipe Thread-Timeout Validierung (war nicht geplant)
- ✅ Config-Hash Deadlock Check (war nicht gedacht)
- ✅ Expanded Stress-Testing (50k, 100k images)
- ✅ Memory-Leak Detection (war zu kurz behandelt)

### Realisiert - aber Timing geändert
- ⏳ Launch Jun 1 - Oct 1, nicht Apr 1-Oct 1
- ⏳ Soft-Launch Jun (beta) statt direkt public Oct
- ⏳ Gewerbe-Anmeldung Oct (muss wait für 16. birthday)

---

## 🚨 NEXT IMMEDIATE STEPS (Feb 22-23) - UI-Responsiveness CRITICAL

### Status Update: MAJOR PROGRESS  
**EXE läuft:** ✅ Model Loading blockiert nicht mehr, PyInstaller Build stabil
**MediaPipe Timeout:** ✅ Implementiert und validated on dev machine
**UI-Freeze Problem:** ✅ **ROOT CAUSE IDENTIFIZIERT + GEFIXT** (45s Thumbnail-Loading im UI-Thread)

### Root Cause Identified & Fixed (Feb 22, 2026)
**Problem:** 
- Dialog aktualisiert ("Bilder werden bewertet...") vor Worker.start() ✅
- ABER: Qt verarbeitet Events nicht sofort → Dialog bleibt unsichtbar
- QualityAnalyzer.__init__() in Worker dauert 2-3 Sekunden **ohne** Progress-Signale
- User sieht "keine Rückmeldung" weil Windows UI-Thread als blockiert markiert

**Implementierte Lösungen:**
1. ✅ Dialog **EXPLIZIT** mit `.show()` sichtbar machen (falls minimiert)
2. ✅ `QApplication.processEvents()` nach `thread.start()` → forciert Event-Loop
3. ✅ **SOFORT** erstes Progress-Signal emittieren (vor Model-Init)
4. ✅ Progress-Updates **WÄHREND** Model-Init (QualityAnalyzer ready → GroupScorer ready)
5. ✅ Timing-Diagnose Logging (`time.monotonic()` für Init-Dauer)

**Code-Änderungen:**
- `modern_window.py:2662-2692` (_on_duplicate_finder_finished):
  - Dialog explizit show() wenn nicht visible
  - processEvents() mit Logging
- `modern_window.py:159-207` (RatingWorkerThread.run):
  - Sofortiges emit(87, "Modelle werden geladen...")
  - Progress-Signals zwischen QualityAnalyzer + GroupScorer
  - Timing-Logs für jede Init-Phase

### 🚨 ZWEITE CRITICAL DISCOVERY: 45-Sekunden UI-Freeze (Feb 22, 2026)

**Problem - "Keine Rückmeldung" zwischen Logs:**
- User meldet: 45 Sekunden zwischen "Loaded 136 groups" und "Connecting to database"
- UI zeigt "Keine Rückmeldung" - kein Progress-Dialog sichtbar

**Root Cause:**
```
_on_indexing_finished() → refresh_groups() → _render_groups()
→ FÜR JEDE DER 136 GRUPPEN: get_thumbnail() SYNCHRON!
→ 136 × 300ms Disk I/O = 40+ Sekunden im UI-Thread
```

**Fix Implementiert:**
- ✅ Synchronous thumbnail loading ENTFERNT aus `_render_groups()`
- ✅ Async ThumbnailLoader eingefuehrt (QImage im Worker, QPixmap im UI)
- ✅ Progress-Dialog Phase "Bilder werden geladen..." mit Live-Zaehlung
- ✅ Standard-Icons/Placeholder bis Thumbnail-Signal ankommt
- ✅ Extensive timing diagnostics in allen UI handlers
- ✅ Performance-Budget dokumentiert: UI-Thread max 100ms blockieren

### Diese Woche (Feb 22-28)
1. **[URGENT] UI-Responsiveness Fix - IMPLEMENTED**
   - ✅ Fixed: Dialog explizit show() + verify isVisible()
   - ✅ Fixed: QApplication.processEvents() nach RatingWorkerThread.start()
   - ✅ Fixed: IMMEDIATE progress signal (87, "Modelle werden geladen...")
   - ✅ Fixed: Progress-Updates WÄHREND Model-Init (3 signals statt silent 2-3s)
   - ✅ Added: Timing-Diagnose Logs (time.monotonic() für alle UI handlers)
   - ✅ **CRITICAL FIX: 45s UI-Freeze durch synchrones Thumbnail-Loading entfernt**
   - ✅ **Added: Extensive timing diagnostics in refresh_groups(), _render_groups(), etc.**
   - 🔄 Build läuft mit ALLEN Fixes
   - [ ] Test: Verify refresh_groups() jetzt <1s (vorher 45s)
   - [ ] Test: Verify Dialog sofort "Bilder werden bewertet..." sichtbar
   - [ ] Test: Kein "keine Rückmeldung" mehr zwischen Hashing → Bewertung
   - [ ] Verify: Logs zeigen exakte Timing für jeden Schritt (ms-Genauigkeit)

2. **Check Other Workers** (IndexingThread, ExifWorkerThread)
   - [ ] Pattern check: Sofort Signals emittieren (nicht erst nach Init)
   - [ ] QApplication.processEvents() Konsistenz
   - [ ] Explicit dialog.show() wo nötig

3. **Documentation & Lessons Learned**
   - ✅ Created `THREADING_BEST_PRACTICES.md` (comprehensive guide)
   - ✅ Section: Worker init patterns (emit status IMMEDIATELY, nicht nach Init)  
   - ✅ Section: When to use QApplication.processEvents()
   - ✅ Section: Dialog visibility checks (isVisible() + explicit show())
   - [ ] **TODO**: Add section on synchronous I/O anti-patterns (thumbnail/file loading)
   - [ ] **TODO**: Add performance profiling guide (time.monotonic() patterns)
   - [ ] Update Phase 4.1: UI-Responsiveness is now explicit stability goal

4. **Performance Optimization Follow-up**
   - ✅ Async thumbnail loading fuer Gruppenliste + Grid-Page implementiert
   - [ ] Lazy loading nur fuer visible items (weiter optimieren)
   - [ ] Profile other potential I/O bottlenecks (EXIF reading, DB queries)
   - [ ] Establish Performance Budget documentation: UI-Thread max 100ms per operation
   - [ ] Add performance regression tests

### Ziel nach dieser Woche
Kein sichtbarer Freeze zwischen Pipeline-Phasen. Alle Dialoge erscheinen sofort.
**Refresh ohne synchrone I/O - max 1s für 500+ Gruppen.**
Alle Progress-Signale innerhalb <500ms nach Thread.start().
   - [ ] Update ROADMAP.md mit diesem Document

### Nächste 2 Wochen (Mar 1-15)
4. **Phase 4.1 Implementation Sprint**
   - Execute all tasks in 4.1 section above
   - Weekly report: Was blockiert noch?

### Mar 15: Go/No-Go Decision
- IF Phase 4.1 complete + green → Phase 4.2 start
- IF NOT → Extend 4.1, debug blockers

---

## 📊 SUCCESS METRICS (Updated)

### Phase 4.1 Exit Criteria (MUST PASS)
- ✅ EXE runs pollution-free on 5 target systems
- ✅ Zero hangs/freezes during normal use
- ✅ Model-loading <20s total
- ✅ All fallbacks function correctly
- ✅ Logs clear and actionable

### Phase 4.2 Exit Criteria
- ✅ 310 pytest all pass
- ✅ 100k image stress test completes
- ✅ Zero memory growth
- ✅ All edge cases handled
- ✅ UI responsive (>30 FPS)

### Phase 4.3 Exit Criteria
- ✅ No regression >5%
- ✅ Baselines documented

### Launch Readiness (Oct 1)
- ✅ v1.0.0 stable + tested
- ✅ First 10 paying customers
- ✅ Zero critical bugs in production
- ✅ Support system operational

---

## 💭 BOTTOM LINE

**Alte Roadmap war zu aggressiv.** 
Frozen-Build Komplexität war unterschätzt. MediaPipe blockiert, Config könnte deadlock, Haar-Cascades fragil.

**Neue Roadmap ist konservativ ableugnen realistisch:**
- 3-4 Wochen Stabilisierung (nicht 2)
- Smoke-testing systematisch (nicht ad-hoc)
- Stress-testing expanded (10k → 100k)
- Launch in Nov (nicht Oct), aber + Geburtstag still Oct 1

**Wenn Phase 4.1 erfolgreich:**
- Launch ist realistisch
- Produkt stabil
- Geschäft ready

**Wenn Phase 4.1 Probleme hat:**
- Lieber Verschiebung als buggier Launch
- Reputational damage > Timing pressure



---

## 📋 COMPLETED PHASES (Archiv - Details entfernt, siehe Git History)

**Phase 0 (Jan 20 - Feb 2):** ✅ Foundation (Profiling, CI/CD, Database Migrations)

**Phase 1 (Feb 3):** ✅ v0.6.0 Release Candidate (Build complete)

**Phase 2 (Feb 3-4):** ✅ v0.7.0 Performance Optimization (9.19x speedup: 19.1 min → 2.1 min für 5k images)

**Phase 3 (Feb 5):** ✅ v0.8.2 Algorithm Improvements (Face Detection, Lighting, Sharpness)

**Features Complete:** Quality Analysis, Duplicate Detection, Theme System, Lizenzierung, i18n, Stripe+Supabase, Performance Optimized, Code Quality (310 tests pass)

---

## 📊 SUCCESS METRICS (Updated)

### Phase 4.1 Exit Criteria (MUST PASS)
- ✅ EXE runs pollution-free on 5 target systems
- ✅ Zero hangs/freezes during normal use
- ✅ Model-loading <20s total
- ✅ All fallbacks function correctly
- ✅ Logs clear and actionable

### Phase 4.2 Exit Criteria
- ✅ 310 pytest all pass
- ✅ 100k image stress test completes
- ✅ Zero memory growth
- ✅ All edge cases handled
- ✅ UI responsive (>30 FPS)

### Phase 4.3 Exit Criteria
- ✅ No regression >5%
- ✅ Baselines documented

### Launch Readiness (Oct 1)
- ✅ v1.0.0 stable + tested
- ✅ First 10 paying customers
- ✅ Zero critical bugs in production
- ✅ Support system operational

---

## 💭 BOTTOM LINE

**Alte Roadmap war zu aggressiv.** 
Frozen-Build Komplexität war unterschätzt. MediaPipe blockiert, Config könnte deadlock, Haar-Cascades fragil.

**Neue Roadmap ist konservativ und realistisch:**
- 3-4 Wochen Stabilisierung (nicht 2)
- Smoke-testing systematisch (nicht ad-hoc)
- Stress-testing expanded (10k → 100k)
- Launch in Oct (+ Geburtstag + Gewerbe-Anmeldung)

**Wenn Phase 4.1 erfolgreich:**
- Launch ist realistisch
- Produkt stabil
- Geschäft ready

**Wenn Phase 4.1 Probleme hat:**
- Lieber Verschiebung als buggier Launch
- Reputational damage > Timing pressure

---

## � FINAL NOTES - Feb 22, 2026
**Dauer:** 3 Wochen (Jan 20 - Feb 2) | **Status:** Complete

#### Week 4 P2: Performance Profiling ✅
- **Deliverable**: Profiling framework mit baseline metrics
- **Metrics**: 
  - License init: 180.26ms (baseline)
  - Feature flags: 0.001ms
  - Activation: 1.68ms
  - Image processing: 320s → 40s with cache (8x)
- **Files**: `src/photo_cleaner/profiling/`, `PERFORMANCE_BASELINE_2026-02-02.md`

#### Week 5 P2: GitHub Actions CI/CD ✅
- **Deliverable**: 4 workflows, 6 test environments, 9 quality tools
- **Workflows**:
  - tests.yml: 54 unit + 47 E2E tests
  - security.yml: Bandit + Safety
  - quality.yml: Code quality analysis
  - performance.yml: Regression detection
- **Files**: `.github/workflows/`, 2 comprehensive documentation guides

#### Week 6 P2: Database Migration System ✅
- **Deliverable**: Safe schema evolution with rollback support
- **Migrations**: 4 migrations (V001-V004)
- **Features**: Checksum validation, transaction safety, history tracking
- **Files**: `src/photo_cleaner/db/migrations/`, `docs/DATABASE_MIGRATIONS.md`

---

### PHASE 1: RELEASE CANDIDATE & USER TESTING ✅ (Februar 3-15)
**Status:** COMPLETE | **Result:** v0.6.0 Ready

#### Completed ✅
- ✅ **Onedir Build**: Fixes antivirus extraction issues
- ✅ **Lazy Imports**: Fixed numpy/cv2 PyInstaller conflicts  
- ✅ **Auto-ZIP Script**: `create_release.py` creates distributable packages
- ✅ **Version 0.6.0**: Ready for testing
- ✅ **Security Analysis**: Comprehensive privacy/security documentation created

#### Testing (Parallel zu Phase 2)
- ⏳ **User Testing**: Läuft parallel, nicht blockierend
- ⏳ Edge Cases dokumentieren wenn gefunden
- ⏳ Bugs in Issues tracken

**Deliverable:** ✅ v0.6.0 Build Complete + DATENSICHERHEIT_ANALYSE.md

---

### PHASE 2: DATA-DRIVEN OPTIMIZATION ✅ (Februar 3-4 - COMPLETE!)
**Status:** ✅ COMPLETE (2 days!) | **Achievement:** v7.0.0 mit 9.19x Speedup! | **Ziel übertroffen:** 919% schneller statt 40-50%

#### Week 1 (Feb 3-9): Profiling Baseline ✅ COMPLETE
- ✅ Ran profiling framework on 5k synthetic images
- ✅ Identified Top 5 bottlenecks with cProfile
- ✅ Documented baseline: 144.1 seconds, 15 MB memory delta
- ✅ **CRITICAL FINDING:** Indexing = 137.3s (95% of total time!)
- ✅ Root cause: ProcessPool IPC overhead (~25ms per image vs ~2ms actual work)
- ✅ Created performance improvement roadmap (ThreadPool + batching = 4-7x speedup potential)

**Results Summary:**
- Test Run: 5,000 synthetic images (1920-4032px, varying quality)
- Duration: 144.14 seconds (2.4 minutes)
- Memory: 37 MB → 88 MB (15 MB delta, very efficient)
- Top Bottleneck: `_stage_index()` in pipeline.py:230 (137.3s / 95%)
- Secondary: ProcessPool/IPC overhead (threading, context switches)
- **Optimization Strategy:** ThreadPool instead of ProcessPool (saves IPC, suitable for I/O-bound hashing)
- **Expected Improvement:** 4-7x speedup → 20-35 seconds for 5k images

#### Week 2 (Feb 3-4): ThreadPool Optimization ✅ COMPLETE (CRITICAL FINDING)
- ✅ Replaced ProcessPool with ThreadPoolExecutor in indexer.py
- ✅ Tested on 1k images: 30.87s → **4.67x speedup** 🎉
- ✅ Tested on 5k images: 142.36s → **1.01x speedup** ⚠️ (bottleneck shifted!)
- ✅ Profiled and documented results
- ✅ Identified root cause: **SQLite single-writer contention**

**CRITICAL DISCOVERY:**
- ✗ IPC overhead was NOT the primary bottleneck (would scale linearly)
- ✅ **Database write lock contention IS the real bottleneck**
- ✅ ThreadPool threads compete for same database connection
- ✅ ProcessPool actually performs similarly at 5k scale (144s vs 142s = ~1%)
- ✅ Per-image throughput: 28-31ms/image (consistent across scales)
- **Conclusion:** ThreadPool viable for small batches, but database architecture limits scaling

**Results Summary:**
- 1k test: 30.87s (4.67x faster due to smaller memory footprint)
- 5k test: 142.36s (1.01x, database lock contention dominates)
- Per-image: ~29ms consistent (proves threading works, database is bottleneck)
- **Next:** Async writes with dedicated database write thread needed for true scaling

#### Week 3 (Feb 4): Async Database Writes ⚠️ PARADOXICAL RESULTS → ❌ REVERTED
- ✅ Designed queue-based write architecture
- ✅ Implemented dedicated database write thread (DatabaseWriteQueue)
- ✅ Refactored indexer to queue writes instead of blocking
- ✅ Tested on 1k images: **20.44s (7.05x speedup!)** 🎉
- ✅ Tested on 5k images: **170.07s (0.85x - SLOWER!)** ❌
- ✅ Tested batch_size=500: **148.52s (0.97x - still slower)** ❌
- ✅ Validated thread safety (0 errors, 0 data loss)
- ❌ **CONCLUSION: Async writes add MORE overhead than they save at scale**
- ✅ **REVERTED to sync batch-insert approach** (optimal for SQLite)

**ROOT CAUSE ANALYSIS:**
- ✅ 1k images: 20.44s → **7.05x speedup** (queue is small, flushes fast)
- ❌ 5k images: 170.07s → **0.85x slower** (queue grows faster than write thread can consume)
- ❌ batch_size=500: 148.52s → **0.97x** (still slower, queue overhead dominates)
- **Real Bottleneck:** **Disk I/O (~28-30ms/image)**, NOT database locks
- **Physical Limit:** HDDs: ~100 IOPS, SSDs: ~10k IOPS → 28ms/image is near HDD limit
- **Async Queue:** Adds Python overhead (threading, queue management) without solving I/O bottleneck

**LESSONS LEARNED:**
1. ✅ Profiling identified database as bottleneck (correct)
2. ❌ Assumed database LOCKS were the issue (incorrect)
3. ✅ Real issue: Disk I/O throughput (reads dominate, not writes)
4. ✅ Current performance (~28-30ms/image) is ALREADY EXCELLENT for I/O-bound work
5. ✅ Further optimization requires: SSD upgrade, OS-level caching, not code changes

**REALISTIC PERFORMANCE TARGETS (REVISED):**
- 5k images: ~140-150 seconds (current baseline) ✅ ACCEPTABLE
- 10k images: ~280-300 seconds (5 minutes) ✅ REALISTIC
- 50k images: ~1400-1500 seconds (23-25 minutes) ✅ ACHIEVABLE
- **Further improvement:** User hardware upgrades (HDD → SSD = 10x faster)

#### Week 4 (Feb 4): Focus Shift → Quality Analysis Optimization ✅ COMPLETE
- ✅ Accept indexing performance as near-optimal (~28ms/image)
- ✅ Shift focus to OTHER pipeline stages (quality analysis, duplicate detection)
- ✅ **CRITICAL FINDING:** Quality Analysis is **8x SLOWER than indexing!** (228.9ms vs 28ms/image)
- 🔵 Profile results: 5k images take **1,172 seconds (19.5 minutes)** for quality analysis alone!

**Profiling Results:**
```
Pipeline Stage        5k Time    Per-Image   Ratio
─────────────────────────────────────────────
Indexing             144s       28ms        ✅ OPTIMAL
Quality Analysis   1,172s      228ms        🔴 8x SLOWER
─────────────────────────────────────────────
Total Pipeline    1,300+ s               ⚠️ UNACCEPTABLE
```

**Root Cause Analysis:**
- Quality analysis is resolution-dependent
- Large images (4032x3024) take **50x longer** than small images (1200x800)
- Sequential processing (no parallelization)
- MediaPipe model may be loaded multiple times

**New Strategy:**
- ✅ Indexing is FAST ENOUGH (5k in 2.4 minutes)
- 🎯 **Focus on Quality Analysis** (19.5 min → target 2.5 min)
- 🎯 Three optimization vectors: Resolution-adaptive, Parallelization, Caching

**Documentation:**
- 📄 Created `PHASE2_WEEK4_ACTION_PLAN.md` with detailed priorities
- 📄 Created `PHASE2_WEEK4_PROFILING_RESULTS.md` with detailed findings ← **NEW**
- 📊 Created `profile_quality_analyzer.py` script
- 📊 Created `profile_duplicate_finder.py` script

#### Week 4 (Feb 4): Priority 1-3 Optimizations ✅ COMPLETE (9.19x speedup!)
**Status:** COMPLETE | **Result:** v7.0.0 Ready for Release

**Optimizations Implemented:**

1. **Priority 1: Resolution-Adaptive Processing** ✅
   - Downsample images >2000px to max 2000px before analysis
   - Maintain original resolution for scoring
   - **Result:** 228.9ms → 61.1ms per image (3.75x speedup)
   - Test: 100 images from test_data_system/5k
   - Disabled downsampling for MTCNN (needs full resolution)

2. **Priority 2: ThreadPool Parallelization** ✅
   - Implement ThreadPoolExecutor in analyze_batch()
   - Optimal: 4 workers (empirically validated)
   - Result: 61.0ms → 24.9ms per image (2.45x speedup)
   - Test: Benchmarked 4 vs 8 workers (4 is optimal)
   - Maintains result ordering, progress callbacks work

3. **Priority 3: MediaPipe Model Caching** ✅
   - Already implemented (singleton pattern)
   - Verified: Loads once, reuses across all images
   - Expected: 1.2x speedup (already amortized)
   - No additional work needed

**MAJOR ACHIEVEMENT:**

```
Combined Performance Improvement: 9.19x 🚀

Baseline (v0.6.0):        228.9ms/image → 1,144.5s for 5000 images (19.1 min)
With All Optimizations:    24.9ms/image →   124.5s for 5000 images (2.1 min)

Time Saved Per 5000 Images: 17 MINUTES ⏱️

Performance Projections:
- 5k images:   2.1 min (was 19.1 min)
- 10k images:  4.2 min (was 38.2 min)
- Full workflow (incl. indexing): 6.3 min (was 23.5 min)
```

**Key Commits:**
- 4fef828: ThreadPool parallelization implementation
- 3cf4d25: MTCNN face detection integration  
- f6b359d: Theme color bug fix (disabled_bg)
- b4ddb15: Database import path fix
- a172ea3: Database.connect() initialization fix
- 61bb837: EXIF getexif() fix for HEIC files
- 0e006fe: QApplication import fix for license dialog
- dfe326a: Documentation of all optimizations

**Testing:**
- ✅ 100 test images analyzed successfully
- ✅ Results maintained in correct order
- ✅ Exception handling per-image
- ✅ Progress callbacks functional
- ✅ MTCNN conditional downsampling
- ✅ Theme rendering without errors
- ✅ **USER VALIDATION (Feb 4):** Tested with 38 real HEIC images from OneDrive
- ✅ **USER FEEDBACK:** "Perfekt, ich liebe dieses Programm!" 🎉
- ✅ All pipeline stages work flawlessly
- ✅ v7.0.0 is production-ready

**Bug Fixes (Feb 4):**
- ✅ Fixed KeyError in folder selection dialog (missing disabled_bg color)
- ✅ Fixed ModuleNotFoundError for Database import path
- ✅ Fixed AttributeError for Database.connect() calls
- ✅ Fixed AttributeError for HEIC EXIF extraction (_getexif → getexif)
- ✅ Fixed NameError for missing QApplication import in license dialog
- ✅ All bugs committed locally, ready to push

#### Tasks (Overall)
1. **Profiling & Benchmarks** (using Week 4 P2 framework)
   - Baseline: 10.000 Bilder = 8-18 Minuten aktuell
   - Expected after optimization: 5-10 Minuten (30-40% faster)
   - Memory Peak bei verschiedenen Batch-Größen
   - CPU Utilization tracken
   - Top 5 Performance Bottlenecks identifizieren (using profiler)

2. **Database Optimization**
   - Query-Optimization: EXPLAIN PLAN für langsame Queries
   - Index-Strategien: Composite indexes
   - Connection Pooling: Optimierung mit WAL mode (V004)
   - Pagination: Für 50.000+ Result Sets

3. **Image Processing Optimization**
   - ✅ MediaPipe Caching (schon gemacht)
   - ✅ Resolution-Adaptive Detection (schon 6-10x speedup!)
   - Lazy Loading: Nur sichtbare Thumbnails rendern
   - Thumbnail Caching: Regenerierte Thumbs speichern (nicht jedesmal neu)
   - Batch Processing: Mehrere Bilder gleichzeitig?

4. **UI Responsiveness**
   - Non-blocking Progress: Loading-Spinner, keine Freezes
   - Worker Threads: Image Processing im Background
   - Virtual Scrolling: Für 50.000+ Listen
   - Cancel-Button: Laufende Operations abbrechen

**Ziele:**
- ✅ 5.000 Bilder: 2.1 Min (war 19.1 Min) - **ÜBERTROFFEN!**
- ✅ 10.000 Bilder: 4.2 Min (war 38.2 Min) - **ERREICHT!**
- ⏳ 50.000 Bilder: ~21 Min (extrapoliert)
- ⏳ 100.000 Bilder: ~42 Min (extrapoliert)
- ✅ Memory: <150 MB peak - **EXCELLENT!**
- ⏳ Face Detection Accuracy: >95% (Phase 3 target)

**Deliverable:** ✅ v0.7.0 Release mit 919% Speedup (statt 40-50%) - **MISSION ACCOMPLISHED!**

**PHASE 2 SUMMARY - MASSIVE SUCCESS! 🚀**

**Timeline:** Feb 3-4, 2026 (2 days instead of 12 weeks!)
**Result:** v0.7.0 released with 9.19x performance improvement

**Achievements:**
- ✅ Week 1: Profiling identified bottlenecks (144s for 5k images)
- ✅ Week 2: ThreadPool optimization (database bottleneck found)
- ✅ Week 3: Async writes tested & reverted (disk I/O is real limit)
- ✅ Week 4: **BREAKTHROUGH - 9.19x speedup in 1 day!**
  - Priority 1: Resolution-Adaptive Processing (3.75x)
  - Priority 2: ThreadPool Parallelization (2.45x)
  - Priority 3: MediaPipe Caching (already implemented)
  - Combined: **919% faster!**
- ✅ 5 Critical bug fixes deployed
- ✅ User validation: "Perfekt, ich liebe dieses Programm!"
- ✅ Production-ready v7.0.0

**Performance Impact:**
```
Before: 5,000 images = 19.1 minutes
After:  5,000 images = 2.1 minutes
Saved:  17 MINUTES per 5k batch!
```

**Next:** Phase 3 starts NOW - Algorithm improvements for even better results!

---

### PHASE 3: ALGORITHMUS-VERBESSERUNG ⚡ (Februar 3-5)
**Status:** ✅ COMPLETE | **Dauer:** 3 Tage | **Ziel:** v0.8.2 (Better Scoring, smarter auto-select)

**COMPLETED (Feb 5):**
1. ✅ Push all commits to GitHub (e3792a1)
2. ✅ Updated version to 0.8.2
3. ✅ Phase 3 Algorithm improvements complete
4. ✅ Beta Feedback System erstellt (HTML + analyze script)
5. ✅ Week 4: Lighting & Exposure improvements
6. ✅ Week 5: Detail Scoring & Local Sharpness
7. ✅ Week 5: Face Detection Improvements (Eye Quality, Gaze, Head Pose, Smile, Best Person)

#### Tasks
1. **User Feedback Loop** ✅
   - ✅ Beta Feedback System erstellt (feedback_form.html)
   - ✅ Automatische Analyse (analyze_feedback.py)
   - ✅ Setup-Dokumentation (FEEDBACK_SETUP.md)
   - 🔵 Beta Testers rekrutieren (10-20 Power Users)
   - 🔵 Tracken: Stimmt der Auto-Select?
   - 🔵 A/B Tests: Alter vs. Neuer Algorithmus

2. **Face Detection Improvements (Week 5 COMPLETE)**
   - ✅ Eye Quality: Öffnungsgrad (0-100%), Sharpness
   - ✅ Eye Contact Detection: Nutzer schaut direkt? (Gaze Score)
   - ✅ Multiple Faces: Beste Person auswählen (Best Person Selection)
   - ✅ Head Pose: Frontal > Seitenprofil bevorzugt (Head Pose Score)
   - ✅ Emotion: Lächeln, natürlicher Ausdruck? (Smile Score)

3. **Lighting & Exposure (Week 4 COMPLETE)**
   - ✅ Histogram-Analyse: Over/Underexposure Erkennung
   - ✅ Kontrast-Messung: Nicht zu flach, nicht zu hart
   - ✅ Color Cast Penalty (starker Farbton wird abgewertet)
   - ✅ HDR/Exposure Balance (Shadows/Highlights Ausgleich)

4. **Sharpness Detection**
   - ✅ FFT basiert statt Laplacian (Week 2 complete)
   - ✅ Lokale Sharpness: Tile-basierte Analyse
   - ✅ Motion Blur: Unterscheiden von Soft Focus
   - ✅ Autofocus-Fehler: Detektieren & penalizieren

5. **Detail Scoring**
   - ✅ Texture Analysis: Haare, Haut, Kleidung Details
   - ✅ Foreground/Background Separation (Subject scharf, Background weicher)

**Deliverable:** ✅ v0.8.2 mit verbessertem Scoring + Beta Feedback System

---

### PHASE 4: QA & TESTING (März - Juli)
**Status:** 🔵 IN PROGRESS | **Dauer:** 16 Wochen | **Ziel:** v0.9.0 → v1.0.0 RC

#### Stage 3 (Feb 6): Profiling auf echten Fotos (Skaliert) ✅
- **Datensatz:** 136 reale HEIC/JPG Fotos (Input-Ordner)
- **Baseline (vor Fixes):** 477.45s
- **Nach Cheap-Filter Optimierung:** 209.97s
- **Nach Parallelisierung Cheap-Filter:** 184.02s
- **Face Mesh Vergleich (nach Log-Optimierung):** 186.25s (an) vs 182.99s (aus) → ~3.26s / ~1.7%
- **Genauigkeit:** Keine Aenderung der Filterlogik, nur Performance
- **Entscheidung:** 10k-100k Stress-Test verschoben, Fokus auf echte Performance-Bottlenecks

#### Naechste Schritte (Phase 4.1 - Performance)
1. ✅ **Face Mesh Isolation Run**: Vergleich mit/ohne Face Mesh nach Log-Optimierung (Delta ~1.7%)
2. ✅ **HEIC Decode/Resize weiter optimieren**: PIL Downsample vor numpy, vermeidet Doppel-Resize
3. ✅ **Profiling-Runs dokumentieren**: Neue Baselines in profiling_results
4. ✅ **UI Performance**: Keine Freezes, Progress stabil
5. ✅ **UI Layout polish**: Settings/License/Language Dialoge, bessere Abstaende, Word-Wrap
6. ✅ **Splash frueh anzeigen**: sichtbares Feedback vor langen Initialisierungen

#### Phase 4.2 (Feb 7): Test-Stabilisierung ✅
- ✅ **Pytest Suite stabil**: 310 Tests, keine Skips/Warnungen/Crashes
- ✅ **Heavy-Dep Guards aktiv**: Keine TensorFlow/MediaPipe Crashes im Testlauf

#### Tasks
1. **Complete Testing Suite**
   - ✅ Unit/Integration/E2E Tests: 310 Tests clean
   - Stress Tests: 100.000+ Bilder
   - ✅ Crash Testing: Ungueltige Inputs (scripts/test_crash_inputs.py)
   - ✅ Memory Leak Detection: Laengere Sessions (scripts/test_memory_leak.py)

2. **Security Audit**
   - ✅ License Key Validation (Ed25519 Signaturen, fail-closed)
   - ✅ Device-Register Enforcement (registered_devices, lokale Checks)
   - ✅ SQL Injection Protection (Parameterbindung geprueft)
   - ✅ File Permission Handling (Batch-Delete Guard bei leerer Liste)
   - ✅ Offline Mode: License Cache Integritaet (Snapshot-Signatur Pflicht)

3. **Documentation** (teilweise erledigt)
   - ✅ Dokumentations-Index + Einstieg: docs/INDEX.md, docs/README.md
   - ✅ Guides (docs/guides): AUTO_SELECTION, CLEANUP, WORKFLOW, MODERN_UI_QUICKSTART, FEEDBACK_SETUP, LICENSE_* , PHASE_B_QUICKSTART
   - ✅ Tech Docs (docs/tech): CACHE_SYSTEM, DATABASE_MIGRATIONS, PERFORMANCE_ANALYSIS, PYINSTALLER_NUMPY_SOLUTIONS, THEME_SYSTEM
   - ✅ Architecture Index: docs/architecture/INDEX.md
   - ✅ Security: docs/SECURITY.md
   - ✅ User Manual: Feature-by-Feature (docs/guides/USER_MANUAL.md)
   - ✅ API Docs: Für zukünftige Entwickler (docs/tech/API_REFERENCE.md)
   - ✅ Troubleshooting: Häufige Fehler + Known Issues (docs/guides/TROUBLESHOOTING.md)
   - ✅ FAQ: User Questions (docs/guides/FAQ.md)

4. **Release Build**
   - PhotoCleaner.exe finalisieren
   - Installer Script
   - Version Numbering, Build Info
   - Release Notes
   - ⚠️ MTCNN/TensorFlow DLL-Init in EXE fixen + auf Clean Machine verifizieren

#### Stress-Test Plan (Draft, Feb 7)
- **Datensaetze**: 10k / 50k / 100k Bilder, Mix aus JPG/HEIC, 1-3 Resolutionsklassen
- **Varianten**: Cache an/aus, Face Mesh an/aus, Cheap-Filter parallel an/aus
- **Metriken**: Gesamtzeit, Stage-Zeiten, Peak RAM, Crash-Freiheit, UI-Progress stabil
- **Pass-Kriterien**: Keine Crashes, Peak RAM <1 GB, keine Hangs, stabile Reihenfolge

**Deliverable:** v1.0.0 RC (Release Candidate)

---

### PHASE 5: MARKET PREPARATION & LAUNCH (August - Oktober)
**Dauer:** 12 Wochen | **Ziel:** Business Ready für Launch

**WICHTIG:** Keine öffentliche Beta, da noch kein Gewerbe! Nur technische & Business-Vorbereitung.

#### August: Final Testing & Polish (Week 1-4)
1. **Final RC Testing**
   - v1.0.0 RC testing mit 5-10 Power Usern
   - Final bug fixes
   - Performance validation
   - v1.0.0 Final Build

2. **Market Research**
   - Konkurrenzbenchmarking: Lightroom, Google Photos, andere Tools
   - Pricing Validation: Sind €59/€199 realistisch?
   - Go-to-Market Strategie: Wer kauft? Wie erreichen?
   - Target Audience definieren

#### September: Business Setup & Marketing (Week 5-8)
3. **Business Setup VORBEREITUNG**
   - ⚠️ Gewerbe-Anmeldung vorbereiten (Unterlagen sammeln)
   - Geschäftskonto recherchieren (Kontist, Fyrst, N26 Business)
   - Rechtliches: ToS Final, Datenschutz, Impressum finalisieren
   - Tax/VAT: Kleinunternehmer-Regelung vorbereiten
   - Stripe Live Mode vorbereiten

4. **Marketing Materials**
   - Landing Page / Website (Design + Copy)
   - Social Media Setup: Twitter, YouTube vorbereiten
   - Press Kit: Logo, Screenshots, Story
   - Demo Video: 3-5 Min Feature Overview
   - Email Campaign Template vorbereiten
   - Launch Announcement vorbereiten

5. **Support Infrastructure**
   - Email Support Template
   - FAQ / Knowledge Base
   - Bug Reporting System
   - Feature Request Process
   - Discord/Community Setup (optional)

---

## 🚨 CRITICAL STRATEGIC INSIGHT - MOBILE FIRST NEEDED!

**Problem Statement (Feb 5, 2026):**
- PC version is stable ✅
- **BUT:** 95% of users store photos on smartphones, not PCs
- Current target market is TOO SMALL (PC users only)
- Current PC performance is heavy (i7-12700F still struggles with MediaPipe)
- **Risk:** Launch v1.0.0 PC without mobile → Limited market adoption

**Solution:** Hybrid Strategy with Cloud-Assisted Mobile App
- **Mobile App** (iOS/Android) for photo collection management
- **Cloud Processing** for expensive ML models
- **Offline Lite Mode** for basic duplicate detection

---

### PHASE 4B: MOBILE STRATEGY & TECHNICAL PLANNING ⚡ (NEW!)

**Goal:** Position PhotoCleaner as THE cross-platform photo management solution

#### Market Opportunity Analysis
```
Market Size Comparison:
─────────────────────────────────────────
Desktop/PC Users:         ~30-40% of target market ✗ TOO SMALL
Smartphone Users:         ~85-95% of target market ✓ MUST HAVE
Android+iOS Combined:     >3 billion devices worldwide
Monthly Active Photo Apps: >500M users
```

**Decision:** Mobile-first approach with cloud backend
- **v1.0.0 PC** remains standalone, but marked "Legacy"
- **v2.0.0 Mobile** (iOS/Android) primary product
- **v2.1.0 Cloud** backend for ML processing

#### Technical Architecture: Cloud-Assisted Mobile

**Option A: Hybrid App (RECOMMENDED for this project)**
```
┌─────────────────────────────────────────────────────────┐
│                   iOS/Android App                       │
│  ┌──────────────────────────────────────────────────┐   │
│  │ On-Device Layer (Lightweight)                    │   │
│  │ ├─ Local Photo Library Integration               │   │
│  │ ├─ Light Hashing (pHash on-device)               │   │
│  │ ├─ Group Management & UI                         │   │
│  │ └─ Offline Mode (basic duplicate detection)      │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────┐   │
│  │ Cloud Sync Layer (Optional Premium)              │   │
│  │ ├─ Batch upload to cloud                         │   │
│  │ ├─ Cloud Processing (MediaPipe analysis)         │   │
│  │ └─ AI-powered scoring results                    │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
           ⬆️ Lightweight only (5-10MB RAM)
           ⬆️ No heavy ML models on device
           ⬆️ Opt-in cloud for premium features
```

**Why This Approach:**
1. **Performance:** No MTCNN/MediaPipe burden on mobile
2. **Battery:** Lite pHash algorithm only
3. **Storage:** Minimal app size (<50MB)
4. **User Choice:** Basic offline, optional premium cloud
5. **Revenue:** Premium tier for cloud features

#### Technical Stack Options

**Option 1: Flutter (BEST CHOICE)**
- ✅ Single codebase for iOS+Android
- ✅ Excellent native performance
- ✅ Direct access to photo library APIs
- ✅ TensorFlow Lite support if needed
- ✅ Growing ecosystem for ML
- ⏱️ Dev time: 4-6 weeks (basic version)

**Option 2: React Native**
- ✅ Larger dev community
- ✅ Code sharing with potential web version
- ⚠️ Performance slightly lower than Flutter
- ⏱️ Dev time: 5-7 weeks

**Option 3: Native (SwiftUI + Kotlin)**
- ✅ Best performance
- ✅ Best native APIs
- ❌ Double dev work (2x time)
- ⏱️ Dev time: 8-12 weeks

**Recommendation:** Flutter (best balance of speed + performance)

#### Phase 4B Timeline

**February (Week 1-2): Architecture & Design**
- [ ] Finalize cloud vs local strategy
- [ ] Wireframe mobile UI (Figma/Adobe XD)
- [ ] API design for cloud backend
- [ ] Tech stack decision (Flutter vs React Native)
- [ ] Deliverable: Technical Design Document

**March-April (Week 1-8): MVP Development**
- [ ] Flutter project setup
- [ ] Photo library integration
- [ ] Local pHash duplicate detection (offline)
- [ ] Basic grouping and management UI
- [ ] Local storage for results
- [ ] Deliverable: iOS/Android testable APK/IPA

**May (Week 1-4): Cloud Integration**
- [ ] Cloud API design (REST/GraphQL)
- [ ] Supabase backend setup for mobile
- [ ] MediaPipe cloud inference (optional)
- [ ] Premium tier unlock logic
- [ ] Deliverable: Cloud-enabled beta version

**June-July (Week 1-8): Testing & Refinement**
- [ ] Beta testing with real users
- [ ] Performance optimization
- [ ] Bug fixes
- [ ] App store submission prep (Google Play, Apple)
- [ ] Deliverable: v2.0.0 Mobile ready for launch

**Aug-Oct (Week 1-12): Launch**
- [ ] App store approval process
- [ ] Marketing campaign
- [ ] Initial user acquisition
- [ ] Support & monitoring
- [ ] Deliverable: Live on App Stores

#### MVP Feature Set (v2.0.0)

**Tier 1: Free (On-Device Only)**
- ✅ Photo library browser
- ✅ Local duplicate detection (pHash)
- ✅ Grouping & organization
- ✅ View/delete with confirmation
- ✅ No cloud, no advanced features
- 📊 Target: 1M+ downloads (awareness)

**Tier 2: Premium (With Cloud)**
- ✅ All Tier 1 features
- ✅ Cloud backup of analysis
- ✅ MediaPipe quality scoring
- ✅ AI-powered auto-select
- ✅ Cross-device sync
- ✅ Priority support
- 💰 €4.99/month or €49/year
- 📊 Target: 10-20% conversion

**Tier 3: Family (Cloud + Sharing)**
- ✅ All Premium features
- ✅ Family sharing (2-6 members)
- ✅ Shared albums & analysis
- 💰 €7.99/month or €79/year

#### Cloud Infrastructure Strategy

**Supabase + Edge Functions** (leverage existing setup)
```
Mobile App ──→ Supabase Edge Function
                ├─ Validate license
                ├─ Queue job for processing
                └─ Return processing URL

Processing Server (separate)
├─ MediaPipe inference (on GPU)
├─ Quality scoring
└─ Results saved to Supabase

Mobile App ──→ Poll for results ──→ Cache & display
```

**Cost Model:**
- Free tier: Basic pHash (no server cost)
- Premium: €0.05-0.10 per image for cloud processing
- Profitable at €4.99/month with <50 premium images/month

#### Performance Targets (Mobile)

**On-Device (Local Mode):**
- App startup: <2 seconds
- Photo library load: <1 second
- Duplicate detection: <1ms per image (pHash only)
- RAM usage: 5-10MB max
- App size: 30-50MB

**Cloud Mode (Premium):**
- Queue image: <1 second
- Processing time: 5-30 seconds per image (depending on device)
- Results sync: <5 seconds

#### Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| App store rejection | Follow guidelines from day 1, beta test |
| User acquisition | Launch with launch PC version awareness |
| Cloud costs | Free tier is on-device, premium covers cost |
| Development delay | MVP focuses on core features only |
| Performance issues | Lite algorithms, cloud for heavy lifting |

---

#### Oktober: LAUNCH! 🚀 (Week 9-12)
6. **Pre-Launch (Week 1)**
   - Final server checks (Supabase, Stripe, Email)
   - Marketing campaign finalisieren
   - Social Media Announcements

7. **LAUNCH DAY - Oktober 1, 2026** 🎂
   - **16. Geburtstag** = Geschäftsfähig!
   - **Gewerbe anmelden** (Termin vorher buchen!)
   - **Geschäftskonto eröffnen**
   - Stripe Live Mode aktivieren
   - v1.0.0 Official Release
   - First Paying Customers möglich! 💰

8. **Post-Launch (Week 2-4)**
   - Erste Verkäufe abwickeln
   - Customer Support Live
   - Post-Launch Hotfixes (v1.0.1, v1.0.2)
   - Customer Feedback Loop
   - Roadmap für v1.1 planen

**Deliverable:** v1.0.0 Final + Business Live + First Customers! 🎉

---

**🎯 Ziel:** v1.0.0 Launch + Erste 10 zahlende Kunden im Oktober!

---

## 📈 SUCCESS METRICS

### Code Quality
| Metrik | Target |
|--------|--------|
| Syntax Errors | 0 |
| Test Coverage | >80% |
| Bug Reports | <5 pro 1000 installs |
| Crashes in v1.0 | 0 |
| Code Review Comments | <3 avg |

### Performance
| Metrik | Current | Phase 2 Goal | Status |
|--------|---------|------------|--------|
| 5k images | 144s (2.4 min) | 140-150s | ✅ OPTIMAL |
| 10k images | ~280-300s | <5 min | ✅ ACHIEVABLE |
| 50k images | ~1400-1500s | 23-25 min | ✅ REALISTIC |
| Memory Peak | ~150 MB | <1 GB | ✅ EXCELLENT |
| UI Responsiveness | ~1-2sec freezes | <100ms | 🔵 PRIORITY |
| Face Detection Acc. | ~92% | >95% | 🔵 NEXT PHASE |

### Business
| Metrik | Target |
|--------|--------|
| Beta Testers | 50-100 |
| NPS Score | >4.5/5.0 |
| First Month Customers | 100+ |
| Monthly Recurring Revenue (MRR) | €500+ |
| Customer Satisfaction | >4.7/5.0 |

---

## 📅 TIMELINE VISUAL

```
✅ Phase 0 (Jan 20 - Feb 2)     → Foundation complete
                                   Performance profiling, CI/CD, Migrations

✅ Phase 1 (Feb 3)              → v0.6.0 Build Complete
                                   PyInstaller, Testing, Security audit

✅ Phase 2 (Feb 3-4)            → Performance Optimization (v0.7.0)
                                   9.19x Speedup! Resolution-adaptive + ThreadPool
                                   ⚡ 5k images: 19.1 min → 2.1 min

✅ Phase 3 (Feb 5)              → Algorithm Improvements (v0.8.2)
                                   Face Detection (Eye Quality, Gaze, Head Pose, Smile)
                                   Lighting & Exposure, Sharpness, Detail Scoring
                                   Beta Feedback System created

🔵 Phase 4 (März - Juli)        → QA & Testing (v0.9.0 → v1.0.0 RC)
   📅 März:   Beta Testing (10-20 users), User Feedback
   📅 April:  Testing Suite Expansion (90% coverage)
   📅 Mai:    Security Audit, Performance Validation
   📅 Juni:   Documentation & Polish
   📅 Juli:   v1.0.0 RC Build

⏳ Phase 5 (Aug - Okt)          → Market Prep & Launch (v1.0.0 Final)
   📅 Aug:    Final Testing, Market Research
   📅 Sept:   Business Setup, Marketing Materials
   📅 Okt 1:  🎂🚀 LAUNCH DAY!
              16. Geburtstag + Gewerbe-Anmeldung
              v1.0.0 Release + First Customers! 💰

🚀 Oct+ (Week 1-4)              → Post-Launch
                                   Customer Support, Hotfixes, Roadmap v1.1
```

**Kritischer Pfad:**
- ✅ Feb: Phase 2 + 3 complete (Performance + Algorithms)
- 🔵 Mär-Jul: QA & Testing (v1.0.0 RC)
- ⏳ Aug-Sept: Marketing + Business Setup vorbereiten
- **🚀 1. Okt: GO LIVE** (endlich verkaufen dürfen!)

---

## 🎯 WHAT NOT TO DO

- ❌ New features before v1.0
- ❌ Mobile app Entwicklung vor v1.0 (nur Planung in Phase 4B)
- ❌ Additional languages before v1.0
- ❌ Complex integrations (Dropbox, OneDrive, etc.)
- ❌ UI redesigns (current design is professional)
- ❌ Perfectionism on minor details

---

## ✨ STRATEGY

### Problem mit "New Features"
- Jede neue Feature = neue Bugs = mehr Support = weniger Zeit für andere Dinge
- Zahlende Kunden wollen **Stabilität & Performance**, nicht "Bling"
- v1.0.0 sollte **perfekt** sein, nicht "Features" haben

### Warum dieser Fokus?
1. **Stabilität** = User trust
2. **Performance** = User satisfaction
3. **Business** = Revenue & sustainability
4. **Quality** = Professional reputation
5. **Polish** = Ready to compete

### Vorteil der 9-Monate
- Genug Zeit für gründliche Arbeit (nicht gehetzt)
- Echtes Beta Testing (50-100 users, real data)
- Time for market research
- Time for algorithm optimization
- Time for business setup
- Gewerbe-Anmeldung passt perfekt mit 16. Birthday

---

## 🎓 WARUM DAS FUNKTIONIERT

**Für einen 15-Jährigen ist das beeindruckend:**
- Feature-complete Produkt
- Professionelles Lizenzierungs-System
- Stripe + Supabase Integration
- i18n Support
- Modern UI mit Dark Mode

**Das unterscheidet dich von 99% der Hobby-Projekte:**
- Nicht "schnell 100 Features"
- Sondern "machen wir v1.0 echt gut"
- Business-focused, nicht nur technical
- User-centered, nicht ego-driven

**Oktober Launch ist realistisch:**
- 9 Monate ist genug Zeit
- Nicht im Eile gebaut
- Beta-tested mit echten Nutzern
- Geschäft korrekt setup

---

## 📝 DIESE WOCHE (Feb 7-14)

1. **Check EXE Build Status**
   - ✅ PhotoCleaner.exe in dist/PhotoCleaner
   - ⏳ Smoke-Test: Dark/Light Theme, Import, 10 Bilder
   - ⏳ Installer pruefen

2. **Testing**
   - ✅ Pytest full suite clean (310 Tests, 29.65s)
   - ⏳ Stress-Test Plan fuer 100k Bilder definieren

3. **Start Refactoring**
   - Priority: modern_window.py (78 Farben)
   - Nutze color_constants.py
   - Theme Switching teste nach jedem Change
   - ✅ Begonnen: Status/High-Contrast/Selection-Overlay Farben zentralisiert

4. **Planen für Phase 4 QA**
   - Edge Cases auflisten
   - Crash-Testing Matrix definieren
   - Issues in GitHub/Tracker anlegen

5. **Business**
   - Gewerbe-Anmeldung planen (nach 01. Oct)
   - Geschäftskonto recherchieren
   - Lawyer für ToS konsultieren (falls nötig)

---

**TL;DR:**
- ✅ Feature-complete mit Lizenzierung
- ✅ 9 Monate für Stabilität + Performance + Business
- ✅ Oktober 1 = Offizieller Launch
- ✅ Echo Produktentwicklung, nicht gehetzt Hobby
- 🚀 **Das wird real!**

---

## 🧪 VERSION 0.6 → 0.7 TESTING & UPGRADE WORKFLOW

### Nach Phase 2 Week 1 (Jetzt)
**User:** Tests v0.6.0 mit echten Fotos
- [ ] Copy latest build to testing folder
- [ ] User test auf real photo library
- [ ] Document all bugs/edge cases found
- [ ] Create GitHub issues for each bug
- [ ] Rate functionality (which features work perfectly vs. need work)

### Parallel zu Phase 2 Weeks 2-12 (Optimization)
**Developer:** Implements optimizations, fixes bugs from v0.6.0 testing
- [ ] ThreadPool implementation (Week 2)
- [ ] Fix reported bugs from user testing
- [ ] Re-profile after each optimization
- [ ] Measure speedup against baseline

### After Phase 2 Complete (May)
**Integration Phase:**
1. Merge all bug fixes from v0.6.0 testing into main branch
2. Create v0.7.0 release branch
3. Merge Phase 2 optimizations (ThreadPool, batch-tuning, caching)
4. Run full test suite on v0.7.0
5. Create v0.7.0 build (PhotoCleaner_v0.7.0.exe)
6. User re-tests v0.7.0 to verify:
   - All previous bugs are fixed
   - Performance is significantly better (4-7x faster)
   - No new bugs introduced

### Deliverables
- **v0.6.0:** Current stable release (feature-complete)
- **v0.7.0:** Optimized release (40-50% faster, bugs fixed)
- **Testing Report:** Before/After comparison with metrics
- **Ready for v0.8.2:** Algorithm improvements phase

**This approach ensures:**
- Quality: Real-world user feedback before optimization
- Stability: Bugs fixed before performance work
- Validation: Can measure true improvement (v0.6 → v0.7)
- Confidence: v0.7.0 is rock-solid before Phase 3
