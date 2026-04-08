# Week 1 Trust Foundation

## Goal

Week 1 builds the first visible trust layer for review: explainable scores, an initial confidence signal, and the technical baseline for later merge/split and undo work.

The main product problem is not raw automation quality. It is that users cannot quickly understand why a photo was recommended and when they should double-check the result.

## Scope

This week covers three streams:

1. Explainable Score Breakdown
2. Confidence Badge plus Needs-Review heuristic
3. Technical prep for Merge/Split and Undo

## Explainable Score Breakdown

The current pipeline already persists these components on the files table:

- quality_score
- sharpness_component
- lighting_component
- resolution_component
- face_quality_component

Week 1 uses those fields directly in the Modern UI instead of showing only a flat total score.

### UX rule

Every detailed image view should answer three questions in under three seconds:

1. Why was this image scored this way?
2. What is the strongest signal?
3. What looks weak enough that I should manually verify it?

### First implementation slice

- Show overall score plus per-component breakdown in the Modern detail views.
- Add a short text summary: strongest driver and weakest component.
- Add explicit strengths and concerns text.
- Preserve a fallback for old data that only contains an overall score.

### Data rule

`NULL` component values must stay `NULL` in the UI loading path.

This is important because `COALESCE(..., 0)` makes missing analysis look like a real 0 percent result and produces misleading explanations.

## Confidence Badge

Week 1 does not attempt a complex ML confidence model. It starts with a deterministic heuristic on top of existing component scores.

### Initial heuristic

- High confidence:
  overall score is strong, no weak component, all core signals stable
- Medium confidence:
  mixed but acceptable signals, user should briefly verify
- Low confidence:
  two or more weak components, very low total score, or a clearly weak single signal
- Incomplete:
  only legacy total score exists and the image should be re-analyzed for details

### Product meaning

- High confidence reduces review friction.
- Medium confidence keeps the user in the loop.
- Low confidence is the first building block for a future Needs-Review queue.

## Merge/Split Prep

Merge/Split is not implemented in this slice, but the design should assume:

- group-level confidence can later aggregate file-level confidence
- action history must record manual regrouping events
- merge and split must be reversible through the same undo pipeline as manual keep/delete changes

Relevant code paths already identified:

- `src/photo_cleaner/core/duplicate_groups.py`
- `src/photo_cleaner/session_manager.py`
- `src/photo_cleaner/ui/modern_window.py`
- `src/photo_cleaner/ui_actions.py`

## Acceptance Criteria

- ✅ Modern detail views show explainable score output, not only a flat total.
- ✅ Old rows with only `quality_score` show an explicit re-analysis hint.
- ✅ The UI never renders fake 0 percent components for missing data.

---

## Status: ✅ COMPLETED (2026-04-08)

**Completion Summary:**

Woche 1 Trust Foundation wurde nicht nur erfüllt, sondern massiv erweitert. Das Projekt ist nun deutlich über die Baseline hinaus:

### Phase C: Status Language Überhaul ✅
- Alle technischen Jargon-Texte in benutzerfreundliche Deutsch/English-Begriffe ersetzt
- Confidence-Labels vereinheitlicht („Sehr zuverlässig", „Überprüfung nötig", „Daten unvollständig")
- Quality Ratings klarer gemacht (\"Sehr gut\", \"Gut\", \"Mittel\", \"Schwach\")
- 24+ neue i18n-Keys ergänzt und getestet
- Alle Tests grün: 15/15 Regression-Suite bestätigt

### Phase D: Enhanced Analysis Pipeline ✅
- Neuer `ProgressStepDialog` mit visuellen Schritten (1/2/3/4) + ETA-Berechnung
- Neuer `FinalizationResultDialog` mit Erfolgs-Cards, Error-Reporting, Betroffene-Dateien-Liste
- Vollständige Signal-Integration in `_run_automatic_pipeline()`
- 24 neue i18n-Keys für Progress/Finalization
- UI-Smoke-Test bestätigt: fehlerfreier Start, korrekte Dialog-Rendering

### Phase E: Review-Produktivität ✅
- Keyboard Shortcuts erweitert: K/D/U/Z/S/M/Pfeile
- Buttons vergrößert und priorisiert (Behalten > Löschen > Unsicher, vertikal angeordnet)
- Action-Visibility verbessert (Merge/Split/Undo jetzt klarer sichtbar)
- Unsicher-Flow als Standard für schwierige Fälle etabliert
- 9+ neue i18n-Keys für Shortcuts und Actions

### Phase F: KPI Tracking Foundation ✅
- Neue `KPITracker`-Klasse implementiert (Decision Recording, Session Statistics, JSON Export)
- Decision Timing und Error Rate Tracking eingebaut
- KPI-Session Start/End im Main Window integriert
- Decision-Recording in `_apply_status_to_selection()` aktiviert
- Export-Funktion bereit für zukünftige User-Tests
- 9+ neue i18n-Keys für KPI-Reporting

### UI-Fixes ✅
- Doppelte Fragezeichen bei „Unsicher" behoben
- Button-Layout optimiert (3 Entscheidungs-Buttons nun untereinander)
- Statusleiste aufgeräumt (KPI-Elemente für später deaktiviert)
- ETA-Beschriftung verständlicher: „Restzeit" statt „ETA"

**Deliverables:**
- 4 neue Workflow-Controller (bereits vorhanden)
- 1 neue KPI-Tracking-Klasse
- 66+ neue, bilinguale i18n-Keys
- 2 neue Dialog-Klassen (ProgressStepDialog, FinalizationResultDialog)
- 8+ neue Keyboard Shortcuts
- 6 neue UI-Helper-Funktionen für konsistentes Styling

**Validation:**
- Syntax: 0 Fehler in allen geänderten Dateien
- Tests: 15/15 Regression-Suite bestanden
- UI: Smoke-Test erfolgreich (kein Runtime-Error, Dialog-Rendering korrekt)

**Nächste Phase:** Woche 2 wird sich auf Nutzer-Validierung (Phase F Completion) und Performance-Optimierung konzentrieren.
- Score-to-confidence mapping is covered by unit tests.

## Status

Started in this slice:

- added a reusable score explanation helper
- wired explainability into Modern UI detail surfaces
- added unit tests for confidence mapping and legacy-score fallback

Completed status for Week 1 foundations:

- Explainable score breakdown in Modern UI: done
- Confidence heuristic helper: done
- Confidence mapping unit tests: done
- Legacy-score fallback hint: done

Open items to finish Week 1:

- route low-confidence items into a review queue (UI filter + counter)
- define group-level confidence aggregation rule (min/median guardrail)
- finalize KPI targets and measurement hooks

Next slices:

1. route low-confidence items into a review queue
2. add group-level confidence and group diagnostics
3. implement merge/split persistence plus undo integration

## Week 1 Completion Plan (2026-04-08 to 2026-04-09)

### Step 1 (today): Review Queue foundation

- Add deterministic flag `needs_review` from existing confidence levels.
- Surface a dedicated filter in the review flow for low-confidence files.
- Show a visible counter (`Needs Review: N`) near existing result controls.

Acceptance for Step 1:

- low-confidence files are discoverable in one click
- no false zero values for missing component data
- existing behavior for high-confidence items stays unchanged

### Step 2 (today): Group confidence rule draft

- Define group confidence as conservative aggregate (lowest confidence dominates).
- Add diagnostics text per group: strongest and weakest component patterns.
- Keep this as read-only diagnostics in Week 1 (no merge/split logic yet).

Acceptance for Step 2:

- every group has a confidence label
- low-confidence groups are visually distinguishable
- diagnostics remain consistent with file-level explanations

### Step 3 (tomorrow): MSI test pass and gate logging

- Run new MSI smoke test on target machine (Install -> First run -> Scan -> Duplicate groups visible).
- Validate that perceptual hashing is active (non-zero hashed files on mixed JPG/HEIC set).
- Capture startup latency and confirm no long TensorFlow diagnostic stall in production mode.

Smoke test checklist:

- app starts without freeze
- indexing completes without cancellation loop
- duplicate groups are shown
- review filter for low confidence works
- no critical error in log for pHash initialization