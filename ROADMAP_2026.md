# PhotoCleaner – Roadmap 2026

**Stand:** 07. April 2026 · Version 0.8.4
**Ziel:** v1.0.0 Launch Q3/Q4 2026
**Launch-Readiness:** 7.4 / 10 → zwei externe Gates offen

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

Nur diese zwei Punkte blockieren den Launch.

| # | Gate | Status |
|---|---|---|
| 1 | **Secret Rotation** – Supabase-Keys im Dashboard rotieren | ✅ erledigt (nur Anon-Key in History; privates Repo; kritische Keys nie exponiert) |
| 2 | **5× Frozen-Build Smoke-Test** – EXE auf sauberen Windows-Maschinen ohne Dev-Setup | ⬜ offen (Docker-Teilabdeckung möglich, siehe unten) |

Protokoll: `docs/guides/MSI_BUILD.md` · Script: `scripts/smoke_test_protocol.py`

---

## 📋 Nächste Schritte (kein Launch-Blocker, aber sinnvoll)

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

### Slice 3 · Stripe/Supabase Produktmodell (🟡 in Arbeit)
- ✅ Webhook-Metadaten fixiert (`metadata.plan=pro` Guardrail), deployed und negativ getestet (falscher Plan -> HTTP 400)
- ✅ Technischer E2E-Fluss getestet (Testpfad B): Webhook -> Lizenz -> Exchange-Aktivierung -> signierte `license_data`
- ✅ E2E-Runbook erstellt: `docs/guides/STRIPE_SUPABASE_E2E.md`
- ⬜ Echter Stripe-Checkout mit Signaturpfad offen: Checkout -> Webhook -> Lizenzmail -> Aktivierung

### Slice 4 · Guardrails + Tests
- Unit-Tests für Free-Quota (250) + PRO unlimited ergänzen
- Regression-Tests: alte ENTERPRISE-Lizenzen werden als PRO akzeptiert
- Smoke-Test-Checkliste um Lizenzfälle FREE/PRO erweitern

---

## 🎯 Feature-Scope

### v1.0 (geplant)
- **Explainable Selection Scores** – Sharpness / Eye-Quality / Lighting im Detail-Panel sichtbar (1–2 Tage)
- **Keyboard Shortcuts & Accessibility** – Power-User-Flows, Qt-Accessibility (1–2 Tage)
- **ML-Fallback-Mechanismen** – ✅ bereits fertig (Haar+MTCNN-only Fallback)

### v1.1+
- Undo/Redo mit Versionshistorie
- Batch Metadata Editor (EXIF/IPTC/XMP Bulk-Update)
- Verbesserte Fehlermeldungen & User-Guidance

### Out of Scope (v1.x)
- Non-destructive Image Editing
- Mobile-Unterstützung

---

## 📊 Launch-Readiness Score (Stand 2026-04-07)

| Bereich | Score |
|---|---:|
| Code-Qualität | 7.5 |
| Struktur / Architektur | 8.5 |
| Performance | 8.0 |
| UX | 7.5 |
| Wartbarkeit | 8.0 |
| Betrieb / Infra | 5.5 *(Supabase gelöst; Secrets + Smoke-Tests noch offen)* |
| **Gesamt** | **7.6 / 10** |

**Conditional Go:** Launch freigegeben, sobald Secret Rotation + 5× Smoke-Test abgehakt sind.
