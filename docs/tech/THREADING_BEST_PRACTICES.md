# Threading Best Practices für PhotoCleaner UI

**Erstellt:** Feb 22, 2026  
**Problem:** UI-Freeze "keine Rückmeldung" zwischen Pipeline-Phasen  
**Lösung:** Korrekte Signal-Timing, Dialog-Visibility, Immediate Progress

---

## 🎯 Core Principle: UI-Thread darf NIE blockieren

Windows markiert ein Fenster als "Keine Rückmeldung", wenn der UI-Thread:
- >2 Sekunden keine Events verarbeitet
- Keine Window Messages verarbeitet (WM_PAINT, WM_TIMER, etc.)
- In synchronem Code blockiert (ohne processEvents())

**ZIEL:** Jede heavy Operation MUSS in einem Worker-Thread laufen UND regelmäßig Progress-Signale emittieren.

---

## ✅ DO: Korrekte Worker-Thread Implementierung

### 1. Immediate Progress Signal - SOFORT nach Thread-Start

**FALSCH** ❌ (Silent Init):
```python
def run(self):
    # 2-3 Sekunden stille Initialisierung - USER SIEHT "keine Rückmeldung"
    analyzer = QualityAnalyzer(use_face_mesh=True)
    scorer = GroupScorer(top_n=3)
    
    # ERST JETZT Progress-Signal - ZU SPÄT!
    self.progress.emit(87, "Models ready...")
```

**RICHTIG** ✅ (Immediate Signal):
```python
def run(self):
    import time
    start_time = time.monotonic()
    
    # Database queries (fast)
    conn = db.connect()
    groups = query_groups(conn)
    
    # SOFORT Status emittieren - zeigt User dass Thread lebt
    self.progress.emit(87, f"Modelle werden geladen... 0/{total}")
    
    # Jetzt Heavy Init mit Feedback
    analyzer = QualityAnalyzer(use_face_mesh=True)
    init_time = time.monotonic() - start_time
    logger.info(f"[WORKER] QualityAnalyzer init: {init_time:.2f}s")
    
    # Nach JEDEM schweren Schritt: Signal
    self.progress.emit(88, f"QualityAnalyzer bereit, lade GroupScorer...")
    scorer = GroupScorer(top_n=3)
    
    self.progress.emit(90, f"Modelle aufwärmen...")
```

### 2. Dialog Visibility - Explizit Sichtbar Machen

**FALSCH** ❌ (Assume Dialog is Shown):
```python
def _on_duplicate_finder_finished(self):
    progress = self._post_indexing_progress_dialog
    progress.setLabelText("Bilder werden bewertet...")
    
    self._rating_thread = RatingWorkerThread(...)
    self._rating_thread.start()
    # Dialog KÖNNTE noch invisible sein!
```

**RICHTIG** ✅ (Force Visibility):
```python
def _on_duplicate_finder_finished(self):
    progress = self._post_indexing_progress_dialog
    progress.setLabelText("Bilder werden bewertet...")
    
    self._rating_thread = RatingWorkerThread(...)
    self._rating_thread.start()
    
    # EXPLICIT show() falls Dialog minimiert/invisible
    if progress and not progress.isVisible():
        logger.info("[UI] Dialog not visible - showing explicitly")
        progress.show()
    
    # Force Qt Event Loop BEFORE worker initializes
    from PySide6.QtWidgets import QApplication
    QApplication.processEvents()
    logger.info("[UI] Dialog should now be visible")
```

### 3. QApplication.processEvents() - Event-Loop Forcieren

**Wann verwenden:**
- Nach `thread.start()` → forciert Dialog-Rendering
- Nach `dialog.show()` → stellt sicher dass Fenster sichtbar wird
- Nach mehreren UI-Updates hintereinander → verhindert "Stau"

**FALSCH** ❌ (Too Much):
```python
for i in range(1000):
    self.label.setText(f"{i}")
    QApplication.processEvents()  # ❌ Zu oft! Macht UI LANGSAMER
```

**RICHTIG** ✅ (Strategic):
```python
# Vor kritischer Heavy-Operation
dialog.show()
QApplication.processEvents()  # ✅ Dialog ist jetzt garantiert visible

thread.start()
QApplication.processEvents()  # ✅ Thread-Start visible, bevor Worker silent wird
```

### 4. Progress Throttling - Nicht zu viele Signals

Im **UI-Thread** (Signal-Handler):
```python
def _on_rating_progress(self, pct: int, status: str):
    progress = self._post_indexing_progress_dialog
    if progress:
        # Throttle zu 100ms (10 updates/sec max)
        self._update_progress_dialog(progress, value=pct, label=status)

def _update_progress_dialog(self, dialog, *, value=None, label=None, force=False):
    if not force:
        now = time.monotonic()
        if now - self._progress_update_ts < 0.1:  # 100ms throttle
            return
        self._progress_update_ts = now
    
    if value is not None:
        dialog.setValue(value)
    if label is not None:
        dialog.setLabelText(label)
```

Im **Worker-Thread**:
```python
# Emittiere Progress alle 5-10 Bilder (nicht jedes!)
for i, image in enumerate(images):
    process(image)
    
    if i % 5 == 0:  # Alle 5 Bilder
        pct = 87 + int(7 * (i / total))
        self.progress.emit(min(94, pct), f"Analyzing... {i}/{total}")
```

---

## ❌ DON'T: Häufige Anti-Patterns

### 1. Heavy Init im UI-Thread

```python
# ❌ NEVER - Blockiert UI-Thread komplett!
def _on_button_click(self):
    analyzer = QualityAnalyzer(use_face_mesh=True)  # 2-3 Sekunden!
    result = analyzer.analyze(image)
    self.show_result(result)
```

### 2. Worker ohne Progress-Signale

```python
# ❌ NEVER - Silent Worker = "keine Rückmeldung"
class BadWorkerThread(QThread):
    finished = Signal(dict)
    
    def run(self):
        # 5 Minuten Arbeit ohne einziges Signal
        for i in range(1000):
            heavy_operation()
        
        self.finished.emit(result)  # User hat längst abgebrochen!
```

### 3. Synchrone Long-Running Calls

```python
# ❌ NEVER - Blockiert UI bis Timeout
def _on_action(self):
    result = requests.get("http://slow-api.com", timeout=30)  # 30s Block!
    self.process(result)

# ✅ Richtig: Asynchron in Worker
class ApiWorkerThread(QThread):
    finished = Signal(object)
    
    def run(self):
        result = requests.get("http://slow-api.com", timeout=30)
        self.finished.emit(result)
```

### 4. Synchrones File I/O im UI-Thread (CRITICAL!)

```python
# ❌ CRITICAL ANTI-PATTERN - 45 Sekunden UI-Freeze!
# Real-world bug from Feb 22, 2026
def _render_groups(self):
    for grp in self.groups:  # 136 groups
        # JEDES get_thumbnail() = 300ms Disk I/O + Image Resize!
        thumb_path = get_thumbnail(grp.sample_path, (96, 96))  # ❌ SYNC I/O!
        pixmap = QPixmap(str(thumb_path)).scaled(48, 48)        # ❌ SYNC Decode!
        item.setIcon(QIcon(pixmap))
    # Result: 136 × 300ms = 40+ seconds "keine Rückmeldung"

# ✅ FIX 1: Don't load thumbnails at all (use placeholders)
def _render_groups(self):
    for grp in self.groups:
        # Use standard icon - instant rendering
        item.setIcon(self.style().standardIcon(QStyle.SP_FileIcon))

# ✅ FIX 2 (Better): Async lazy loading for visible items only
def _render_groups(self):
    for grp in self.groups:
        item = QListWidgetItem(label)
        # Defer thumbnail loading to visibility event
        item.setData(Qt.UserRole, grp.sample_path)
    
    # Later: When item becomes visible, load thumbnail in worker thread
```

**Why this matters:**
- Single `Image.open()` = 50-200ms (SSD) or 200-500ms (HDD)
- Multiply by 100+ items = **10-50 seconds UI freeze**
- Windows marks window as "Keine Rückmeldung" after 2-3 seconds
- User thinks app crashed

**Golden Rule:** ANY file I/O MUST be in worker thread or lazy-loaded.

---

## 🧪 Testing Checklist: UI-Responsiveness

Nach JEDER Änderung an Worker-Threads:

- [ ] **Smoke Test: "keine Rückmeldung"**
  - Start Analysis Pipeline
  - Zwischen jeder Phase (<1 Sekunde vergehen)
  - Fenster darf NIEMALS "keine Rückmeldung" zeigen
  
- [ ] **Progress Dialog: Sofort Sichtbar**
  - Dialog erscheint innerhalb 100-300ms
  - Erster Text/Progress sofort lesbar (nicht verzögert)
  
- [ ] **Progress Updates: Regelmäßig**
  - Mindestens 1 Update alle 500ms (während Heavy-Operation)
  - Text/Percentage ändert sich sichtbar
  
- [ ] **Cancel Button: Responsive**
  - Klick auf "Abbrechen" reagiert innerhalb 1 Sekunde
  - Thread stoppt tatsächlich (check mit Logs)

- [ ] **Multi-Machine Test**
  - Test auf min. 2 verschiedenen Windows-Versionen
  - Test mit langsamen CPU (i5-7xxx oder älter)
  - Test mit vielen Hintergrund-Prozessen (simuliert "langsames" System)

---

## 📊 Diagnostic Logging Pattern

Verwende **[TAG]** Prefixes für Thread-Diagnose:

```python
# UI-Thread
logger.info("[UI] Starting RatingWorkerThread...")
logger.info("[UI] Processing Qt events...")
logger.info("[UI] Dialog should be visible")

# Worker-Thread
logger.info("[WORKER] Thread started, connecting DB...")
logger.info("[WORKER] DB connected in {elapsed:.2f}s")
logger.info("[WORKER] QualityAnalyzer init: {init_time:.2f}s")
logger.info("[WORKER] GroupScorer init: {scorer_time:.2f}s")
logger.info("[WORKER] Total init time: {total:.2f}s")
```

**Timing-Diagnose** mit `time.monotonic()`:
```python
import time

start = time.monotonic()
heavy_operation()
elapsed = time.monotonic() - start
logger.info(f"[WORKER] Operation completed in {elapsed:.2f}s")

if elapsed > 1.0:
    logger.warning(f"[WORKER] Slow operation detected: {elapsed:.2f}s")
```

---

## 🔍 Debugging "keine Rückmeldung"

Wenn User "keine Rückmeldung" sieht:

1. **Check Logs: Wann war letztes Signal?**
   ```
   [UI] Starting RatingWorkerThread...
   [UI] Processing Qt events...
   [UI] Dialog should be visible
   
   # GAP von 2-3 Sekunden hier? → Worker emittiert nicht sofort!
   
   [WORKER] Thread started...
   [WORKER] QualityAnalyzer init: 2.34s  # ← Zu lange ohne Signal!
   ```

2. **Fix: Sofortiges Signal VOR Heavy-Init**
   ```python
   def run(self):
       # Database queries
       groups = query_groups()
       
       # ✅ HIER sofort Signal!
       self.progress.emit(87, "Modelle werden geladen...")
       
       # Jetzt Heavy-Init
       analyzer = QualityAnalyzer(...)
   ```

3. **Verify Dialog Visibility**
   ```python
   if progress and not progress.isVisible():
       progress.show()  # ← Explizit sichtbar machen
   ```

4. **Add processEvents() after thread.start()**
   ```python
   thread.start()
   QApplication.processEvents()  # ← Force Event-Loop
   ```

---

## 📚 References

- **Original Issue:** Feb 22, 2026 - "keine Rückmeldung" zwischen Hashing → Bewertung
- **Root Cause:** QualityAnalyzer.__init__() 2-3s ohne Progress-Signale
- **Fix Commit:** modern_window.py Lines 159-207 (RatingWorkerThread.run), Lines 2662-2692 (_on_duplicate_finder_finished)
- **Qt Documentation:** [QThread](https://doc.qt.io/qt-6/qthread.html), [QProgressDialog](https://doc.qt.io/qt-6/qprogressdialog.html)

---

## 🎯 Summary: Golden Rules

1. **Heavy operations ALWAYS in Worker-Thread (nie UI-Thread)**
2. **IMMEDIATE progress signal nach Thread.start() (<500ms)**
3. **Progress-Updates während Init (nicht erst nach Init)**
4. **Dialog explizit show() + processEvents() nach thread.start()**
5. **Timing-Logs für alle Operations >500ms**
6. **Test auf mehreren Maschinen (langsame CPU wichtig!)**

**Ziel:** Kein "keine Rückmeldung", kein Freeze, jeder Dialog sofort sichtbar.
