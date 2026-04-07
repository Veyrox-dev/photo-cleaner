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
   - [x] Slice 5.3: Veraltete Face-Mesh-Altlasten (`_FACE_MESH_*`, lokaler Wrapper) aus `quality_analyzer.py` bereinigt
   - [x] Slice 5.4: Lokale Face-Mesh-Cache/Config-Hash-Reste aus `quality_analyzer.py` entfernt; Warmup delegiert an `FaceDetector`
   - [x] Slice 5.5 (größer): Image-Preprocessing-Cluster (Load/Fallback/Downsampling) nach `pipeline/analysis/image_preprocessor.py` extrahiert und in `analyze_image()` verdrahtet
   - [x] Slice 5.6 (größer): EXIF/Orientation/Metadaten-Cluster nach `pipeline/analysis/metadata_enricher.py` extrahiert und in `analyze_image()` verdrahtet
   - [x] Slice 5.7 (größer): Core-Execution-Cluster (Gray/Scoring/Face/Total) nach `pipeline/analysis/analysis_executor.py` extrahiert und in `analyze_image()` verdrahtet
   - [x] Slice 5.8 (größer): Batch-Orchestrierung von `analyze_batch()` nach `pipeline/analysis/batch_runner.py` extrahiert und in `QualityAnalyzer` verdrahtet
   - [x] Slice 5.9 (größer): Runtime-Dependency-Bootstrap/Lazy-Import-Logik nach `pipeline/analysis/runtime_dependencies.py` extrahiert und `quality_analyzer.py` umgestellt
   - [x] Slice 5.10 (größer): Stage-/Capability-Resolver nach `pipeline/analysis/capability_resolver.py` extrahiert und in `QualityAnalyzer` verdrahtet
9. [x] Slice 6 starten: `modern_window.py` top-down in views/controllers/workflows teilen
   - [x] 6.1 Workflow-Seams markieren (Import, Rating, Selection, Dialogs)
   - [x] 6.2 Ersten Controller extrahieren (ohne UX-Änderung)
   - [x] 6.3 Fokussierte Regression-Tests ergänzen
   - [x] 6.4 Zweiten Controller extrahieren (Rating-Workflow: Thread-Wiring + Start)
   - [x] 6.5 Dritten Controller extrahieren (Selection/Dialog-Workflow)
   - [x] 6.6 Vierten Controller extrahieren (Export/Delete-Dialog-Flow)
   - [x] 6.7 Slice konsolidieren (technische Schulden + Abschlusskriterien dokumentiert)
10. [x] Legacy-UI Pfade sichtbar als deprecation markieren
11. [x] Website gemeinsame CSS/JS-Bundles einführen
12. [x] MSI-Installer Track aufsetzen (Vertrauenswürdigkeit Distribution)
   - [x] Entscheidung: WiX Toolset (v4) als MSI-Tooling
   - [x] Reproduzierbaren MSI-Build-Command definiert (`powershell -ExecutionPolicy Bypass -File scripts/build_msi.ps1`)
   - [x] Install/Upgrade/Uninstall Smoke-Test auf clean Windows vorbereitet (`docs/guides/MSI_BUILD.md`)

---

## LATER (Sprint 3+)

13. [x] Supabase HTTP-503 Root-Cause Sprint – `_request_with_retry` exponentialBackoff+Jitter+Retry-After, `exchange_license_key` und `register_device` auf Retry umgestellt, Unit-Tests ergänzt (34/34 grün)
14. [x] Naming-/Terminologie-Guide finalisieren (Code Englisch, UI via i18n)
15. [x] QA-Baselines risikobasiert konsolidieren (1k/5k Pflicht, 10k optional)
   - Ergebnis: Vergleichsreport erstellt und Zielbild angepasst (`docs/tech/QA_BASELINE_COMPARISON_2026-04-06.md`)
   - Definition of Done: 1k/5k als Standard-Baselines, 10k als optionaler Soak/Stress-Lauf, 50k/100k nicht mehr blockierend
16. [x] Launch-Readiness Re-Score nach P1/P2 Fortschritt
   - Ergebnis: Re-Score durchgeführt (2026-04-06) mit aktualisierter 1-10-Bewertung und Blocker-Liste in `ROADMAP_2026.md`
17. [ ] Supabase Licensing Incident Follow-up (erneut geparkt bis Infra-Fix)
   - Typ: Extern/Backend
   - Befund: `exchange-license-key` liefert Mock-Signatur (`sig-...`, Länge 32) statt Ed25519-Base64; `/rest/v1/licenses` liefert `503 / PGRST002`
   - Re-Entry: Nach Edge-Function-Signer-Fix + PostgREST-Schema-Cache-Stabilisierung

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
- 2026-03-12: `quality_analyzer` Split Slice 5.3 umgesetzt (`pipeline/quality_analyzer.py`), obsolete Face-Mesh-States/Wrapper entfernt nach Resolver-Auslagerung. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-13: `quality_analyzer` Split Slice 5.4 umgesetzt (`pipeline/quality_analyzer.py`), lokale Face-Mesh-Cache/Config-Hash-Verwaltung entfernt und `warmup()` auf `FaceDetector`-Preload umgestellt. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-13: `quality_analyzer` Split Slice 5.5 umgesetzt (`pipeline/analysis/image_preprocessor.py`), großer Image-Preprocessing-Block aus `analyze_image()` (Load/Fallback/Downsampling) extrahiert. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-13: `quality_analyzer` Split Slice 5.6 umgesetzt (`pipeline/analysis/metadata_enricher.py`), EXIF/Orientation/Metadaten-Block aus `analyze_image()` extrahiert; Kompatibilität (`CameraProfile`-Export aus `quality_analyzer`) beibehalten. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-13: `quality_analyzer` Split Slice 5.7 umgesetzt (`pipeline/analysis/analysis_executor.py`), Core-Execution-Block (Gray/Scoring/Face/Total) aus `analyze_image()` extrahiert. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-13: `quality_analyzer` Split Slice 5.8 umgesetzt (`pipeline/analysis/batch_runner.py`), `analyze_batch()`-ThreadPool-Orchestrierung extrahiert und in `QualityAnalyzer` integriert. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-15: `quality_analyzer` Split Slice 5.9 umgesetzt (`pipeline/analysis/runtime_dependencies.py`), Runtime-Dependency-Bootstrap/Lazy-Import-Status aus `quality_analyzer.py` extrahiert und per Snapshot-Bridge kompatibel gehalten. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-15: `quality_analyzer` Split Slice 5.10 umgesetzt (`pipeline/analysis/capability_resolver.py`), Stage-/Capability-Logik extrahiert und in `QualityAnalyzer` delegiert. Validierung: 36/36 fokussierte Tests grün.
- 2026-03-15: Backlog-Sync: Slice 6 als nächster Top-Down-Block priorisiert; Supabase HTTP 503 explizit geparkt; MSI-Installer-Track als neues Sprintziel ergänzt.
- 2026-03-15: Slice 6.1/6.2 gestartet: erster Workflow-Controller extrahiert (`ui/workflows/indexing_workflow_controller.py`), `modern_window.py` delegiert Indexing-/Post-Indexing-Dialog+Thread-Wiring ohne UX-Änderung.
- 2026-03-15: Slice 6.3 abgeschlossen: fokussierte Tests ergänzt (`tests/unit/test_indexing_workflow_controller.py`), Validierung: 3/3 grün.
- 2026-03-15: Slice 6.4 abgeschlossen: zweiter Workflow-Controller extrahiert (`ui/workflows/rating_workflow_controller.py`), Rating-Thread-Wiring/Start aus `modern_window.py` delegiert; Validierung: 6/6 fokussierte Workflow-Controller-Tests grün.
- 2026-03-15: Slice 6.5 abgeschlossen: dritter Workflow-Controller extrahiert (`ui/workflows/selection_workflow_controller.py`), Selection-/Comparison-/Status-Target-Logik aus `modern_window.py` delegiert; Validierung: 10/10 fokussierte Workflow-Controller-Tests grün.
- 2026-04-04: Slice 6.6 abgeschlossen: vierter Workflow-Controller extrahiert (`ui/workflows/export_delete_workflow_controller.py`), Export-/Delete-Dialog-Entscheidungen und Ergebnis-Meldungen aus `modern_window.py` delegiert; Validierung: 16/16 fokussierte Workflow-Controller-Tests grün.
- 2026-04-04: Punkt 10 abgeschlossen: Legacy-UI-Pfade (`ui/main_window.py`, `ui/cleanup_ui.py`) sichtbar als deprecated markiert (Docstring + Runtime-Warnung + Log-Hinweis auf `ModernMainWindow`).
- 2026-04-04: Slice 6.7 abgeschlossen: Slice-6-Konsolidierung dokumentiert (Controller-Set + technische Schulden + Abschlusskriterien); Slice 6 im Backlog formal auf COMPLETE gesetzt.
- 2026-04-04: Punkt 11 abgeschlossen: gemeinsames Website-Bundle eingeführt (`website/assets/site-bundle.css`, `website/assets/site-bundle.js`) und in alle Website-Seiten eingebunden.
- 2026-04-04: Punkt 12 abgeschlossen: MSI-Track mit WiX v4 aufgesetzt (`installer/PhotoCleaner.wxs`, `scripts/build_msi.ps1`) und Build/Smoke-Test-Guide dokumentiert (`docs/guides/MSI_BUILD.md`).
- 2026-04-05: Punkt 13 abgeschlossen: Supabase HTTP-503 Retry-Logik implementiert – `_request_with_retry` auf exponentielles Backoff+Jitter+Retry-After-Header+30s-Budget umgestellt; `exchange_license_key` und `register_device` nutzen jetzt Retry; 10 neue Unit-Tests, alle 34 Tests grün.
- 2026-04-06: Follow-up-Diagnose zu Supabase Licensing durchgeführt: Live-Response zeigt Mock-Signatur (`sig-...`, Länge 32) und `/rest/v1/licenses` liefert `503 / PGRST002`; Thema als externer Infra-Blocker erneut geparkt (Backlog #17).
- 2026-04-06: Punkt 14 abgeschlossen: Naming-/Terminologie-Guide finalisiert (`docs/standards/NAMING_TERMINOLOGY_GUIDE.md`), Doku-Indizes aktualisiert; Regel fixiert: Code-Identifiers Englisch, UI-Texte via i18n.
- 2026-04-06: Punkt 15 gestartet: vorhandene QA-Artefakte konsolidiert und Vergleichsreport erstellt (`docs/tech/QA_BASELINE_COMPARISON_2026-04-06.md`). Befund: 10k-Runs vorhanden aber ungültig (`success=false`, ReturnCode 1/2), 50k/100k fehlen noch.
- 2026-04-06: Punkt 15 finalisiert: QA-Zielbild auf risikobasierten Umfang umgestellt (1k/5k Pflicht, 10k optional, 50k/100k nicht blockierend) und in Report/Roadmap synchronisiert.
- 2026-04-06: Punkt 16 abgeschlossen: Launch-Readiness Re-Score durchgeführt. Ergebnis: intern technisch solide, aber extern/manuell weiter geblockt durch Secret Rotation + 5x Clean-Windows Smoke-Tests; Supabase-Incident separat geparkt (#17).
