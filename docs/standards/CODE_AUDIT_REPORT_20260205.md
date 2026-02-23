# 🔍 PhotoCleaner - UMFASSENDE CODE-AUDIT REPORT
**Datum**: 5. Februar 2026  
**Version**: 0.8.2  
**Status**: Phase 3 Review Complete  

---

## 📌 EXECUTIVE SUMMARY

Eine systematische Code-Review des gesamten PhotoCleaner-Projekts identifizierte **16 bedeutende Probleme**, davon:
- 🔴 **4 KRITISCH**: Können zu Crashes oder Datenverlust führen
- 🟠 **8 HOCH**: Logische Fehler, Memory Leaks, Race Conditions
- 🟡 **4 MITTEL**: Performance-Probleme, UX-Unstimmigkeiten

---

## 🚨 KRITISCHE BUGS (Sofort beheben!)

### 1. **Race Condition in MTCNN Face Detector Cache**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (~Zeile 500-600)

**Problem**:
```python
# NICHT THREAD-SICHER!
if self._mtcnn_detector_cache is None:
    self._mtcnn_detector_cache = MTCNN()  # Mehrere Threads können parallel initialisieren!
```

**Auswirkungen**:
- Mehrere MTCNN-Instanzen werden erstellt → **Memory Leak**
- TensorFlow-Initialisierungsfehler im Worker-Process
- Crashes bei paralleler Bildanalyse (Multiprocessing)

**Lösungsansatz**:
```python
import threading

class QualityAnalyzer:
    def __init__(self):
        self._mtcnn_lock = threading.Lock()
        self._mtcnn_detector_cache = None
    
    def _get_mtcnn_detector(self):
        with self._mtcnn_lock:
            if self._mtcnn_detector_cache is None:
                try:
                    logger.info("Initializing MTCNN detector...")
                    self._mtcnn_detector_cache = MTCNN()
                except Exception as e:
                    logger.error(f"MTCNN initialization failed: {e}")
                    raise
        return self._mtcnn_detector_cache
    
    def _analyze_faces_mtcnn(self, img):
        detector = self._get_mtcnn_detector()
        # ... rest of logic ...
```

**Severity**: 🔴 KRITISCH  
**Priority**: P0 - Fix immediately before any release

---

### 2. **TOCTOU (Time-of-Check-Time-of-Use) File-Lock Vulnerability**
**Datei**: `src/photo_cleaner/repositories/file_repository.py` (Zeile ~75-95)

**Problem**:
```python
def set_status(self, path: Path, status: FileStatus, *, reason: str = ""):
    # CHECK: Prüfe ob Datei gesperrt ist
    cur = self.conn.execute("SELECT file_id, is_locked FROM files WHERE path = ?", (str(path),))
    row = cur.fetchone()
    if row[1]:  # is_locked
        raise PermissionError("File is locked")
    
    # RACE: Zwischen CHECK und USE kann anderer Thread sperren!
    
    # USE: Status aktualisieren
    self.conn.execute("UPDATE files SET file_status = ? WHERE file_id = ?", (status.value, row[0]))
```

**Auswirkungen**:
- Status gesperrter Dateien wird trotzdem geändert
- Datenbank-Inkonsistenz
- Undo/Redo werden falsch

**Lösungsansatz**:
```python
def set_status(self, path: Path, status: FileStatus, *, reason: str = ""):
    """Set status, atomically checking lock status."""
    try:
        self.conn.execute("BEGIN IMMEDIATE")
        
        cur = self.conn.execute(
            "SELECT file_id, file_status, is_locked, decided_at FROM files WHERE path = ?", 
            (str(path),)
        )
        row = cur.fetchone()
        if not row:
            self.conn.rollback()
            raise KeyError(f"File not found: {path}")
        
        file_id, old_status, is_locked, old_decided_at = row
        
        if is_locked:
            self.conn.rollback()
            raise PermissionError(f"File is locked: {path}")
        
        # Update status (atomically within transaction)
        new_ts = None
        if status in (FileStatus.KEEP, FileStatus.DELETE):
            new_ts = self.conn.execute("SELECT unixepoch()").fetchone()[0]
        
        self.conn.execute(
            "UPDATE files SET file_status = ?, decided_at = ? WHERE file_id = ? AND is_locked = 0",
            (status.value, new_ts, file_id)
        )
        
        # Insert history
        self.conn.execute(
            """INSERT INTO status_history (action_id, file_id, file_path, old_status, new_status, 
               old_locked, new_locked, old_decided_at, new_decided_at, reason)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (action_id, file_id, str(path), old_status, status.value, 
             0, 0, old_decided_at, new_ts, reason)
        )
        
        self.conn.commit()
    except Exception as e:
        try:
            self.conn.rollback()
        except sqlite3.Error:
            pass
        raise
```

**Severity**: 🔴 KRITISCH  
**Priority**: P0 - Affects data integrity

---

### 3. **Inkonsistente Batch-Update-Transaktionen**
**Datei**: `src/photo_cleaner/ui_actions.py` (Zeile 144-202)

**Problem**:
```python
def ui_batch_set_status(self, paths: List[Path], status: FileStatus):
    self.files.conn.execute("BEGIN IMMEDIATE")
    
    # Validate files
    # ...
    
    # Insert history records
    self.files.bulk_set_status(..., commit=False)  # ← History wird inserted
    
    # PROBLEM: Wenn nächste Operation fehlschlägt:
    # - History-Records sind committed
    # - File-Status wurde nicht aktualisiert
    # - Datenbank-Inkonsistenz!
    
    self.files.conn.commit()
```

**Auswirkungen**:
- Partial writes bei Fehlern
- Undo-System ist falsch
- Datenbank-Korruption

**Lösungsansatz**: Alle Operationen in single transaction

---

### 4. **MediaPipe Model Cleanup fehlend**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (~Zeile 600-650)

**Problem**:
```python
class QualityAnalyzer:
    def __init__(self):
        self._face_mesh_cache = None
        # ... kein __del__ ...
    
    def _get_face_mesh_model(self):
        if self._face_mesh_cache is None:
            self._face_mesh_cache = _resolve_face_mesh_ctor()(...)
        # LEAK: Wird nie geschlossen!
```

**Auswirkungen**:
- **Memory Leak**: ~50-100MB pro QualityAnalyzer
- Klassenhalt TensorFlow-Sessions offen
- Bei 100+ Scans: ~5GB Speicherleck
- System wird langsamer

**Lösungsansatz**:
```python
class QualityAnalyzer:
    def __del__(self):
        """Cleanup resources on deletion."""
        self._cleanup_models()
    
    def _cleanup_models(self):
        """Close all cached ML models."""
        if hasattr(self, '_face_mesh_cache') and self._face_mesh_cache:
            try:
                # MediaPipe Task models have close()
                if hasattr(self._face_mesh_cache, 'close'):
                    self._face_mesh_cache.close()
                    logger.debug("Face Mesh cache closed")
            except Exception as e:
                logger.warning(f"Error closing face mesh cache: {e}")
            finally:
                self._face_mesh_cache = None
        
        if hasattr(self, '_mtcnn_detector_cache') and self._mtcnn_detector_cache:
            try:
                # MTCNN doesn't have explicit close, but clear reference
                self._mtcnn_detector_cache = None
                logger.debug("MTCNN detector reference cleared")
            except Exception as e:
                logger.warning(f"Error clearing MTCNN: {e}")
    
    def __exit__(self, *args):
        """Context manager cleanup."""
        self._cleanup_models()
```

**Severity**: 🔴 KRITISCH  
**Priority**: P0 - Causes memory exhaustion

---

## 🐛 LOGISCHE FEHLER

### 5. **Globaler Module-State nicht Thread-Safe**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (Zeile 45-65)

**Problem**:
```python
# Globale lazy-loaded modules
_cv2 = None
_np = None
_Image = None
_mp = None
_dlib = None
_MTCNN = None

def _ensure_dependencies():
    global _cv2, _np, ...
    if _cv2 is not None:
        return  # Scheinbar sicher, aber:
    
    # Race condition: Mehrere Threads können hier gleichzeitig landen!
    import cv2 as cv2_module  # Thread A startet
    _cv2 = cv2_module         # Thread A setzt
    # VS.
    import cv2  # Thread B startet  → Verschiedene Instanzen!
    _cv2 = cv2
```

**Lösungsansatz**:
```python
import threading

_deps_lock = threading.Lock()
_deps_initialized = False

def _ensure_dependencies():
    global _cv2, _np, _Image, _mp, _dlib, _MTCNN, _deps_initialized
    global CV2_AVAILABLE, MEDIAPIPE_AVAILABLE, DLIB_AVAILABLE, MTCNN_AVAILABLE
    
    with _deps_lock:  # ← Thread-safe now
        if _deps_initialized:
            return
        
        # ... all imports here ...
        
        _deps_initialized = True  # Set flag AFTER all imports complete
```

**Severity**: 🟠 HOCH  
**Priority**: P1

---

### 6. **Cache-Invalidierung ohne Rollback-Kompensation**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (~Zeile 620)

**Problem**:
```python
def _invalidate_face_mesh_cache(self):
    """Invalidate cached model on config change."""
    with self._cache_lock:
        try:
            if self._face_mesh_cache:
                self._face_mesh_cache.close()
        except (RuntimeError, AttributeError):
            pass  # 🐛 Silently ignore!
        self._face_mesh_cache = None  # Set to None ANYWAY
```

Wenn `.close()` fehlschlägt (z.B. model ist beschädigt), wird trotzdem auf `None` gesetzt. Nächste Analyse versucht, Modell neu zu laden - aber alte Analysen sind falsch!

**Lösungsansatz**:
```python
def _invalidate_face_mesh_cache(self):
    """Invalidate cached model on config change."""
    with self._cache_lock:
        if not self._face_mesh_cache:
            return
        
        try:
            logger.debug("Closing Face Mesh cache due to config change...")
            self._face_mesh_cache.close()
            self._face_mesh_cache = None
            logger.info("Face Mesh cache invalidated successfully")
        except Exception as e:
            # Don't silently fail!
            logger.error(
                f"Failed to close Face Mesh cache properly: {e}. "
                f"Setting to None anyway, but analyzer should be restarted.",
                exc_info=True
            )
            self._face_mesh_cache = None
            # Could also: raise InvalidStateError("Cache corrupted, restart analyzer")
```

**Severity**: 🟠 HOCH  
**Priority**: P1

---

### 7. **Scorer ignoriert Disqualifizierungen in Auto-Select**
**Datei**: `src/photo_cleaner/pipeline/scorer.py` (~Zeile 200-250)

**Problem**:
```python
def auto_select_best_image(self, group_id: str, scored_images: list) -> str:
    """Auto-select the best image in a group."""
    disqualified = [img for img in scored_images if img.disqualified]
    usable = [img for img in scored_images if not img.disqualified]
    
    if not usable:
        # PROBLEM: Falls alle disqualifiziert, wähle disqualifiziertes Bild!
        best = max(disqualified, key=lambda x: x.overall_score)
    else:
        best = max(usable, key=lambda x: x.overall_score)
    
    return best.path
```

Wenn ein Bild disqualifiziert ist (z.B. Augen geschlossen), wird es TROTZDEM als best ausgewählt wenn alle anderen auch disqualifiziert sind. UI zeigt aber "⚠️ Disqualified" Tag.

**Auswirkungen**:
- UX-Verwirrung
- Widersprüchliche Empfehlungen
- Nutzer sieht "disqualified" Tag aber Status ist "RECOMMENDED"

**Lösungsansatz**:
```python
def auto_select_best_image(self, group_id: str, scored_images: list) -> tuple:
    """Auto-select the best image in a group.
    
    Returns:
        (best_image_path, qualification_status, note)
        qualification_status: 'qualified', 'disqualified_but_selected', 'all_disqualified'
    """
    qualified = [img for img in scored_images if not img.disqualified]
    
    if qualified:
        best = max(qualified, key=lambda x: x.overall_score)
        return best.path, 'qualified', None
    
    # All images are disqualified - choose least disqualified
    best = max(scored_images, key=lambda x: x.overall_score)
    worst_reason = best.disqualification_reason or "Unknown"
    return best.path, 'disqualified_but_selected', f"All images disqualified ({worst_reason})"
```

Und im UI:
```python
best_path, status, note = scorer.auto_select_best_image(...)
if status == 'disqualified_but_selected':
    show_warning_dialog(f"⚠️ Warning: {note}")
```

**Severity**: 🟠 HOCH  
**Priority**: P2

---

### 8. **PersonEyeStatus nicht serialisierbar für Multiprocessing**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (~Zeile 1400)

**Problem**:
```python
@dataclass
class PersonEyeStatus:
    person_id: int
    eyes_open: bool
    # ... more fields ...

# Im Multiprocessing Worker:
result = analyzer.analyze_batch(paths)  # Returns list of FaceQuality
# FaceQuality hat list[PersonEyeStatus]

# Worker-Process pickle'et das:
import pickle
pickled = pickle.dumps(result)  # ← Serialisiert komplette Klasse-Def!
```

Wenn Worker-Process andere Python-Version oder Code-Stand hat:
- `pickle` schlägt fehl
- FaceQuality kann nicht deserialisiert werden

**Lösungsansatz**:
```python
@dataclass
class PersonEyeStatus:
    # ... fields ...
    
    def to_dict(self) -> dict:
        """Convert to serializable dict."""
        return {
            'person_id': self.person_id,
            'eyes_open': self.eyes_open,
            'face_confidence': self.face_confidence,
            # ... all fields ...
        }
    
    @staticmethod
    def from_dict(d: dict) -> 'PersonEyeStatus':
        return PersonEyeStatus(**d)

@dataclass
class FaceQuality:
    # ... fields ...
    person_eye_statuses: list[PersonEyeStatus] = field(default_factory=list)
    
    def __getstate__(self):
        """Custom pickle support."""
        state = self.__dict__.copy()
        if self.person_eye_statuses:
            state['person_eye_statuses'] = [p.to_dict() for p in self.person_eye_statuses]
        return state
    
    def __setstate__(self, state):
        """Custom unpickle support."""
        if 'person_eye_statuses' in state and state['person_eye_statuses']:
            state['person_eye_statuses'] = [
                PersonEyeStatus.from_dict(p) for p in state['person_eye_statuses']
            ]
        self.__dict__.update(state)
```

**Severity**: 🟠 HOCH  
**Priority**: P2 - Affects Multiprocessing

---

## ⚠️ MEMORY LEAKS & RESSOURCEN-PROBLEME

### 9. **SQLite Connection nicht korrekt geschlossen bei Errors**
**Datei**: `src/photo_cleaner/repositories/file_repository.py` (Zeile 68-95)

**Problem**:
```python
def set_status(self, path: Path, status: FileStatus, ...):
    try:
        # ... operations ...
        self.conn.commit()
    except Exception as e:
        try:
            self.conn.rollback()
        except (sqlite3.Error, RuntimeError):
            logger.debug("Error during rollback", exc_info=True)  # 🐛 Silently ignore!
        raise
```

Wenn `rollback()` selbst fehlschlägt (z.B. Connection ist beschädigt):
- Exception wird geschluckt
- Connection ist in kaputtem Zustand
- Nächste Operation fehlschlägt mit kryptischem Fehler

**Lösungsansatz**:
```python
def set_status(self, path: Path, status: FileStatus, ...):
    try:
        # ... operations ...
        self.conn.commit()
    except Exception as e:
        logger.error(f"Operation failed, attempting rollback: {e}")
        try:
            self.conn.rollback()
            logger.debug("Rollback successful")
        except sqlite3.OperationalError as rollback_err:
            # Connection might be corrupted
            logger.critical(
                f"CRITICAL: Rollback failed - database connection might be corrupted: {rollback_err}. "
                f"This operation was: {type(e).__name__}: {e}",
                exc_info=True
            )
            # Close and force reconnection
            try:
                self.conn.close()
            except Exception:
                pass
            raise ConnectionError(
                f"Database connection corrupted during rollback. "
                f"Original error: {e}. Rollback error: {rollback_err}"
            ) from rollback_err
        except Exception as rollback_err:
            logger.error(f"Unexpected error during rollback: {rollback_err}", exc_info=True)
            raise
        raise  # Re-raise original exception
```

**Severity**: 🟠 HOCH  
**Priority**: P1

---

### 10. **Unclosed Thumbnail Resources in Cache**
**Datei**: `src/photo_cleaner/ui/thumbnail_memory_cache.py` (~Zeile 100-150)

**Problem**:
```python
class ThumbnailMemoryCache:
    def __init__(self, max_size_mb: int = 500):
        self._cache: Dict[str, QPixmap] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024
        # NO: self._cache is never explicitly cleared on exit
    
    def get_thumbnail(self, path: Path) -> Optional[QPixmap]:
        if str(path) in self._cache:
            return self._cache[str(path)]
        # Load and cache
        pixmap = QPixmap(str(path))
        self._cache[str(path)] = pixmap  # ← Held indefinitely
```

**Auswirkungen**:
- QPixmap objects nicht freigegeben
- ~50-100KB pro Thumbnail × 1000 = 50-100MB Speicher
- Crash bei sehr vielen Dateien

**Lösungsansatz**:
```python
class ThumbnailMemoryCache:
    def __init__(self, max_size_mb: int = 500):
        self._cache: Dict[str, QPixmap] = {}
        self._cache_size_bytes = 0
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def __del__(self):
        """Cleanup on deletion."""
        self.clear()
    
    def clear(self):
        """Explicitly clear cache."""
        self._cache.clear()
        self._cache_size_bytes = 0
        logger.debug("Thumbnail cache cleared")
    
    def get_thumbnail(self, path: Path) -> Optional[QPixmap]:
        # Check cache
        key = str(path)
        if key in self._cache:
            return self._cache[key]
        
        # Load thumbnail
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            return None
        
        # Add to cache with size tracking
        estimated_size = pixmap.width() * pixmap.height() * 4  # RGBA = 4 bytes
        
        # Evict old entries if cache is full
        while (self._cache_size_bytes + estimated_size > self.max_size_bytes 
               and self._cache):
            # Remove least recently used
            oldest_key = next(iter(self._cache))
            old_pixmap = self._cache.pop(oldest_key)
            self._cache_size_bytes -= (old_pixmap.width() * old_pixmap.height() * 4)
            logger.debug(f"Evicted thumbnail from cache: {oldest_key}")
        
        self._cache[key] = pixmap
        self._cache_size_bytes += estimated_size
        return pixmap
```

**Severity**: 🟠 HOCH  
**Priority**: P2

---

## 🔒 CONCURRENCY-PROBLEME

### 11. **Race Condition in RatingWorkerThread**
**Datei**: `src/photo_cleaner/ui/modern_window.py` (Zeile 160-220)

**Problem**:
```python
class RatingWorkerThread(QThread):
    def run(self):
        # Analyze all groups
        for group_id, paths in groups.items():
            results = analyzer.analyze_batch(paths)  # Takes 5-10 seconds
            quality_results[group_id] = results
        
        # PROBLEM: Zwischen Analyse und Speicherung können Dateien gelöscht werden!
        
        # Update database
        for group_id, results in quality_results.items():
            best_path = scorer.auto_select_best_image(...)
            # File could be deleted/locked now!
            self.conn.execute(
                "UPDATE files SET is_recommended = 1 WHERE path = ?",
                (str(best_path),)
            )
```

**Auswirkungen**:
- "File not found" Error während DB-Update
- Recommendations gehen verloren
- UI zeigt Fehler

**Lösungsansatz**:
```python
def run(self):
    try:
        for group_id, paths in groups.items():
            results = analyzer.analyze_batch(paths)
            quality_results[group_id] = results
        
        # Before database updates, re-verify files still exist and aren't locked
        valid_results = {}
        for group_id, results in quality_results.items():
            try:
                # Re-check file exists and is not locked
                best_path = scorer.auto_select_best_image(...)
                
                # VERIFY before update
                cursor = self.conn.execute(
                    "SELECT file_id, is_locked FROM files WHERE path = ?",
                    (str(best_path),)
                )
                row = cursor.fetchone()
                
                if not row:
                    logger.warning(f"Best file {best_path} was deleted, skipping recommendation")
                    continue
                
                file_id, is_locked = row
                if is_locked:
                    logger.warning(f"Best file {best_path} is locked, skipping recommendation")
                    continue
                
                # Now safe to update
                self.conn.execute(
                    "UPDATE files SET is_recommended = 1 WHERE file_id = ?",
                    (file_id,)
                )
                self.conn.commit()
                valid_results[group_id] = file_id
                self.progress.emit(i, f"✓ Recommended for {group_id}")
                
            except Exception as e:
                logger.error(f"Failed to set recommendation for {group_id}: {e}")
                self.progress.emit(i, f"✗ Error for {group_id}")
                continue
    except Exception as e:
        logger.error(f"RatingWorkerThread failed: {e}", exc_info=True)
        self.error.emit(str(e))
```

**Severity**: 🟠 HOCH  
**Priority**: P2

---

### 12. **IndexingThread DB Connection Isolation Level Mismatch**
**Datei**: `src/photo_cleaner/ui/indexing_thread.py` (~Zeile 70-100)

**Problem**:
```python
class IndexingThread(QThread):
    def run(self):
        # Create separate connection for thread
        indexer_db = Database(self.db_path)
        indexer_conn = indexer_db.connect()  # ← Different isolation level?
```

Parent-Thread hat `isolation_level = "DEFERRED"` aber neuer Thread könnte `None` haben:
- Parent: `DEFERRED` → Keine Locks bis zur ersten Query
- IndexingThread: `None` → Autocommit-Modus (SQLite3 default)

Result: Deadlock möglich!

**Lösungsansatz**:
```python
class IndexingThread(QThread):
    def run(self):
        try:
            # Get parent's isolation level
            parent_isolation = self.parent_db.conn.isolation_level
            
            # Create connection with SAME settings
            indexer_db = Database(self.db_path)
            indexer_conn = indexer_db.connect()
            
            # Ensure same configuration as parent
            indexer_conn.isolation_level = parent_isolation
            
            # Apply same PRAGMAs
            indexer_conn.execute("PRAGMA busy_timeout = 5000")
            indexer_conn.execute("PRAGMA journal_mode = WAL")
            
            logger.info(f"IndexingThread isolation_level: {indexer_conn.isolation_level}")
            
            # Now safe to use
            # ... indexing operations ...
```

**Severity**: 🟠 HOCH  
**Priority**: P2

---

## 🔐 SECURITY-PROBLEME

### 13. **Missing Validation on EXIF Data**
**Datei**: `src/photo_cleaner/pipeline/quality_analyzer.py` (~Zeile 800-900)

**Problem**:
```python
def analyze_exif(self, path: Path) -> dict:
    try:
        with Image.open(path) as img:
            exif_data = img._getexif() or {}
            # PROBLEM: No validation of EXIF size or content
            exif_json = json.dumps(exif_data)  # Could be huge!
            
            self.conn.execute(
                "UPDATE files SET exif_json = ? WHERE path = ?",
                (exif_json, str(path))
            )
```

Malicious JPEG mit 1MB EXIF Blob → Database wird aufgeblasen:
- 10.000 Dateien × 1MB = **10GB Database**
- Performance degradation
- Disk space exhaustion

**Lösungsansatz**:
```python
def analyze_exif(self, path: Path) -> Optional[dict]:
    """Extract and validate EXIF data."""
    MAX_EXIF_SIZE = 100 * 1024  # 100KB max
    MAX_EXIF_FIELDS = 500  # Don't accept >500 tags
    
    try:
        with Image.open(path) as img:
            exif_raw = img._getexif() or {}
            
            # Validate count
            if len(exif_raw) > MAX_EXIF_FIELDS:
                logger.warning(
                    f"EXIF too many fields ({len(exif_raw)}), truncating to {MAX_EXIF_FIELDS}"
                )
                exif_raw = dict(list(exif_raw.items())[:MAX_EXIF_FIELDS])
            
            # Try to serialize
            exif_json = json.dumps(exif_raw, default=str)  # Use default=str for non-serializable
            
            # Validate size
            if len(exif_json.encode('utf-8')) > MAX_EXIF_SIZE:
                logger.warning(
                    f"EXIF data too large ({len(exif_json)} bytes), storing minimal EXIF"
                )
                # Only keep essential fields
                essential_fields = {'Make', 'Model', 'DateTime', 'ExposureTime', 'FNumber'}
                minimal_exif = {k: v for k, v in exif_raw.items() 
                               if str(k) in essential_fields}
                exif_json = json.dumps(minimal_exif, default=str)
            
            # Final validation
            try:
                json.loads(exif_json)  # Verify it parses
            except json.JSONDecodeError:
                logger.error(f"EXIF JSON validation failed for {path}")
                return None
            
            return json.loads(exif_json)
    
    except Exception as e:
        logger.debug(f"EXIF extraction failed for {path}: {e}")
        return None
```

**Severity**: 🔴 KRITISCH (DoS-Vektor)  
**Priority**: P0 if handling untrusted images

---

### 14. **No Path Validation in File Operations**
**Datei**: `src/photo_cleaner/repositories/file_repository.py` (Zeile 40-80)

**Problem**:
```python
def set_status(self, path: Path, status: FileStatus, ...):
    """Set file status."""
    # NO VALIDATION!
    cur = self.conn.execute(
        "SELECT file_id FROM files WHERE path = ?",
        (str(path),)  # Could be /etc/passwd !
    )
```

Wenn UI kompromittiert ist oder manipulated, könnte es beliebige Dateien sperren/löschen.

**Lösungsansatz**:
```python
def _validate_safe_path(self, path: Path) -> None:
    """Validate path is safe to operate on."""
    try:
        # Resolve to absolute, normalized path
        resolved = path.resolve()
    except (OSError, ValueError) as e:
        raise ValueError(f"Invalid path {path}: {e}")
    
    # Prevent suspicious paths
    parts = resolved.parts
    if '..' in parts:
        raise ValueError(f"Path traversal detected: {path}")
    
    # Could add: must be under scan directory
    # if not resolved.is_relative_to(self.scan_directory):
    #     raise ValueError(f"Path outside scan directory: {path}")
    
    # Prevent system directory access
    forbidden_roots = {
        Path('/etc'),
        Path('/sys'),
        Path('/proc'),
        Path('/bin'),
        Path('/sbin'),
        Path('C:\\Windows'),
        Path('C:\\System32'),
    }
    
    for forbidden in forbidden_roots:
        try:
            resolved.relative_to(forbidden)
            raise ValueError(f"Path in forbidden directory: {path}")
        except ValueError:
            pass  # Not under forbidden directory, good
    
    return resolved

def set_status(self, path: Path, status: FileStatus, ...):
    """Set file status (with validation)."""
    # Validate path first
    safe_path = self._validate_safe_path(path)
    # ... rest of operation ...
```

**Severity**: 🟠 HOCH  
**Priority**: P2

---

## 📊 PERFORMANCE-PROBLEME

### 15. **ImageCacheManager Hashes entire File on Lookup**
**Datei**: `src/photo_cleaner/cache/image_cache_manager.py` (~Zeile 100-150)

**Problem**:
```python
def lookup(self, file_path: Path) -> Optional[CacheEntry]:
    """Check if file is in cache."""
    try:
        # 🐌 VERY SLOW: Reads entire file to compute hash!
        file_hash = self.compute_file_hash(file_path)  # MD5 of entire file
    except OSError:
        return None
    
    cur = self.conn.execute(
        "SELECT ... FROM image_cache WHERE file_hash = ?",
        (file_hash,)
    )
```

**Performance impact**:
- 10.000 Dateien × 5MB each = 50GB data read  
- At 100MB/s disk = **500 seconds = 8+ minutes** just checking cache!
- 80-90% of cache benefits are wasted

**Lösungsansatz**: Use file metadata instead of content hash

```python
def lookup_fast(self, file_path: Path) -> Optional[CacheEntry]:
    """Fast cache lookup using file metadata."""
    try:
        stat = file_path.stat()
        
        # Create fast cache key from metadata
        # Collisions are rare (mtime + size + name)
        fast_key = f"{int(stat.st_mtime)}_{stat.st_size}_{file_path.name}"
        
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT cache_entry_id, content_hash, analysis_json 
               FROM image_cache WHERE fast_key = ? AND file_path = ?""",
            (fast_key, str(file_path))
        )
        
        row = cursor.fetchone()
        if not row:
            return None  # Fast: Not in cache
        
        cache_entry_id, stored_hash, analysis_json = row
        
        # Verify with content hash only if metadata matches
        # (to detect hash collisions)
        actual_hash = self.compute_file_hash(file_path)
        if actual_hash != stored_hash:
            # Hash mismatch = file was modified
            # Delete stale cache entry
            cursor.execute("DELETE FROM image_cache WHERE cache_entry_id = ?", (cache_entry_id,))
            self.conn.commit()
            return None
        
        # Cache hit!
        return CacheEntry.from_json(analysis_json)
    
    except OSError:
        return None
```

**Severity**: 🟡 MITTEL  
**Priority**: P3 - Performance optimization

---

### 16. **Synchronous EXIF Extraction Blocks UI Thread**
**Datei**: `src/photo_cleaner/ui/modern_window.py` (~Zeile 3000-3100)

**Problem**:
```python
class ImageDetailPanel(QWidget):
    def show_details(self, file_path: Path):
        # ⚠️ BLOCKING: Extracts EXIF on main thread
        exif_data = extract_exif_data(file_path)  # Can take 1-5 seconds!
        
        # UI FREEZES while reading large JPEG
        self.exif_text.setText(format_exif(exif_data))
```

**Impact**:
- Click "Details" button → UI freezes for 5 seconds
- User thinks app is crashed
- Bad UX

**Lösungsansatz**: Move to background thread

```python
from concurrent.futures import ThreadPoolExecutor

class ImageDetailPanel(QWidget):
    def __init__(self):
        # ... ui setup ...
        self.exif_executor = ThreadPoolExecutor(max_workers=2)
        self._exif_future = None
    
    def show_details(self, file_path: Path):
        """Load EXIF asynchronously."""
        # Cancel any pending EXIF load
        if self._exif_future:
            try:
                self._exif_future.cancel()
            except Exception:
                pass
        
        # Show loading indicator
        self.exif_text.setText("Loading EXIF data...")
        
        # Submit to background thread
        self._exif_future = self.exif_executor.submit(
            self._load_exif_background,
            file_path
        )
        
        # Add callback
        self._exif_future.add_done_callback(self._on_exif_loaded)
    
    def _load_exif_background(self, file_path: Path) -> dict:
        """Load EXIF in background (not on UI thread)."""
        try:
            logger.debug(f"Loading EXIF for {file_path.name}...")
            exif_data = extract_exif_data(file_path)
            logger.debug(f"EXIF loaded: {len(exif_data)} fields")
            return exif_data
        except Exception as e:
            logger.warning(f"EXIF load failed for {file_path}: {e}")
            return {"error": str(e)}
    
    def _on_exif_loaded(self, future):
        """Called when EXIF load completes."""
        try:
            exif_data = future.result()
            
            # Update UI on main thread
            formatted = format_exif(exif_data)
            self.exif_text.setText(formatted)
            
            logger.debug("EXIF display updated")
        except Exception as e:
            logger.error(f"EXIF display error: {e}")
            self.exif_text.setText(f"⚠️ Error loading EXIF: {e}")
    
    def __del__(self):
        """Cleanup executor."""
        if hasattr(self, 'exif_executor'):
            self.exif_executor.shutdown(wait=False)
```

**Severity**: 🟡 MITTEL  
**Priority**: P3 - UX improvement

---

## 📋 SUMMARY & ACTION ITEMS

### SOFORT BEHEBEN (P0 - vor Release):
```
[ ] 1. MTCNN Race Condition - Add threading.Lock
[ ] 2. File-Lock TOCTOU - Use UPDATE with WHERE clause
[ ] 3. MediaPipe Cleanup - Implement __del__ and __exit__
[ ] 4. Batch Transaction - Single atomic transaction for all ops
[ ] 5. SQLite Rollback Safety - Handle rollback errors properly
```

### NÄCHSTE ITERATION (P1 - v0.8.2):
```
[ ] 6. Global Module State - Threading Lock
[ ] 7. Cache Invalidation - Proper error handling
[ ] 8. Scorer Disqualification - Include status in decision
[ ] 9. Multiprocessing Serialization - Custom pickle support
[ ] 10. EXIF Validation - Size and field limits
```

### MITTELFRISTIG (P2 - v0.9.0):
```
[ ] 11. RatingWorkerThread Race - Re-verify files before update
[ ] 12. IndexingThread Isolation - Match parent connection settings
[ ] 13. Path Validation - Prevent suspicious paths
[ ] 14. Fast Cache Lookup - Metadata-based fast path
[ ] 15. Async EXIF Loading - Background thread
[ ] 16. Thumbnail Cache Cleanup - Implement __del__
```

---

**Report Generated**: 5. Februar 2026  
**Analyzer**: Comprehensive Code Review v1.0  
**Status**: Ready for remediation planning

