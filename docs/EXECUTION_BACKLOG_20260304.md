# PhotoCleaner – Execution Backlog (Stand: 2026-03-04)

Zweck: Operative Abarbeitung der offenen Tasks aus Audit + Roadmap in klaren Blöcken.

## Arbeitsregeln
- Single Source of Execution: Dieses Backlog ist die aktive To-do-Liste.
- Definition of Done je Task: Code + kurze Validierung + Statusupdate in Roadmap.
- Priorität: P0 extern/manuell abschließen, dann P1 Architektur in kleinen, testbaren Slices.

---

## NOW (Sprint 1)

### A) Kritische Blocker (P0)
1. [ ] Secret-Rotation (Supabase Keys)
   - Typ: Extern/Manuell
   - Done wenn: Alte Keys deaktiviert, neue Keys gesetzt, kurzer Rotationsvermerk in Roadmap.

2. [ ] Frozen Build Smoke-Test auf 5+ Clean Windows Maschinen
   - Typ: Extern/Manuell
   - Done wenn: 5 Reports mit Start/Import/Rating/Log-Marker vorhanden, keine Blocker offen.

### B) Architektur & Wartbarkeit (P1)
3. [x] Lizenz-Flow entkoppeln (Service-Adapter Slice #1)
   - Typ: Code
   - Ergebnis: `services/license_service.py` + Dialog über Service angebunden.

4. [x] Modern Window: ersten UI→Service Adapter extrahieren (Slice #2)
   - Typ: Code
   - Scope: genau ein klarer Workflow (z. B. Status-/Batch-Aktion), keine UX-Änderung.
   - Done wenn: UI ruft Service statt direkter Repo/Pipeline-Kopplung.

5. [x] Lizenz/Activation Regression-Checks ergänzen
   - Typ: Code/Test
   - Scope: gezielte Tests für Aktivierung, fehlende Env-Konfig, Remove/Refresh.
   - Done wenn: relevante Tests grün, kein Regressionsfehler.


### C) Struktur & Governance
6. [x] Roadmap als Steuerdokument bereinigen
   - Typ: Doku
   - Scope: Aktiver Teil oben, Historie unten als Archiv referenzieren.
   - Done wenn: Top-Section zeigt nur aktuellen Plan + nächstes Sprintziel.

7. [x] Audit auf Ist-Status aktualisieren
   - Typ: Doku
   - Scope: P0 als weitgehend geschlossen markieren, Rest-Risiken transparent halten.
   - Done wenn: Audit enthält "Offen", "Erledigt", "Nächste Schritte".

---

## NEXT (Sprint 2)

8. [x] `quality_analyzer.py` in erste Submodule schneiden (Face/Sharpness/Scoring/EXIF)
   - [x] Slice 1: Datenmodelle (`CameraProfile`, `PersonEyeStatus`, `FaceQuality`, `QualityResult`) nach `pipeline/analysis/models.py` extrahiert
   - [x] Slice 2: Face-Analyse-Funktionen nach `pipeline/analysis/face_detector.py` extrahiert
   - [x] Slice 3: Sharpness/Scoring-Block extrahiert nach `pipeline/analysis/quality_scorer.py`
   - [x] Slice 4: EXIF/Metadata-Block extrahiert nach `pipeline/analysis/exif_extractor.py`
   - [x] Slice 5.1: Haar-Cascade-Resolver nach `pipeline/analysis/haar_cascade_resolver.py` extrahiert; doppelte Cascade-Initialisierung in `QualityAnalyzer` entfernt
   - [x] Slice 5.2: Face-Mesh-Resolver nach `pipeline/analysis/face_mesh_resolver.py` extrahiert; `face_detector.py` von `quality_analyzer.py` entkoppelt
9. [ ] `modern_window.py` weiter in views/controllers/workflows teilen
10. [ ] Legacy-UI Pfade sichtbar als deprecation markieren
11. [ ] Website gemeinsame CSS/JS-Bundles einführen

---

## LATER (Sprint 3+)

12. [ ] Naming-/Terminologie-Guide finalisieren (Code Englisch, UI via i18n)
13. [ ] Weitere QA-Baselines (10k/50k/100k) mit Vergleichsreport konsolidieren
14. [ ] Launch-Readiness Re-Score nach P1/P2 Fortschritt

---

## Status-Log
- 2026-03-04: Backlog initial erstellt und mit Roadmap/Audit abgeglichen.
- 2026-03-04: P1 Slice #1 (License Service Adapter) bereits umgesetzt.
- 2026-03-04: Lizenz/Activation Regression-Checks umgesetzt (`tests/unit/test_license_service.py`), 7 Tests grün.
- 2026-03-04: P1 Slice #2 umgesetzt: Progress-Update in `modern_window.py` über Service/Facade statt direkter SQL-Zählung.
- 2026-03-04: `quality_analyzer` Split Slice 1 umgesetzt (`pipeline/analysis/models.py`), Validierung: 36/36 fokussierte Analyzer-Tests grün.
- 2026-03-04: `quality_analyzer` Split Slice 2 umgesetzt (`pipeline/analysis/face_detector.py`), Validierung: 36/36 fokussierte Analyzer-Tests grün.
- 2026-03-04: `quality_analyzer` Split Slice 3 umgesetzt (`pipeline/analysis/quality_scorer.py` mit 18+ Scoring-Methoden). Validierung: 36/36 fokussierte Tests grün. Quality-Analyzer von 2112 auf 1387 Zeilen reduziert.
- 2026-03-12: `quality_analyzer` Split Slice 4 umgesetzt (`pipeline/analysis/exif_extractor.py`), EXIF-Methoden über Wrapper in `QualityAnalyzer` kompatibel gehalten. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-12: `quality_analyzer` Split Slice 5.1 umgesetzt (`pipeline/analysis/haar_cascade_resolver.py`), Haar-Pfadauflösung zentralisiert und Cascade-Laden als Single Source in `FaceDetector` konsolidiert. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-12: `quality_analyzer` Split Slice 5.2 umgesetzt (`pipeline/analysis/face_mesh_resolver.py`), Face-Mesh-Konstruktorauflösung zentralisiert und `face_detector.py` vom Monolith-Import entkoppelt. Validierung: 36/36 fokussierte Tests grün.
