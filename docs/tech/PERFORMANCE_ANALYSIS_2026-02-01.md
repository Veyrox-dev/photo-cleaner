# Performance Analysis – PhotoCleaner (2026-02-01)

## Kontext
- Beobachtung: Lauf steht bei ~19/132 Bildern; geschätzte Restlaufzeit ~8 Stunden.
- Log-Auszug zeigt MTCNN-Detektion auf 30.7MP HEIC-Bildern mit mehreren Minuten pro Bild.

## Kurzantwort auf die Stop-Frage
- **Bei Abbruch des aktuellen Auto-Rate-Laufs werden die Qualitätsbewertungen höchstwahrscheinlich nicht gespeichert.**
- Grund: In `ModernWindow._auto_rate_images()` werden die Ergebnisse erst **nachdem alle Gruppen** analysiert wurden gesammelt, dann in einem Schritt durch `GroupScorer.apply_scores_to_db()` und die anschließenden `UPDATE`-Statements geschrieben. Ein Abbruch mitten im Lauf verhindert diese Sammel- und Schreibphase.
- **Duplikat-Gruppen bleiben sichtbar**, aber **ohne Bewertungen/Empfehlungen**.

## Pipeline (vereinfacht, realer Ablauf)
1. **Indexing & Hashing** (ProcessPool) – `PhotoIndexer.index_folder()`
2. **Duplikat-Gruppenbildung** – `DuplicateFinder.build_groups()`
3. **Auto-Rating** (sequentiell, UI-Thread)
   - `QualityAnalyzer.warmup()`
   - `QualityAnalyzer.analyze_batch()` → `analyze_image()` je Bild
   - `GroupScorer.score_multiple_groups()`
   - `GroupScorer.apply_scores_to_db()` + DB-Updates

## Logbeobachtungen (Ausschnitt)
- 30.7MP HEIC (8160×3768)
- Zwischen „Using MTCNN for face detection“ und „MTCNN: faces detected“ liegen **1–7 Minuten**
- Beispiel:
  - Start MTCNN: 12:26:06
  - Ergebnis: 12:33:08
  - **~7 Minuten für ein Bild**

## Haupt-Engpass (höchste Wahrscheinlichkeit für 7-Minuten-Laufzeit)
1. **MTCNN auf Vollauflösung (30MP)** ohne Downscaling
2. **Sequenzielles Processing** pro Bild und pro Gesicht (kein Parallelismus)
3. **Mehrfaches Decode** des gleichen Bildes (EXIF + Bildload)

## Präzision vs. Performance (Einordnung)
- Aktueller Modus priorisiert **maximale Genauigkeit**:
  - MTCNN Face Detection auf voller Auflösung
  - MediaPipe FaceMesh pro Gesicht
- Das ist extrem teuer für 30MP-HEIC und Gruppenszenen.
- Performance-Optimierung ist möglich, aber führt zu **kontrolliertem Genauigkeitsverlust** (z. B. Downscale, Begrenzung der Gesichtsanzahl, ROI-Pipeline).

## Empfehlung (ohne Implementierung)
- **Erst Genauigkeit beibehalten, aber Messung/Profiling machen**.
- Danach schrittweise, messbare Optimierungen (z. B. Downscale vor MTCNN), um Abwägung „Genauigkeit vs. Leistung“ datenbasiert zu treffen.

## Referenzen im Code
- Auto-Rating Ablauf: `ModernWindow._auto_rate_images()`
- Analyse pro Bild: `QualityAnalyzer.analyze_batch()` → `analyze_image()`
- MTCNN + MediaPipe: `QualityAnalyzer._analyze_faces_mtcnn()`
- DB-Write: `GroupScorer.apply_scores_to_db()`
