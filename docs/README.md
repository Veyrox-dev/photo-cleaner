# PhotoCleaner

Windows-Desktop-App für intelligentes Foto-Management mit Duplikaterkennung, Qualitätsbewertung und kontrolliertem Review-Workflow.

**Stand:** 15. April 2026  
**Version:** 0.8.7  
**Status:** Beta / Launch-Vorbereitung  
**Geplanter Launch:** 3. Oktober 2026  
**Pläne:** FREE (einmaliger Scan, 250 Bilder) · PRO (29 EUR/Jahr, unbegrenzt)

---

## Überblick

PhotoCleaner hilft dabei, große Fotosammlungen strukturiert zu bereinigen, ohne direkt in einen riskanten Auto-Delete-Flow zu geraten.

Kernidee:
- ähnliche Bilder automatisch erkennen
- Bildqualität innerhalb einer Gruppe bewerten
- die besten Kandidaten vorselektieren
- Entscheidungen im Review transparent und korrigierbar machen
- Export und Bereinigung kontrolliert abschließen

Die App ist auf Windows als primäre Zielplattform ausgelegt. Der Fokus bis v1.0 liegt auf Stabilität, Review-Vertrauen und sauberem Release-Engineering.

---

## Aktueller Funktionsumfang

### Bereits im Produkt

- Perceptual Hashing für ähnliche Bilder und Duplikatgruppen
- Qualitätsbewertung mit Schärfe-, Belichtungs-, Auflösungs- und Gesichtsmetriken
- MediaPipe Face Mesh im Analysepfad mit Fallback-Strategien
- Explainable Score Breakdown und Confidence-Hinweise
- Merge / Split für Gruppen
- Undo-Historie und Action Log
- Guided Onboarding und Smart Filter im Review
- konfigurierbare Auto-Keep-Logik mit Stufen
- konfigurierbare Exportstruktur und Exportformate
- moderne PySide6-Oberfläche mit Light/Dark Theme
- produktive Mehrsprachen-Basis: DE, EN, FR, ES, NL, IT
- MSI-Build-Track für Windows-Distribution
- Update-Check Phase A via Manifest

### Vor v1.0 noch offen

- Gallery-View nach dem Review
- EXIF Smart Grouping nach Ort + Datum
- Watch Folders / Auto-Import
- 5× Frozen-Build Smoke-Test als letztes offenes Go/No-Go-Gate
- Code-Signing
- finale User-Dokumentation / FAQ / Troubleshooting

---

## Für wen ist PhotoCleaner gedacht?

- Nutzer mit großen Smartphone- oder Kamera-Backups
- Familien- und Urlaubsarchive mit vielen ähnlichen Bildern
- Portrait- und Event-Sets mit Serienaufnahmen
- Nutzer, die keine Blackbox-Auto-Löschung wollen, sondern einen Review-Flow

---

## Technischer Stack

- Python
- PySide6 / Qt
- SQLite
- Pillow
- OpenCV
- MediaPipe Face Mesh
- perceptual hashing / imagehash
- Stripe + Supabase für Lizenzierung / Backend

---

## Installation

### Empfohlener Weg für Endnutzer

Für Endnutzer ist der MSI-Installer der vorgesehene Distributionsweg. Der Build- und Testprozess ist hier dokumentiert:

- [MSI Build Guide](guides/MSI_BUILD.md)
- [Windows 11 Test Checklist](guides/WIN11_TEST_CHECKLIST.md)

### Entwicklung / Ausführung aus dem Quellcode

Voraussetzungen:
- Windows als Zielplattform
- Python 3.12
- virtuelle Umgebung empfohlen

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

### Start der Desktop-App

```powershell
python run_ui.py
```

Optional mit vorgegebenen Ordnern:

```powershell
python run_ui.py --input C:\Fotos\Input --output C:\Fotos\Output
```

### CLI

Die CLI ist schlanker als der Haupt-UI-Flow und eignet sich vor allem für Indexing und Statistik.

```powershell
photo-cleaner --help
photo-cleaner index C:\Fotos
photo-cleaner stats
```

---

## Typischer Ablauf in der App

1. Bilderordner auswählen
2. Indexing und Duplikatgruppen berechnen
3. Qualität bewerten und Keep/Delete vorschlagen
4. Gruppen im Review prüfen
5. Status anpassen, zusammenführen oder trennen
6. Export / Bereinigung abschließen

Das Produkt ist bewusst als kontrollierter Review-Workflow gebaut, nicht als vollautomatischer Cleaner ohne menschliche Kontrolle.

---

## Architektur in Kurzform

Der produktive Flow ist grob in diese Phasen aufgeteilt:

1. Indexing / Hashing
2. Duplicate Detection
3. günstige Vorfilter
4. Quality Analysis
5. Scoring / Empfehlung
6. Review / Export / Cleanup

Wichtige Architekturziele:
- keine unnötigen UI-Freezes
- saubere Fallbacks bei CV/ML-Problemen
- stabile Thumbnails, Caches und Settings in Windows-Builds
- reproduzierbare Release- und Smoke-Test-Pfade

Mehr Details:
- [Architektur-Index](INDEX.md)
- [WEEK1 Trust Foundation](architecture/WEEK1_TRUST_FOUNDATION.md)
- [WEEK4 Onboarding + Smart Filter](architecture/WEEK4_ONBOARDING_SMART_FILTER.md)

---

## Lizenzmodell

### FREE

- kostenlos
- einmaliger Scan
- bis zu 250 Bilder

### PRO

- 29 EUR / Jahr
- unbegrenzte Nutzung
- voller Produktumfang

Hinweis: Der produktive Business-Rollout ist an die organisatorischen Schritte vor Launch gekoppelt. Technisch ist das Lizenzsystem bereits weit vorbereitet, der finale Produktionsbetrieb folgt zum Launch-Fenster.

Mehr dazu:
- [License System Guide](guides/LICENSE_SYSTEM.md)
- [Stripe + Supabase E2E](guides/STRIPE_SUPABASE_E2E.md)

---

## Qualität und Release-Status

Aktuell wichtig:
- Version 0.8.7 ist funktional weit fortgeschritten
- das letzte harte Launch-Gate ist der 5× Frozen-Build Smoke-Test
- vor v1.0 liegt der Fokus auf Hardening, Release-Engineering und einigen gezielten Differenzierungsfeatures

Roadmap:
- [ROADMAP_2026.md](../ROADMAP_2026.md)

Changelog:
- [CHANGELOG.md](CHANGELOG.md)

Feature-Matrix:
- [FEATURES.md](FEATURES.md)

---

## Dokumentation

### Einstieg

- [Dokumentations-Index](INDEX.md)
- [User Manual](guides/USER_MANUAL.md)
- [FAQ](guides/FAQ.md)
- [Troubleshooting](guides/TROUBLESHOOTING.md)

### Betrieb / Release

- [MSI Build Guide](guides/MSI_BUILD.md)
- [Update Phase B](guides/UPDATE_PHASE_B.md)
- [Update Phase C](guides/UPDATE_PHASE_C.md)
- [License Signatures](guides/LICENSE_SIGNATURES.md)

### Workflow / Produkt

- [Workflow](guides/WORKFLOW.md)
- [Auto Selection](guides/AUTO_SELECTION.md)
- [Cleanup](guides/CLEANUP.md)
- [Feedback Setup](guides/FEEDBACK_SETUP.md)

### Sicherheit

- [SECURITY.md](SECURITY.md)

---

## Entwicklung

Tests und lokale Qualitätssicherung laufen über `pytest`.

```powershell
pytest
```

Gezielte UI-/i18n-Regressionsprüfungen liegen unter anderem in:
- `tests/ui`

Das Projekt enthält zusätzlich Build-, Smoke- und Hilfsskripte unter `scripts/`.

---

## Projektstatus in einem Satz

PhotoCleaner ist kein Ideen-Prototyp mehr, sondern eine weit fortgeschrittene Windows-App in der Launch-Vorbereitung, bei der der Restaufwand hauptsächlich in Release-Härtung, Dokumentation und den letzten v1.0-Differenzierungsfeatures liegt.

---

## Lizenz

Proprietär. Details siehe [LICENSE](../LICENSE).
