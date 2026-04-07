# PhotoCleaner 📸

**Intelligente Foto-Verwaltung mit Duplikaterkennung und automatischer Qualitätsbewertung**

[![Version](https://img.shields.io/badge/version-0.8.4-green.svg)](https://github.com/your-repo/photo-cleaner)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Proprietary-lightgrey.svg)](../LICENSE)
[![Status](https://img.shields.io/badge/status-beta--testing-yellow.svg)]()
[![Performance](https://img.shields.io/badge/performance-9.19x_faster-brightgreen.svg)]()

> **v0.8.4 Architecture Refactoring (Apr 4, 2026)**: Slice 6 Workflow Controllers, MSI Distribution Track (WiX v4).

---

## 📑 Inhaltsverzeichnis

- [Überblick](#-überblick)
- [Features](#-features)
- [Schnellstart](#-schnellstart)
- [Installation](#-installation)
- [Final Pipeline](#-final-pipeline-architektur)
- [Verwendung](#-verwendung)
  - [CLI](#cli-kommandozeile)
  - [Grafische UI](#grafische-benutzeroberfläche)
  - [Python API](#python-api)
- [Pipeline-Architektur](#-pipeline-architektur-technische-details)
- [Konfiguration](#-konfiguration)
- [Testing](#-testing--entwicklung)
- [Troubleshooting](#-troubleshooting)
- [Versionen & Updates](#-versionen--updates)
- [Dokumentation](#-zusätzliche-dokumentation)
- [Lizenz](#-lizenz)

---

## 🎯 Überblick

PhotoCleaner ist ein professionelles Werkzeug zur intelligenten Verwaltung großer Foto-Sammlungen. Es kombiniert **Perceptual Hashing**, **MediaPipe Face Mesh** und **intelligentes Scoring**, um automatisch die besten Bilder aus Duplikat-Gruppen auszuwählen und sicher zu löschen.

### Warum PhotoCleaner?

- ✅ **Intelligent**: Gesichtserkennung bewertet Augen, Blick, Kopfhaltung und Lächeln (v0.8.3!)
- ✅ **Schnell**: 9.19x optimierte Pipeline verarbeitet 5.000 Bilder in 2.1 Minuten (v0.7.0!)
- ✅ **Sicher**: Dreistufiges Mode-System (SAFE/REVIEW/CLEANUP) mit Papierkorb-Integration
- ✅ **Flexibel**: CLI, UI und Python API für alle Anwendungsfälle
- ✅ **Beta-Testing**: Stabilisierung nach Pipeline-Fixes, Feedback willkommen

### Typische Anwendungsfälle

- 🏖️ **Urlaubs-Fotos aufräumen**: Automatisch die besten Bilder behalten
- 📱 **Smartphone-Backup bereinigen**: Burst-Mode Duplikate eliminieren
- 📂 **Foto-Archiv konsolidieren**: Mehrere Sammlungen zusammenführen
- 🎯 **Professionelle Sortierung**: Qualitätsbasierte Auswahl für Fotografen

---

## ✨ Features

### Hauptfunktionen

| Feature | Beschreibung | Status |
|---------|-------------|--------|
| **Perceptual Hashing (pHash)** | Erkennt ähnliche Bilder auch bei Rotation/Skalierung | ✅ Production |
| **Face Mesh Analyse** | MediaPipe erkennt Augen, Blick, Kopfneigung | ✅ Production |
| **Automatic Top-N Selection** | Automatisches Ranking der besten Bilder | ✅ Production |
| **Smart Quality Scoring** | Gewichtete Bewertung: Schärfe, Auflösung, Gesicht | ✅ Production |
| **Safe Deletion** | send2trash Papierkorb-Integration | ✅ Production |
| **Results UI** | Interaktive Vorschau mit Thumbnails | ✅ Production |
| **Mode System** | SAFE/REVIEW/CLEANUP für kontrollierten Ablauf | ✅ Production |
| **File Locking** | Schutz vor versehentlichem Löschen | ✅ Production |
| **Parallel Processing** | ThreadPoolExecutor & ProcessPool für schnelle Verarbeitung (v7.0.0: 9.19x speedup!) | ✅ Production |
| **Progress Tracking** | Detaillierte Fortschrittsanzeige | ✅ Production |
| **License System** | Online-Validierung mit Device Binding & Offline Grace Period | ✅ Production |
| **Image Cache** | Persistentes Caching von Analyse-Ergebnissen (2-8x Speedup) | ✅ Production |
| **Internationalization** | Deutsch & Englisch mit echtzeitlichem Sprachenwechsel | ✅ Production |
| **Modern UI** | Moderne Qt6-Benutzeroberfläche mit Light/Dark Theme | ✅ Production |
| **Database Migrations** | Sichere Schema-Evolution mit Rollback-Support (v0.6.0) | ✅ Production |
| **GitHub Actions CI/CD** | Automatisierte Tests, Security Scan, Multi-Platform Build (v0.6.0) | ✅ Production |
| **Performance Profiling** | Baseline Tracking & Regression Detection (v0.6.0) | ✅ Production |

### Technische Highlights

- **6-stufige optimierte Pipeline** (Index → Duplicates → Filter → Analyze → Score → UI)
- **Selective Face Mesh**: Nur auf Duplikat-Gruppen (10-20% der Bilder)
- **Bucketed Comparison**: Effiziente Duplicate Detection
- **Comprehensive Guards**: Locks, Modes, Status History
- **OpenCV + MediaPipe**: State-of-the-art Computer Vision
- **Database Migrations**: 4 sichere Migrationen (V001-V004) mit Checksum-Validierung
- **CI/CD Infrastructure**: 4 GitHub Actions Workflows, 6 Test Environments, 9 Quality Tools

---

## 🚀 Schnellstart

### 3-Minuten Setup

```powershell
# 1. Repository klonen
git clone <repository-url>
cd photo-cleaner

# 2. Dependencies installieren
pip install -r requirements.txt

# 3. Pipeline ausführen
python run_final_pipeline.py ~/Pictures/MyPhotos

# 4. Results UI öffnet sich automatisch → Prüfen → Löschen bestätigen
```

### Ein-Zeilen Befehle

```bash
# Schnell (ohne Face Mesh)
python run_final_pipeline.py ~/Pictures --no-face-mesh

# Streng (nur beste Bilder)
python run_final_pipeline.py ~/Pictures --top-n 1 --hash-dist 2

# Mit Cleanup (Löschen erlaubt)
python run_final_pipeline.py ~/Pictures --mode cleanup
```

---

## 🔧 Installation

### Voraussetzungen

- **Python**: ≥3.12 (empfohlen für volle Kompatibilität)
- **OS**: Windows, Linux, macOS
- **Speicher**: ~500MB-2GB (abhängig von Sammlungsgröße)
- **Festplatte**: ~10GB für Datenbank-Cache (bei 100k+ Bildern)

### Standard Installation

```powershell
# Virtual Environment erstellen (empfohlen)
python -m venv .venv
.\.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Dependencies installieren
pip install -r requirements.txt

# Package installieren
pip install -e .

# Validierung
python run_final_pipeline.py --help
```

### Installation mit dlib (Stage 2 Gesichtserkennung)

Für erweiterte Gesichtserkennung (geschlossene Augen):

```powershell
# Windows: Visual Studio Build Tools erforderlich
# Download: https://visualstudio.microsoft.com/downloads/
# Workload: "Desktop development with C++"

# dlib installieren
pip install dlib

# Stage 2 aktivieren
$env:PHOTOCLEANER_EYE_DETECTION_STAGE="2"
python run_ui.py
```

### Minimal Installation (ohne Face Mesh)

Wenn OpenCV/MediaPipe Probleme bereiten:

```powershell
# Nur Core Dependencies
pip install Pillow imagehash send2trash numpy

# Package installieren (ohne Dependencies)
pip install --no-deps -e .

# Pipeline im No-Face-Mesh Mode nutzen
python run_final_pipeline.py ~/Pictures --no-face-mesh
```

### Installation Troubleshooting

#### Problem: NumPy Build Error (Python 3.14)

```powershell
# Lösung: Pre-built Wheels erzwingen
pip install --only-binary :all: "numpy>=1.24.0,<2.0.0"
```

#### Problem: OpenCV/MediaPipe nicht verfügbar

```powershell
# Face Mesh deaktivieren (Pipeline funktioniert trotzdem!)
python run_final_pipeline.py ~/Pictures --no-face-mesh
```

---

## 🔥 Final Pipeline Architektur

### Pipeline-Übersicht

```
📁 Folder Input
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 1: INDEXING (5-10 Min @ 10k Bilder)                  │
│ - Rekursiver Scan aller Bilder                              │
│ - Perceptual Hash (pHash) Berechnung                        │
│ - Metadaten-Extraktion (Größe, Datum)                       │
│ - Parallel Processing (ProcessPoolExecutor)                 │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 2: DUPLICATE DETECTION (~30 Sek @ 10k Bilder)        │
│ - Hamming Distance ≤ 5 auf pHash                            │
│ - Bucketed Comparison (optimiert)                           │
│ - Gruppierung ähnlicher Bilder                              │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 3: CHEAP FILTER (1-2 Min @ 10k Bilder)               │
│ - ❌ Auflösung < 800x600                                    │
│ - ❌ Unscharf (Laplacian < 50)                              │
│ - ❌ Über-/Unterbelichtet                                   │
│ - OpenCV only (kein AI) → sehr schnell                      │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 4: QUALITY ANALYSIS (5-15 Min, nur auf Gruppen!)     │
│ - MediaPipe Face Mesh (selektiv: 10-20% der Bilder)        │
│ - ✓ Augen offen/geschlossen                                 │
│ - ✓ Blickrichtung (forward/away)                            │
│ - ✓ Kopfneigung (straight/tilted)                           │
│ - ✓ Gesichtsschärfe                                         │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 5: SCORING & TOP-N MARKING (~1 Sek)                  │
│ - Ranking innerhalb jeder Gruppe                            │
│ - Top-N automatisch als KEEP markiert                       │
│ - Rest als DELETE markiert                                  │
└─────────────────────────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────────────────────────┐
│ Stage 6: USER DECISION (Results UI)                         │
│ - Top-N grün markiert (KEEP)                                │
│ - Rest rot markiert (DELETE)                                │
│ - Thumbnail-Vorschau mit Scores                             │
│ - Delete Button mit Bestätigung                             │
└─────────────────────────────────────────────────────────────┘
    ↓
🗑️ Safe Deletion oder ✅ Keep
```

### Performance

| Komponente | Zeit @ 10k Bilder | Bottleneck |
|------------|-------------------|------------|
| Indexing | 5-10 Min | Disk I/O |
| Find Duplicates | ~30 Sek | Hash Vergleich |
| Cheap Filter | 1-2 Min | OpenCV |
| **Face Mesh** | **5-15 Min** | **MediaPipe** |
| Scoring | ~1 Sek | Database |
| **Total** | **12-28 Min** | **Face Mesh** |

---

## 💻 Verwendung

### CLI (Kommandozeile)

```bash
# Standard: Review-Mode mit Face Mesh
python run_final_pipeline.py ~/Pictures/Vacation2024

# Schnell: ohne Face Mesh
python run_final_pipeline.py ~/Pictures/Vacation2024 --no-face-mesh

# Streng: nur beste Bilder
python run_final_pipeline.py ~/Pictures/Vacation2024 --top-n 1 --hash-dist 2

# Cleanup: mit Löschen erlaubt
python run_final_pipeline.py ~/Pictures/Vacation2024 --mode cleanup
```

#### Alle CLI-Optionen

```powershell
--top-n N                    # Top-N Bilder pro Gruppe behalten (default: 3)
--hash-dist N                # Hamming-Distanz Schwelle (default: 5)
--no-face-mesh              # Face Mesh deaktivieren
--mode {safe|review|cleanup} # App-Mode (default: review)
--min-resolution WIDTHxHEIGHT  # Minimale Auflösung (default: 800x600)
--sharpness-threshold N        # Schärfe-Schwelle (default: 50)
--db PATH                    # Database-Pfad
--no-ui                     # Keine UI starten
--force-reindex             # Alle Dateien neu indizieren
-v, --verbose               # Detailliertes Logging
```

### Grafische Benutzeroberfläche

PhotoCleaner bietet **zwei UI-Optionen**:

#### 🎨 Modern UI (Empfohlen) - NEU!

Komplett überarbeitete UI mit modernem Design:

```powershell
# Mit bestehender Datenbank
python test_modern_ui.py

# Oder direkt
python -m photo_cleaner.ui.modern_window
```

**Features:**
- ✨ Grid-Layout mit großen Thumbnail-Cards
- 🔍 **Zoom-Funktion** (Mausrad, +/-, Doppelklick)
- 📊 **EXIF-Daten** strukturiert anzeigen (Kamera, Belichtung, GPS)
- 🎴 Moderne Card-basierte Optik mit Animationen
- 🖱️ Detail-Ansicht per Klick mit Pan-Funktion
- 🎨 4 Themes: Dark, Light, System, High-Contrast
- ⚡ Schnellere Navigation mit Keyboard Shortcuts

📖 **Dokumentation:** siehe [guides/USER_MANUAL.md](guides/USER_MANUAL.md) und [guides/FAQ.md](guides/FAQ.md)

#### 🖥️ Classic UI (Legacy)

Die bewährte UI für Produktions-Workflows:

```powershell
python run_ui.py
```

**Features:**
- ✅ Gruppe-für-Gruppe Navigation
- ✅ Thumbnail-Vorschau (128×128px)
- ✅ 3-Panel-Layout (Gruppen | Vorschau | Details)
- ✅ Mode & Theme Dropdowns
- ✅ Hotkey-Unterstützung

**Beide UIs sind voll kompatibel** - sie nutzen dieselbe Datenbank und können beliebig gewechselt werden!

### Python API

```python
from pathlib import Path
from photo_cleaner.pipeline import run_final_pipeline

stats = run_final_pipeline(
    folder_path=Path("~/Pictures/Vacation"),
    db_path=Path("photos.db"),
    top_n=3,
    hash_dist=5,
    use_face_mesh=True,
)

print(f"Gefunden: {stats.duplicate_groups} Gruppen")
print(f"Markiert: {stats.marked_delete} zum Löschen")
```

---

## 🧪 Testing & Entwicklung

### Test-Bilder generieren

```powershell
# Basic Test Set
python scripts/test_image_generator.py --mode basic --output test_images

# Duplicate Groups
python scripts/test_image_generator.py --mode groups --output test_groups --groups 10

# Performance Test
python scripts/test_image_generator.py --mode performance --output test_big --count 5000
```

### Unit Tests

```powershell
pytest tests/
pytest tests/ --cov=photo_cleaner --cov-report=html
```

---

## 🐛 Troubleshooting

### Installation Issues

```powershell
# NumPy Build Error
pip install --only-binary :all: "numpy>=1.24.0,<2.0.0"

# OpenCV/MediaPipe nicht verfügbar
python run_final_pipeline.py ~/Pictures --no-face-mesh
```

### Runtime Issues

```powershell
# Zu langsam
python run_final_pipeline.py ~/Pictures --no-face-mesh --top-n 1

# Zu viele False Positives
python run_final_pipeline.py ~/Pictures --hash-dist 3

# Zu wenige Duplikate
python run_final_pipeline.py ~/Pictures --hash-dist 8
```

**EXE-Logs (Windows):** `%APPDATA%\\PhotoCleaner\\PhotoCleaner.log`

**MTCNN/TensorFlow DLL-Fehler:**
- Stelle sicher, dass der komplette Ordner `dist\\PhotoCleaner\\` kopiert wurde (nicht nur die EXE)
- Logfile pruefen: `%APPDATA%\\PhotoCleaner\\PhotoCleaner.log`

---

## 📊 Versionen & Updates

**Aktuelle Version:** 0.8.4 (Architecture Refactoring + MSI Distribution)  
**Release:** April 4, 2026  
**Status:** Beta-Testing

### Version 0.8.4 Highlights (Latest Release)

- ✅ **Slice 6 Refactoring**: 4 Workflow-Controller aus `modern_window.py` extrahiert
- ✅ **Legacy Deprecation**: `main_window.py`/`cleanup_ui.py` sichtbar markiert
- ✅ **Website Bundles**: Gemeinsame CSS/JS-Assets konsolidiert
- ✅ **MSI Distribution**: WiX v4 Build-Pfad, reproduzierbares Skript, Smoke-Test-Protokoll

### Version History

| Version | Highlights | Datum |
|---------|-----------|-------|
| **0.8.4** | Architecture Refactoring (Slice 6), MSI Distribution Track | Apr 4, 2026 |
| **0.8.3** | Stabilisierung, Pipeline Sequencing, Rating-Fixes | Feb 22, 2026 |
| **0.8.2** | Performance Tuning (Cheap Filter, HEIC, Profiling) | Feb 7, 2026 |
| **0.6.0** | Database Migrations, CI/CD Pipeline, Performance Profiling | Feb 15, 2026 |
| **0.5.6** | MTCNN Performance (6-10x), File Validation, UI Polish | Feb 1, 2026 |
| **0.5.5** | i18n System, Light-Theme Polish, Credential Fallback | Jan 30, 2026 |
| **0.5.3** | Online License System, Cloud Validation, Device Binding | Jan 26, 2026 |
| **0.5.2** | MediaPipe Caching (10-100x Speedup), Session Persistence | Jan 26, 2026 |
| **0.5.0** | 6-Stage Pipeline, Face Mesh Analysis, Modern UI | Jan 2026 |

Siehe [CHANGELOG.md](CHANGELOG.md) für Details.

## 📚 Dokumentation

### Kategorisiert nach Thema

**[Tech Documentation](tech/INDEX.md)** - Technische Details
- Cache System und Optimierungen
- Database Migrations
- UI Theming System
- Performance Analysis

**[Standards & Quality](standards/INDEX.md)** - Qualitätssicherung
- Code Audit Report (16 critical bugs fixed)
- Bug Fix Quick Guide (P0-P1-P2)
- Workflow & Datensicherheit

**[Guides & How-To](guides/INDEX.md)** - Anleitungen
- Contributing Guidelines
- License System
- Feedback System Setup

**[Architecture](architecture/INDEX.md)** - Systemdesign
- Pipeline Architecture
- Module Documentation
- Class Diagrams

### Weitere Ressourcen

- [INDEX.md](INDEX.md) - zentraler Dokumentations-Einstieg
- [CHANGELOG.md](CHANGELOG.md) - Vollständige Version History
- [feedback/README.md](../feedback/README.md) - Feedback sammeln (Offline JSON)
- [SECURITY.md](SECURITY.md) - Security Policy

---

## 🤝 Beitragen

Contributions sind willkommen! Siehe [guides/CONTRIBUTING.md](guides/CONTRIBUTING.md).

---

## 📄 Lizenz

Proprietary License - siehe [LICENSE](../LICENSE)

---

**Viel Erfolg beim Aufräumen deiner Foto-Sammlung!** 📸✨

<p align="center">
  Made with ❤️ by the PhotoCleaner Community
</p>

