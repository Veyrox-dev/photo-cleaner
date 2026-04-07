# Project Audit – PhotoCleaner (2026-03-04)

## Scope
- Codebase: `photo-cleaner` (Python Desktop App + statische Website-Seiten)
- Methodik: Struktur-Scan, Fehlerdiagnostik, Security-Pattern-Scan, Architektur-Spotchecks

---

## 1) Code-Qualität (Findings + konkrete Verbesserungen)

### 1.1 Monolithische UI-Klassen (Wartbarkeitsrisiko)
**Probleme**
- `src/photo_cleaner/ui/modern_window.py` hat ~6310 Zeilen.
- `src/photo_cleaner/pipeline/quality_analyzer.py` hat ~3012 Zeilen.
- `src/photo_cleaner/ui/main_window.py` hat ~819 Zeilen.

**Auswirkung**
- Hohe Änderungsrisiken, schwieriges Debugging, langsameres Onboarding.

**Verbesserung**
- `modern_window.py` in Feature-Module schneiden:
  - `ui/views/` (Panels, Dialog-Launcher)
  - `ui/controllers/` (User-Events, Navigation)
  - `ui/workflows/` (Export, Batch-Operationen)
- `quality_analyzer.py` aufteilen in:
  - `pipeline/analysis/face_analysis.py`
  - `pipeline/analysis/sharpness.py`
  - `pipeline/analysis/exif.py`
  - `pipeline/analysis/scoring.py`

### 1.2 Doppelte Zuständigkeiten in UI
**Probleme**
- Gleichzeitig `main_window.py`, `modern_window.py`, `cleanup_ui.py` und `ui/legacy/cleanup_ui.py` aktiv im Baum.
- Historischer Kommentar in `main_window.py` widerspricht dem aktiven Startpfad.

**Auswirkung**
- Unklare Product-Source-of-Truth, Gefahr von Regressionen in "falscher" UI.

**Verbesserung**
- Ein offizielles Entry-UI festlegen (z. B. Modern UI).
- Legacy-Code klar markieren (`deprecated/`) und optional per Feature-Flag laden.

### 1.3 Schichtkopplung UI ↔ Core/Pipeline/DB
**Probleme**
- UI importiert direkt DB, Repositories, Services und Pipeline-Klassen.

**Auswirkung**
- Enge Kopplung, schwer testbar, UI-Änderungen beeinflussen Business-Logik.

**Verbesserung**
- Application-Service-Schicht einziehen:
  - UI spricht nur `app/services/*` an.
  - Services kapseln DB + Pipeline + Repositories.

### 1.4 Teilweise inkonsistente Sprache/Namenskonvention
**Probleme**
- Deutsch/Englisch gemischt in Kommentaren, Labels, Dateinamen und Symbolen.

**Verbesserung**
- Naming-Policy festlegen:
  - Code-Symbole Englisch
  - UI-Text über i18n
  - Doku/Marketing getrennt

---

## 2) Projektstruktur (Ist vs. Zielstruktur)

### 2.1 Aktuelle Struktur – positiv
- Bereits vorhanden: `core`, `ui`, `services`, `repositories`, `pipeline`, `db`, `models`.
- Gute Basis für saubere Trennung.

### 2.2 Schwächen
- Website-Dateien lagen im Root (jetzt behoben).
- Viele große "Alles-in-einer-Datei"-Module.
- Legacy/Archive-UI nicht strikt getrennt.

### 2.3 Zielstruktur (empfohlen)
```
src/photo_cleaner/
  core/
  app/                # orchestration / use-cases
  services/
  repositories/
  pipeline/
    analysis/
  ui/
    views/
    controllers/
    dialogs/
    legacy/
  utils/
  config/
  assets/
website/
  *.html
```

---

## 3) Performance-Check

### 3.1 Positiv
- Bereits etablierter Lasttest-Baseline-Stack.
- Lazy-Import-Muster vorhanden (z. B. Analyzer-Loading in UI).

### 3.2 Risiken
- Große UI-Dateien mit vielen dialog-basierten Flows → erhöhte Main-Thread-Last wahrscheinlich.
- Mehrfache Initialisierungspfade in großen Klassen schwer kontrollierbar.

### 3.3 Konkrete Optimierungen
- Heavier Jobs strikt in Worker/Threads auslagern (konsistent, nicht nur punktuell).
- UI-Update-Batching bei großen Ergebnislisten.
- Caching-Hotspots in Thumbnail + Quality-Scoring regelmäßig profilen.

---

## 4) UX- und Produktlogik-Check

### 4.1 UX-Schwächen
- Mehrere UIs im Code erzeugen inkonsistente Nutzerflüsse.
- Website hat sehr viel Inline-CSS/JS je Seite (Wiederholung, spätere Pflege teuer).
- Teilweise unterschiedliche Tonalität/Terminologie zwischen Seiten.

### 4.2 Konkrete UX-Verbesserungen
- Einen klaren UI-Flow offiziell machen (Wizard/Flow-Doku).
- Website-Styles/JS in gemeinsame Dateien auslagern (`website/assets/css`, `website/assets/js`).
- UX-Textleitfaden (Deutsch konsistent, kurze klare CTA-Texte).

---

## 5) Sicherheits-Check

### 5.1 Kritische Findings (P0) – Status 2026-03-04
1. **Eingebettete Credentials im Code**
   - Status: **behoben**
   - Betroffene Runtime-Stellen wurden auf env-only Konfiguration umgestellt.
2. **`.env` mit echten Werten im Tracking**
   - Status: **behoben**
   - `.env` wurde aus Git-Tracking entfernt, `.env.example` eingeführt.
3. **Service-Role/Key-Material in Doku-Beispielen**
   - Status: **behoben**
   - Beispiele wurden auf Platzhalter sanitisiert.
4. **Rest-Risiko (offen)**
   - **Secret Rotation extern/manuell noch erforderlich** (außerhalb Repo).

### 5.2 Risiko
- Secret-Leak, Missbrauch von Backend-Ressourcen, unerwartete Kosten/Incident.

### 5.3 Sofortmaßnahmen
- [ ] Keys sofort rotieren (extern/manuell, offen).
- [x] `.env` aus Tracking entfernen, `.env.example` committen.
- [x] Hardcoded Fallback-Credentials aus Runtime-Code entfernen.
- [x] Secret-Scanning im CI und pre-commit aktivieren.

---

## 6) Launch-Readiness (1–10)

- **Code-Qualität:** 6/10
- **Struktur:** 7/10
- **Performance:** 8/10
- **UX:** 7/10
- **Wartbarkeit:** 5/10

### Launch-Blocker
- Secret-Rotation (extern/manuell) noch offen.
- Zu große Monolithen in kritischer UI- und Analyse-Logik (mittelfristiges Release-Risiko).

### Nice-to-have
- Vollständige Website-Asset-Bündelung (gemeinsame CSS/JS-Dateien).
- Weitere Entkopplung alter UI-Pfade.

---

## 7) Priorisierter Aktionsplan (P0/P1/P2)

### P0 (sofort)
1. Secret-Rotation (extern/manuell)
   - Aufwand: **Medium**
2. Secret-Removal aus Code/Repo + Doku-Härtung
   - Aufwand: **Low**
3. CI Secret Scan + pre-commit Hook
   - Aufwand: **Low**

**P0-Status (2026-03-04):**
- Punkt 2 + 3: **erledigt**
- Punkt 1 (Rotation): **offen extern**

### P1 (kurzfristig)
1. `modern_window.py` in Views/Controller/Workflows aufteilen
   - Aufwand: **High**
2. `quality_analyzer.py` in Submodule zerlegen
   - Aufwand: **High**
3. UI nur über App-Service-Layer mit Core/Pipeline verbinden
   - Aufwand: **Medium**

### P2 (mittelfristig)
1. Website auf gemeinsames CSS/JS-Layout umstellen
   - Aufwand: **Medium**
2. Legacy-UI-Pfade in klaren Deprecation-Ordner migrieren
   - Aufwand: **Medium**
3. Naming- und Text-Styleguide finalisieren
   - Aufwand: **Low**

---

## Quick Wins
1. Secret-Exposure in Runtime schließen (**erledigt**)
2. `.env.example` + CI/pre-commit checks (**erledigt**)
3. Website-Dateien zentral in `website/` (**erledigt**)
4. License Flow via Service-Adapter entkoppeln (P1 Slice #1, **erledigt**)

---

## Bereits umgesetzte Maßnahmen in diesem Durchlauf
- Website-HTML aus Root in `website/` verschoben.
- Relative Asset-Pfade in den verschobenen Dateien korrigiert (`assets/...` → `../assets/...`).
- Hardcoded Supabase-Fallbacks aus Runtime entfernt.
- `.env` untracked + `.env.example` hinzugefügt.
- Secret-Scan in CI + pre-commit ergänzt.
- P1 Slice #1 umgesetzt: `services/license_service.py` als Adapter eingeführt.

---

## Operative Weiterarbeit
- Aktive Abarbeitung läuft über: `docs/EXECUTION_BACKLOG_20260304.md`
- Ziel: P1 Slice #2 + Regression-Checks als nächster abgeschlossener Block.
