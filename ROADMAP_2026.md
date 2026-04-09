# PhotoCleaner – Roadmap 2026

**Stand:** 09. April 2026 · Version 0.8.5
**Ziel:** v1.0.0 Launch Q3/Q4 2026
**Launch-Readiness:** 7.6 / 10 → ein externes Gate offen

---

## ✅ Was bisher erledigt wurde

| Bereich | Ergebnis |
|---|---|
| **Frozen-Build Stabilisierung (Phase 4.1)** | State Machines, Haar/MediaPipe-Fallbacks, TF CPU-only, i18n-Vollständigkeit |
| **Security P0** | Hardcoded Secrets entfernt, Secret-Scan CI, `.gitignore` gehärtet, `.env.example` |
| **Architektur – Quality Analyzer** | Slices 1–6 vollständig; Monolith (~2100 Zeilen) in Pipeline-Module aufgeteilt |
| **Architektur – modern_window.py** | Slice 6: alle Workflow-Controller extrahiert (16/16 Tests grün) |
| **MSI Distribution** | WiX v4 Installer-Track fertig (`scripts/build_msi.ps1`, `docs/guides/MSI_BUILD.md`) |
| **Website** | Gemeinsame Asset-Bundles eingeführt (`site-bundle.css/js`) |
| **Governance** | Naming-/Terminologie-Guide: Code=Englisch, UI via i18n |
| **QA-Baseline** | Risikobasierter Scope: 1k/5k Pflicht · 10k optional · 50k/100k nicht blockierend |
| **Licensing Client** | Retry: Backoff + Jitter + Retry-After + DNS-Fail-Fast + Budget-Cap |
| **Supabase Licensing** | Ed25519-Signaturpfad + PostgREST-Schema-Fix vollständig gelöst (2026-04-07) |

---

## 🚨 Go/No-Go-Gates für v1.0 (extern / manuell)

Diese Gates wurden definiert; aktuell blockiert noch ein Punkt den Launch.

| # | Gate | Status |
|---|---|---|
| 1 | **Secret Rotation** – Supabase-Keys im Dashboard rotieren | ✅ erledigt (nur Anon-Key in History; privates Repo; kritische Keys nie exponiert) |
| 2 | **5× Frozen-Build Smoke-Test** – EXE auf sauberen Windows-Maschinen ohne Dev-Setup | ⬜ offen (Docker-Teilabdeckung möglich, siehe unten) |

Protokoll: `docs/guides/MSI_BUILD.md` · Script: `scripts/smoke_test_protocol.py`

---

## 📋 Nächste Schritte (kein Launch-Blocker, aber sinnvoll)

### Status-Delta (2026-04-09)

**✅ Woche-1-Trust-Foundation VOLLSTÄNDIG ABGESCHLOSSEN** (2026-04-08)

Nicht nur Baseline erfüllt, sondern massiv erweitert:
- Phase C (Status Language): Alle Jargon ersetzt, 24+ i18n-Keys, Tests grün
- Phase D (Pipeline UX): ProgressDialog + FinalizationDialog in Production, 24+ i18n-Keys
- Phase E (Review-Produktivität): 8 Shortcuts, Button-Reorg, Action-Visibility, 9+ i18n-Keys
- Phase F (KPI Foundation): Tracking-Klasse live, Decision Recording aktiv, Export-ready
- UI-Fixes: Duplikate behoben, Button-Layout, Statusleiste optimiert

**Validierung:** 15/15 Tests grün, Smoke-Test erfolgreich, 0 Syntax-Fehler.

**Nächster Schritt:** Week-5-Fokus (Benchmark-Flow + Presets + sichtbare Fortschrittsmeilensteine).

### Kurzfristige Bugfix-Liste (2026-04-09)

- ✅ Gruppenliste kompakter: "Gruppe 1 • X Bilder", ohne SG-/Null-Prefix
- ✅ Gruppenstatus visuell klar: fertig = grün, offen = rot
- ✅ MSI-Permissions-Fix: Thumbnail-Cache in benutzerschreibbarem Cache-Ordner statt `Program Files`
- ✅ MSI-Cloud-Config ohne manuellen Endnutzer-Schritt: Build injiziert `SUPABASE_PROJECT_URL` + `SUPABASE_ANON_KEY` automatisch in den Installer-Payload
- ✅ Build/Release-Doku aktualisiert: Cloud-Config-Handling in `docs/guides/MSI_BUILD.md` dokumentiert
- ▶ Neu eingeplant: Code-Signing (Publisher-Vertrauen) vorbereiten, damit Installer nicht mehr als "Unbekannter Herausgeber" erscheint
- ▶ Verbleibend (nicht-blockierend): TensorFlow-Importdauer/GPU-Enumeration beobachten
- ▶ Verbleibend (nicht-blockierend): TensorFlow Retracing-Warnungen im Analysepfad reduzieren
- ▶ Verbleibend (optional): MediaPipe-Thread-Import robuster/fallback-schneller machen

### Status-Delta (2026-04-09, abends)

- ✅ Settings-Dialog umgebaut: weniger Tabs, klarere Struktur, Systemeinstellungen an erster Stelle
- ✅ Doppelte Sprache/Theme-Steuerung entfernt (nur noch zentral im Settings-Dialog)
- ✅ Analyse-Fortschritt modernisiert: sichtbare 4-Stufen-Meilensteine (ausstehend/grau, aktiv/blau, abgeschlossen/gruen)
- ✅ ETA-Begriff in UI auf "Verbleibende Zeit" umgestellt (DE) / "Remaining time" (EN)
- ✅ Benchmark auf Realdaten ausgeführt (`C:\Users\chris\OneDrive\Bilder\01_Photocleaner\Input`)
- ✅ Profiling-Erkenntnis bestätigt: Stage 4 (Quality-Analyse) ist klarer Hauptengpass
- ✅ Week-5-Plan präzisiert: kein kurzfristiger Sprachwechsel, erst Orchestrierung/Parallelisierung optimieren

### 1 · MSI Smoke-Test auf Virgin Windows
Installer (`.msi`) auf einer frischen Maschine validieren: Install → Upgrade → Uninstall.
Separat und ergänzend zu den EXE-Smoke-Tests.

### 2 · Phase 4.3 – Performance Regression
- Baseline v0.7.0 vs. v0.8.4 auf identischem 5k-Dataset vergleichen
- Model-Loading-Zeiten prüfen (Ziel: MTCNN/MediaPipe < 10 s, Haar-Cascade < 500 ms)
- ThreadPool-Verhalten im Frozen Build unter Last verifizieren

### 3 · Phase 4.4 – Launch-Vorbereitung

| Aufgabe | Prio |
|---|---|
| Version auf 1.0.0 bumpen, Tag `v1.0.0-rc1` setzen | Hoch |
| MSI auf virgin Win 10 / Win 11 testen (Install / Upgrade / Uninstall) | Hoch |
| Code-Signing-Zertifikat beschaffen + EXE/MSI mit Timestamp signieren (Publisher-Vertrauen) | Mittel |
| Stripe + Supabase Produktionsbereitschaft end-to-end validieren | Hoch |
| Lizenz-Vollständig-Durchlauf (Kauf → Aktivierung → Ablauf → Erneuerung) | Hoch |
| User Manual vervollständigen | Mittel |
| Troubleshooting Guide + FAQ | Mittel |
| Support-Setup (E-Mail-Template, Bug-Melde-Prozess) | Niedrig |

---

## 🔐 Lizenzmodell-Migration (neu)

Neues Modell: **FREE (einmalig 250 Bilder, kostenlos per E-Mail-Lizenz)** + **PRO (Jahresabo, unbegrenzt)**.  
**ENTERPRISE entfällt**.

### Slice 1 · Domain/Backend-Grundlage (✅ umgesetzt)
- FREE-Lifetime-Limit auf 250 gesetzt
- Enterprise als aktiver Tier entfernt, Alt-Daten werden kompatibel auf PRO gemappt
- Upgrade-Meldungen auf PRO-only angepasst
- Webhook auf PRO-only umgestellt

### Slice 2 · UI + Texte (✅ umgesetzt)
- Lizenzdialog auf 2 Pläne (FREE/PRO) reduzieren
- i18n-Texte und Pricing-Tabellen bereinigen (kein Enterprise mehr)
- Free-Quota-Texte überall auf „einmalig 250 Bilder" vereinheitlichen

### Slice 3 · Stripe/Supabase Produktmodell (✅ umgesetzt)
- ✅ Webhook-Metadaten fixiert (`metadata.plan=pro` Guardrail), deployed und negativ getestet (falscher Plan -> HTTP 400)
- ✅ Technischer E2E-Fluss getestet (Testpfad B): Webhook -> Lizenz -> Exchange-Aktivierung -> signierte `license_data`
- ✅ E2E-Runbook erstellt: `docs/guides/STRIPE_SUPABASE_E2E.md`
- ✅ Echter Stripe-Checkout mit Signaturpfad durchgeführt: Checkout -> Webhook -> Lizenzmail -> Aktivierung

### Slice 4 · Guardrails + Tests (✅ umgesetzt)
- ✅ Unit-/E2E-Tests für Free-Quota (250) + PRO unlimited ergänzt
- ✅ Regression-Tests ergänzt: alte ENTERPRISE-Eingaben werden als PRO akzeptiert
- ✅ Smoke-Test-Checkliste um Lizenzfälle FREE/PRO erweitert (`docs/guides/MSI_BUILD.md`, `scripts/smoke_test_protocol.py`)

---

## 🎯 Feature-Scope

### Produktfokus bis Release

Primäres Ziel ist jetzt nicht mehr Feature-Breite, sondern Vertrauen in die Automatik und sichere Korrekturpfade im Review.

### v1.0 Must-have

1. Explainable Score Breakdown
2. Confidence Badge + Needs Review
3. Merge/Split für Gruppen
4. Undo-Historie + Action Log
5. Guided Onboarding + Sample Walkthrough
6. Smart Filter im Review
7. Quota- und Upgrade-Messaging im Workflow

### v1.1 Should-have

1. Warum nicht gruppiert? Diagnose
2. Review Queue für unsichere/große Gruppen
3. Side-by-Side Compare mit Zoom + EXIF-Diff
4. Presets Fast / Balanced / Best Quality
5. Progressive Results während Analyse
6. Benchmark- und Diagnostics Center

### Later Nice-to-have

1. Performance Mode für High-Res
2. Batch Approval mit Guardrails

### Out of Scope (v1.x)

1. Non-destructive Image Editing
2. Mobile-Unterstützung

---

## 🗺️ Nächste 8 Wochen (max. 2 Entwickler)

### Woche 1
- ✅ Produkt- und UX-Spezifikation für Vertrauen, Confidence, Merge/Split, Undo
- ✅ KPI-Ziele definieren: Trust, False Split/Merge, Time-to-first-result
- ✅ Testbasis und Benchmark-Kriterien fixieren

### Woche 2
- ✅ Datenmodell für Explainability und Confidence fertigstellen
- ✅ UI-Konzept für Badges, Score-Details und Review-Hinweise
- ✅ Unit-Tests für Score-to-Confidence-Mapping
- ✅ Technisches Startdokument: `docs/architecture/WEEK1_TRUST_FOUNDATION.md`

### Woche 3
- ✅ Merge/Split-Flow inklusive Persistenz und Recovery implementiert
- ✅ Undo-/Action-Log-Verhalten finalisiert (inkl. UI-Rueckmeldungen/History-Beschreibungen)
- ✅ Sicherheitsregressionen für Delete/Export ergänzt (Controller + Integrationsabdeckung)

### Woche 4
- ✅ Onboarding, Smart Filter und Quota-/Upgrade-Messaging umgesetzt
- ✅ Safe-Review-Hinweise für Erstnutzer integriert
- ✅ First-run-Test auf sauberem Windows-Setup
- 📄 Umsetzungsplan: `docs/architecture/WEEK4_ONBOARDING_SMART_FILTER.md`

### Woche 5
- ✅ Sichtbare Fortschrittsmeilensteine im langen Run umgesetzt
- ✅ Realdaten-Benchmark als Baseline durchgeführt (Input-Ordner, Profiling-Artefakt vorhanden)
- ▶ A/B-Benchmark-Flow finalisieren (Current Thread-Batch vs. Process-Parallel vs. Fast-Mode)
- ▶ Profiling-Ausgabe bereinigen (image_count korrekt berichten)
- 📌 Presets Fast/Balanced/Best Quality bleiben Backlog (nicht in Week 5/6 implementieren)

#### Week-5 Performance-Plan (Profiling-basiert, 2026-04-09)
- Fokus auf Stage 4 (Quality-Analyse), da aktuell groesster Laufzeitblock.
- Kein Sprachwechsel (Rust/andere Sprache) im kurzfristigen Plan: zuerst Orchestrierung und Parallelisierung optimieren.
- A/B-Benchmark auf Realdaten etablieren: Current Thread-Batch vs. Process-Parallel vs. Fast-Mode (Haar).
- Multiprocessing-Variante fuer Quality-Stage produktionsreif schalten (Feature-Flag, Guardrails, Fallback).
- MTCNN-Einsatz staffeln: erst Cheap-Filter/Pre-Scoring, dann MTCNN nur fuer Kandidatenbilder (Top-K pro Gruppe).
- Thread-Overhead reduzieren: Progress/Logging drosseln, groebere Callback-Intervalle.
- Profiling-Report korrigieren: image_count im JSON sauber ausweisen, damit Benchmarks belastbar vergleichbar sind.

#### Erwarteter Effekt (kurzfristig)
- Deutlich weniger Wartezeit in Lock-/Thread-Synchronisation.
- Bessere Skalierung auf Mehrkern-Systemen ohne kompletten Re-Write.
- Saubere Entscheidungsgrundlage fuer spaetere Architektur-Schritte.

### Woche 6
- Stage-4-Optimierung umsetzen (Quality-Analyse als Hauptengpass)
- Multiprocessing-Variante für Quality-Stage produktionsreif schalten (Feature-Flag + Fallback)
- MTCNN-Einsatz staffeln (Top-K/Kandidaten statt Vollanalyse auf allen Bildern)
- Thread-/Progress-Overhead reduzieren (Callback-Intervall, Logging, Synchronisationsdruck)
- Cache-Pfad und Qualitätsdrift validieren

### Woche 7
- Stabilisierung + Regressionstests auf optimiertem Analysepfad
- Frozen-Build-Validierung und Review-Polish
- FREE/PRO Lizenz-Sanity und Delete-Safety final prüfen
- Optional: Progressive Results in der Analyse starten (nur wenn Week-6-Ziele stabil)

### Woche 8
- Pilot-Release-Readiness
- Support-Playbook für Gruppierungsprobleme
- KPI-Tracking für Trust, Korrekturen und Durchsatz
- Release-Entscheidung auf Basis der A/B-Benchmark-Deltas und Smoke-Test-Status

### Team-Aufteilung (Empfehlung)

- Entwickler 1: Review UX, Explainability, Confidence, Merge/Split, Onboarding, Messaging
- Entwickler 2: Scoring-Heuristik, Benchmarking, Presets, Progressive Results, Performance, Stabilität

### Warum diese Reihenfolge

Der aktuelle Engpass ist Vertrauen, nicht Funktionsanzahl. Solange Nutzer bei Fehlgruppierung keinen klaren Korrekturpfad haben und lange Läufe intransparent wirken, liefern zusätzliche Features wenig Netto-Wert. Deshalb zuerst Vertrauen und Recovery, danach Geschwindigkeit und Power-Features.

---

## 📊 Launch-Readiness Score (Stand 2026-04-07)

| Bereich | Score |
|---|---:|
| Code-Qualität | 7.5 |
| Struktur / Architektur | 8.5 |
| Performance | 8.0 |
| UX | 7.5 |
| Wartbarkeit | 8.0 |
| Betrieb / Infra | 6.5 *(Supabase + Secrets erledigt; 5× Smoke-Tests noch offen)* |
| **Gesamt** | **7.6 / 10** |

**Conditional Go:** Launch freigegeben, sobald der 5× Smoke-Test abgehakt ist.
