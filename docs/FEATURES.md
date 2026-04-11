# 📋 PhotoCleaner v0.8.7 - Komplette Feature-Liste

## 🎯 Überblick

PhotoCleaner ist eine intelligente Foto-Verwaltungsanwendung mit fortgeschrittener KI-Analyse, benutzerfreundlicher Oberfläche und professionellen Funktionen für die Bildverwaltung.

**Statistik**: 8+ Kernfunktionen • 7 Dialoge • 6 Sprachen • 4 KI-Backend • 50+ Features insgesamt

---

## 1. 🔍 CORE ANALYSE-ENGINE

### Duplizierte Erkennung
- **Perceptual Hashing**: pHash-basierte Bildvergleiche
- **Hamming-Distanz** für Ähnlichkeitserkennung
- **Bucketing System**: Effiziente Gruppenbildung
- Automatische Gruppierung ähnlicher Bilder

### Gesichtserkennung
- **4-stufiges Falling-Back System**:
  - Stufe 1: MediaPipe Face Mesh (schnell, modern)
  - Stufe 2: dlib (genau, klassisch)
  - Stufe 3: MTCNN (robust, tiefes Learning)
  - Stufe 4: Haar Cascade (Fallback)
- Konfigurierbar pro Session
- Confidence-Thresholds anpassbar
- Minimale Augengröße einstellbar

### Augenqualitäts-Analyse
- **Augengüte-Lanalyse**: Offenheit, Fokus, Ausrichtung
- **Blickrichtung**: Gaze Direction Erkennung
- **Kopfhaltung**: Head Pose Detection
- **Lächel-Erkennung**: Smile Detection
- **Schärfe-Analyse**: Gesicht-Schärfe Bewertung
- Detaillierte per-Image Metriken

### Bildqualitäts-Bewertung
- **Mehrdimensionale Analyse**:
  - Unschärfe / Schärfewert
  - Helligkeit / Belichtung
  - Kontrast
  - Rauschen
- **Auflösung Analysis**:
  - Megapixel-Bewertung
  - DPI-Check
  - Seitenverhältnis
- **Kamera-Profil Kalibrierung**
- Gewichtete Scoring-Formeln

### EXIF-Datenextraktion
- **Vollständige Metadaten**:
  - Kameramodell
  - ISO, Blende, Verschlusszeit
  - Brennweite
  - GPS-Koordinaten
  - Aufnahmedatum/Uhrzeit
- **Fallback Parsing**: Fehlerbehandlung bei beschädigtem EXIF
- **Zeitstempel-Normalisierung**

### Auto-Auswahlystem
- **Intelligente Empfehlungen**: Keep/Delete automatisch vorschlagen
- **Top-N Ranking**: Beste Bilder pro Gruppe priorisieren
- **Dynamische Bewertung**: Gruppengröße-abhängige Schwellwerte
- **Multi-Parameter Gewichtung**: Kombinierte Scoring-Formeln
- Benutzer-anpassbare Presets

---

## 2. 🖥️ BENUTZEROBERFLÄCHE

### Modernes Qt6-Hauptfenster
- **Dreispaltenlayout**:
  - Links: Gruppen-Panel mit Statistiken
  - Mitte: Rasteransicht Thumbnails
  - Rechts: Detail-Panel mit Metadaten
- **Seite-an-Seite Vergleich**: Mehrere Bilder gleichzeitig vergleichen
- **Responsives Design**: Splitter-basierte Größenverstellung
- **Dunkles/Helles Theme**: Vollständig durchgestylt

### Duplikat-Gruppen-Panel
- **Kompakte Anzeige** von Bildgruppen
- **Farbcodierung**:
  - Grün: Keine Probleme erkannt
  - Rot: Warnung/Empfehlung
  - Grau: Verarbeitete Gruppe
- **Filter-Schalter**:
  - Nur offene Gruppen
  - Nur niedrige Konfidenz
  - Nur große Gruppen
- **Sortierung**: Nach Größe, Konfidenz, Status
- **Kontext-Menüs**: Split, Merge, Auto-Select

### Thumbnail-Raster
- **Lazy-Loading**: Bilder bei Bedarf laden
- **Memory-Cache**: LRU-Caching für Aufführung
- **Disketten-Cache**: Persistente Thumbnail-Speicherung
- **Zoom-Steuerung**: +/- Buttons für Vorschauen
- **Mehrfach-Auswahl**: Checkboxen für Batch-Operationen
- **Sortieroptionen**: Nach Name, Datum, Größe, Qualität

### Analyse-Fortschritts-Dialog
- **4-Stufen Workflow**:
  1. **Scanning** (Dateiindex)
  2. **Grouping** (Duplikat-Erkennung)
  3. **Rating** (Qualitäts-Analyse)
  4. **Finalization** (Vorbereitung)
- **Pro-Stufe Fortschrittsbalken**
- **ETA-Berechnung**: Verbleibende Zeit aktualisiert
- **Live-Log Panel**: Terminal-stil Logging mit per-Bild-Nachrichten
  - Emoji-Prefix (📷 📊 ✓ ⚠️ 👥)
  - Detaillierte Ergebnisse pro Bild
  - Auto-Scroll zu neuesten Einträgen
- **Abbruch-Möglichkeit**: Stop-Button während Analyse

### Einstellungs-Dialog
- **System Tab**:
  - Sprache wechseln (6 Sprachen)
  - Theme (Dunkel/Hell)
  - Fenstergeometrie
- **Bildqualität Tab**:
  - Qualitäts-Presets
  - Schwellen-Werte anpassen
  - Gewichtungen konfigurieren
- **Cache Tab**:
  - Cache-Größe anzeigen
  - Cache leeren
  - Cache-Verzeichnis
- **Lizenz Tab**:
  - Free/Pro Status
  - Aktivierung
  - Geräte-Binding Info
- **Wartung Tab**:
  - Datenbank-Info
  - Abhängigkeits-Check
  - GPU-Status
  - Diagnostik-Export

### Lizenz-Dialog
- **Status-Anzeige**:
  - Free-Tier: 250 Bilder/Session
  - PRO-Tier: Unbegrenzt
- **Aktivierungs-Input**: Mit Cloud-Verbindung
- **Geräte-Binding**: Sicherheit via SHA256-Hashing
- **Gültigkeit**: Grace-Period Info (7 Tage offline)
- **Upgrade-Optionen**: Link zu PRO-Abos

### Onboarding-Tour
- **Erste-Start-Hilfe**: Optional beim Start
- **Schritt-für-Schritt Anleitung**:
  - Ordner öffnen
  - Analyse ausführen
  - Bilder bewerten
  - Löschen ausführen
- **Abschließbär**: Nicht erneut anzeigen (persistent)

### Augendetektions-Voreinstellungen
- **Stufen-Auswahl**: MediaPipe, MTCNN, dlib, Haar Cascade
- **Konfidenz-Schwelle**: 0.0-1.0 anpassbar
- **Augengröße Minimum**: Pixelgröße einstellen
- **Live-Vorschau**: Auswirkungen sofort sichtbar

---

## 3. ⌨️ TASTATUR-VERKNÜPFUNGEN & NAVIGATION

| Taste | Funktion | Kategorie |
|-------|----------|-----------|
| **K** | Markiere als BEHALTEN | Entscheidung |
| **D** | Markiere als LÖSCHEN | Entscheidung |
| **U** | Markiere als UNSICHER | Entscheidung |
| **Z** | Letzte Entscheidung rückgängig | History |
| **S** | Gruppe aufteilen | Gruppen-Ops |
| **M** | Gruppen zusammenfassen | Gruppen-Ops |
| **↑ / ↓** | Durch Bilder navigieren | Navigation |
| **← / →** | Zwischen Gruppen wechseln | Navigation |
| **Ctrl+J / Ctrl+K** | Schnelle Gruppen-Navigation | Navigation |
| **+ / -** | Zoom in/out | Ansicht |
| **Home / End** | Erstes/Letztes Bild | Navigation |
| **Tab** | Fokus zwischen Panels | Navigation |

---

## 4. 🌍 DESIGN & LOKALISIERUNG

### Dunkles/Helles Theme
- **Vollständiges Qt6-Stylesheet Theming**
- **Echtzeit-Toggle**: Keine Neustarts erforderlich
- **Konsistentes Styling**: Alle Komponenten durchgestylt
- **Benutzerdefiniert**: Farb-Paletten konfigurierbar (bei Bedarf)

### Unterstützte Sprachen
- 🇩🇪 **Deutsch** (DE)
- 🇬🇧 **Englisch** (EN)
- 🇫🇷 **Französisch** (FR)
- 🇪🇸 **Spanisch** (ES)
- 🇳🇱 **Niederländisch** (NL)
- 🇮🇹 **Italienisch** (IT)

### Lokalisierungs-System
- **JSON-basierte Locale-Dateien**: Leichte Verwaltung
- **Fallback zu Englisch**: Fehlende Übersetzungen abfangen
- **Echtzeit-Umschaltung**: Sprache wechseln ohne Neustart
- **Terminologie-Leitfaden**: Standardisierte Begriffe

---

## 5. 🎮 WORKFLOWS-MODI

| Modus | Löschen | Batch | Ähnlich | Beschreibung |
|-------|--------|-------|--------|--------------|
| **SICHER** (Safe) | ❌ | ❌ | ❌ | Niedrigstes Risiko, nur Empfehlungen |
| **REVIEW** | ❌ | ❌ | ✅ | Manuelle Markierung ohne Löschung |
| **CLEANUP** | ✅ | ✅ | ✅ | Vollständiges Löschen & Batch-Operationen |

---

## 6. 📁 DATEI-OPERATIONEN

### Markierung-System
- **Behalten (KEEP)**: Speichern im Archiv
  - Gesperrt: Verhindert versehentliche Änderung
  - Lock-Grund wird aufgezeichnet
- **Löschen (DELETE)**: In Papierkorb verschieben
  - send2trash Integration
  - Wiederherstellbar
- **Unsicher (UNSURE)**: Zur manuellen Überprüfung markiert

### Rückgängig-System
- **Letzter Aktion umkehren**: Z-Taste
- **Action-Verlauf**: Timestamp & ID getrackt
- **Multi-Level**: Beliebig viele Rückgängig-Operationen

---

## 7. 📤 EXPORT & BEREINIGUNG

### YYYY/MM/DD Export
- **Zeitstempel-Struktur**: Nach EXIF-Datum organisiert
  - Format: `2024/12/25/IMG_1234.jpg`
  - Fallback auf mtime wenn EXIF fehlt
- **Kollisions-Vermeidung**: Duplikat-Namen handhaben
- **Streaming-Export**: Für 50k+ Dateien memory-effizient

### Streaming-ZIP Export
- **Memory-effizient**: Dateien einzeln streamen, nicht gepuffert
- **Große Kapazität**: 50k+ Bilder ohne RAM-Probleme
- **Progress-Tracking**: Upload-Fortschritt anzeigen

### Sichere Löschung
- **Papierkorb-Integration**: send2trash für Wiederherstellung
- **Gesperrte Datei-Schutz**: Verhindert versehentliches Löschen
- **Teilweise Fehlerbehandlung**: Mit Fehler-Zusammenfassung fortfahren
- **Verzeichnis-Bereinigung**: Leere Ordner aufräumen

### Fertigstellungs-Feedback
- **Statistik-Zusammenfassung**:
  - Gelöschte Dateien
  - Freigespielter Speicherplatz
  - Fehler-Zusammenfassung
- **Erfolgs-Animation**: Visuelle Bestätigung
- **Festplatte-Anwendung**: Größen-Details anzeigen

---

## 8. 🔐 LIZENZIERUNG & CLOUD

### FREE-Tier
- **250 Bilder pro Session**
- **Offline-fähig**: Mit 7-Tage Grace Period
- **Grundfunktionen**: Analyse, Bewertung (kein Löschen)

### PRO-Tier
- **Unbegrenzte Bilder**
- **Batch-Löschen**: Mehrere Operationen ermöglicht
- **HEIC-Support**: Erweiterte Format-Unterstützung
- **Erweiterter Cache**: Größere Speichergrenzen
- **Jährliches Abonnement**: Cloud-aktiviert

### Cloud-Aktivierung
- **Supabase PostgREST Backend**: Benutzer-Verwaltung
- **Geräte-Binding**: SHA256-Hash für Sicherheit
- **Ed25519 Signaturen**: Kryptografische Validierung
- **Offline-Grace-Periode**: 7 Tage ohne Internet

### Lizenz-Resilienz
- **Exponentielles Backoff**: Bei Cloud-Fehler Retry
- **Retry-After Support**: Cloud-Raten respektieren
- **DNS-Failfast**: Schnelle Erkennung von Ausfällen
- **Budget-begrenzte Retries**: Zu viele Versuche verhindern

### Features-MAP
| Tier | Funktionen |
|------|-----------|
| FREE | Analyse, Bewertung, Theme, Export-Vorschau |
| PRO | + Batch-Löschen, HEIC, Erweiterter Cache, Unbegrenzte Bilder |

---

## 9. ⚡ LEISTUNG & OPTIMIERUNG

### Parallele Verarbeitung
- **ThreadPoolExecutor**: Dateien-Indexing
- **ProcessPoolExecutor**: KI-Analyse (CPU-gebunden)
- **Adaptive Worker-Anzahl**: Basierend auf Gruppengröße & CPU-Budget

### Thumbnail-Caching
- **Zwei-Schicht System**:
  - RAM: LRU in-Memory Cache (schnell)
  - Disk: SQLite-persistent (sparen)
- **Lazy-Loading**: Bei Scroll laden nach Bedarf
- **Speicher-Effizienz**: Begrenzte RAM-Nutzung

### Qualitäts-Score-Caching
- **SQLite-Persistierung**
- **2-8x Beschleunigung**: Bei Neu-Analyse
- **Invalidierungspolitik**: Nach Parameter-Änderung

### Progress-Drosseln
- **Event Rate-Limiting**: UI-Repaint-Last reduzieren
- **Batch-Updates**: Mehrere Änderungen zusammenfassen
- **ETA-Berechnung**: Glatte Fortschritts-Anzeige

### Batch-Operationen
- **executemany SQLite**: Weniger Statements
- **Transaktionen**: Atomare Operationen
- **Bulk-Delete**: Optimierte SQL für Massenlöschung

### Performance-Metriken
- **Stage-Time Profiling**: Jede Phase gemessen
- **Event Counting**: Fortschritts-Events gezählt
- **JSON Export**: Für Analyse speichern
- **Baseline**: 5k Bilder in ~2.1 Minuten (9.19x schneller als v0.6)

---

## 10. 📊 QUALITÄTS-PRESETS

### System-Presets
| Preset | Fokus | Details |
|--------|-------|---------|
| **Standard** | Balance | Standard-Anforderungen |
| **Streng** | Exzellenz | Nur beste Bilder |
| **Locker** | Permissiv | Lenient, akzeptiert Variationen |
| **Porträt** | Gesichter | Für Gesichts-fokussierte Fotos |
| **Landschaft** | Weitwinkel | Für Architektur/Szenerie |
| **Benutzer** | Custom | Persönliche Presets speichern/laden |

### Preset-Konfiguration
- **Augendetektions-Modus**: Welche KI-Pipeline
- **Gesichts-Konfidenz**: Minimum für Erkennung
- **Qualitäts-Gewichtungen**:
  - Blur/Schärfe
  - Helligkeit/Belichtung
  - Kontrast
  - Rauschen
- **Flags**: Boolean-Optionen für Verhalten

---

## 11. 👥 GRUPPEN-INTELLIGENZ

### Konfidenz-Klassifizierung
- **Sehr Zuverlässig**: High-confidence Ergebnis
- **Review Empfohlen**: Moderate confidence
- **Review Erforderlich**: Low confidence
- **Daten Unvollständig**: Fehlerhafte/unvollständige Analyse

### Smart-Filtering
- **Filter-Toggles**:
  - Nur offene Gruppen
  - Nur Niedrig-Konfidenz
  - Nur große Gruppen
- **Aktive Filter-Anzeige**: Was ist aktuell gefiltert?
- **Schnelle Filterung**: Auf Knopfdruck

### Gruppen-Operationen
- **Split**: Gruppe in Untergruppen teilen
- **Merge**: Mehrere Gruppen zusammenführen
- **Async-Rerating**: Mit detaillierten Phasen erneut bewerten
- **Checkbox-Selektion**: Multi-select für Batch-Ops

---

## 12. 💻 COMMAND-LINE INTERFACE

| Befehl | Funktion | Optionen |
|--------|----------|----------|
| **index** | Recursiv Fotos indexieren | `--skip-existing`, `--workers N` |
| **stats** | Datenbank-Statistiken zeigen | `--db PATH` |

---

## 13. 💾 DATENBANK & SPEICHERUNG

### SQLite-Datenbank
- **Schema-Migrationen**: V001-V004
- **Checksum-Validierung**: Integritätsprüfung
- **Transaktionale Sicherheit**: ACID-Eigenschaften

### Repositories
- **File-Repository**: Status-Tracking, Sperren, Metadaten
- **History-Repository**: Aktions-Verlauf, Undo/Redo
- **User-Settings**: JSON-Speicherung (Sprache, Theme, Geometrie)
- **Session-Snapshots**: Wiederherstellungs-Unterstützung

---

## 14. 🖼️ UNTERSTÜTZTE DATEI-FORMATE

### Bilder
- JPG, JPEG, PNG, BMP, TIFF, HEIC, HEIF, GIF, WEBP

### Metadaten
- **EXIF**: Vollständig extrahiert
- **GPS**: Koordinaten unterstützt
- **IPTC**: Basis-Extraktion
- **XMP**: Basis-Unterstützung

---

## 15. 🎁 SPEZIELLE FUNKTIONEN

### Eye-Mode
- **Detaillierte Metriken**: Pro-Bild Qualitäts-Werte anzeigen
- **Real-Time Stufen-Info**: KI-Pipeline-Verarbeitung live zeigen

### Score-Erklärung
- **Komponenten-Breakdown**: Warum Bild so bewertet?
- **Gewichtungsanzeige**: Wie wirken sich Parameter aus?

### Review-Anleitung
- **Dynamische Hinweise**: Basierend auf Konfidenz & Status
- **Next-Step-Empfehlungen**: Was tun mit dieser Gruppe?

### Quota-Verbrauchte-Nachrichten
- **FREE-Tier Indikatoren**: Bilder-Limit anzeigen
- **Upgrade-Prompts**: Zum PRO hinweisen wenn nötig

### System-Introspektionm
- **GPU-Erkennung**: CUDA/TensorFlow Verfügbarkeit
- **Build-Tools-Check**: PyInstaller, etc. vorhanden?
- **Abhängigkeits-Matrix**: Welche Features verfügbar?

---

## 16. 🛡️ FEHLERBEHANDLUNG & ROBUSTHEIT

### KI-Fallback-Kette
- **MediaPipe** → **dlib** → **MTCNN** → **Haar Cascade** → Graceful Degradation
- **Import-Fallbacks**: HEIC ohne pillow-heif, GPU Auto-Disable
- **Thread-Sicherheit**: Qt Object Validierung, Callback-Schutz

### User-freundliche Fehler
- **Terminologie-Compliance**: Konsistente Begriffe
- **Aktions-Anleitung**: Was kann der Benutzer tun?
- **Gekürzte Fehler-Listen**: Nicht überlasten

---

## 17. ⚙️ KONFIGURATION & ANPASSUNG

### Environment-Variablen
- `PHOTOCLEANER_MODE`: Applikations-Modus
- `PHOTOCLEANER_DEBUG`: Debug-Logging aktivieren
- `PHOTOCLEANER_EYE_DETECTION_STAGE`: KI-Pipeline auswählen
- `CUDA_VISIBLE_DEVICES`: GPU-Selektion

### Cloud-Konfiguration
- **Supabase Credentials**: Build-zeitlich injizieren
- **MSI-Build-Optionen**: Bei Erstellung setzen

### Build-Zeit-Optionen
- **PyInstaller Spec**: Dateistruktur definieren
- **DLL-Bundling**: Abhängigkeiten einpacken
- **Build-Hooks**: Spezielle Behandlung
- **Version-Strings**: Über run_ui.py zentral

---

## 18. 🚀 ERWEITERTE FÄHIGKEITEN

- ✅ **Multi-Bild Batch-Verarbeitung** mit Progress
- ✅ **Streaming ZIP-Export** für 50k+ Dateien
- ✅ **Geräte-Binding** für Lizenz-Sicherheit
- ✅ **Offline-Betrieb** mit 7-Tage Grace Period
- ✅ **Seite-an-Seite EXIF-Vergleich** (v0.8.3 fix)
- ✅ **Smart Fallback-Modi** für fehlende ML-Modelle
- ✅ **Adaptive Worker-Verteilung** basierend auf Bild-Anzahl
- ✅ **Cache-Statistiken** & Management
- ✅ **JSON-Profiling Export** für Performance-Analyse
- ✅ **First-Run Onboarding** mit Zustand-Persistierung
- ✅ **Live Analyse-Log Panel** mit per-Bild-Nachrichten (v0.8.6)
- ✅ **Detaillierte Fortschritts-ETA** mit Phasen-Tracking

---

## 19. 🪟 WINDOWS-SPEZIFISCHE FUNKTIONEN

| Feature | Details |
|---------|---------|
| **MSI-Installer** | WiX v4, automatisches Build-Script, Cloud-Konfiguration injiziert |
| **Frozen Build** | PyInstaller-Unterstützung, DLL-Bundling, CPU-only TensorFlow |
| **Benutzer-Daten-Pfade** | APPDATA-Integration, AppLocal Cache Dir |
| **DLL-Auflösung** | Multi-Pfad-Suche (intern, tensorflow, vc_runtime Subdir) |

---

## 📊 FEATURE-STATISTIKEN

```
Core-Analyse Features:         8+
Major UI-Dialoge:              7
Unterstützte Sprachen:         6
Gesichts-Erkennungs-Backend:  4
Qualitäts-Scoring Dimensionen: 5+
Datei-Status-Typen:           4
Applikations-Modi:            3
Presets (Built-in + Custom):  6+
Unterstützte Bildformate:     9+
Tastatur-Shortcuts:           15+
Parallele Verarbeitungs-Pool: 2
Lizenz-Tiers:                 2
```

---

## 📈 VERSIONS-HIGHLIGHTS

### v0.8.7 (Aktuell)
- ✨ Live Analysis Log Panel mit per-Bild-Nachrichten
- 🔧 Finalize Hang Fix
- 📊 Detaillierte per-Image Logs mit Emoji-Präfixe

### v0.8.5
- 🎨 Animated Completion Dialog
- 📁 Dated Folder Export (YYYY/MM/DD)
- 🔢 Auto-Padding Counter

### v0.8.0+
- Multilingual Support (6 languages)
- Trial/Licensing System
- Quality Presets
- Batch Operations

---

## 🎯 GEPLANTE FEATURES & ROADMAP-IDEEN (2026+)

### 🧠 Analyse & KI (Erweiterte ML)

#### Personen-Clustering (Identity Grouping)
- **Automatische Gesichts-Identität Gruppierung**: Alle Fotos derselben Person automatisch zusammenfassen
- **Ohne Namenseingabe**: Nur visuelle Erkennung, dann manuell benennen (optional)
- **Cross-Event Linking**: Dieselbe Person über mehrere Fotosets hinweg erkennen
- **Potenzial**: Ideal für Familien-Verwaltung, Event-Fotografie

#### RAW-Format Support
- **Formate**: .CR2 (Canon), .NEF (Nikon), .ARW (Sony), .RAF (Fujifilm), .DNG
- **Metadaten-Extraktion**: EXIF auch aus RAW
- **Preview-Thumbnail**: Schnelle Vorschau ohne vollständiges Decoding
- **Zielgruppe**: Hobby-Fotografen, professionelle Fotographen

#### Video-Duplikaterkennung
- **Thumbnail-Extraktion**: Keyframes aus Video extrahieren
- **Perceptual Hash Matching**: Video-Thumbnails gegen Bilder/Videos abgleichen
- **Unterstützung**: MP4, MOV, AVI (je nach verfügbaren Codecs)
- **Use-Case**: Versehentlich mehrfach aufgenommene Videos finden

#### Blur-Ursache-Differenzierung
- **Bewegungsunschärfe erkennen**: Richtungsunschärfe-Analyse
- **Fokus-Fehler**: AF-Misfire Erkennung
- **Kamerawackeln**: Kurzzeitiges Verwackeln vs. Bewegung
- **Score-Impact**: Detailliertere Erklärung im Score-Breakdown
- **Smart Filtering**: Bilder nach Blur-Typ filtern

---

### 📍 Organisation & Verwaltung

#### "Best-of-Day" Automatik
- **Tages-Gruppierung**: Nach EXIF Datum (nicht nur nach Duplikaten)
- **Auto-Top-N Selection**: Z.B. "Top 5 Fotos pro Tag" automatisch herausfiltern
- **Adaptive Logic**: Schwelle basierend auf Gesamtanzahl & Qualität
- **Export Option**: "Best-Of" Sammlung direkt exportieren

#### GPS-Kartenansicht
- **Standort-Visualisierung**: Interaktive Karte (Google Maps / Leaflet API)
- **Cluster-Anzeige**: Pinpoints für Fotogruppen nach Ort
- **Ortsnamen-Lookup**: Reverse Geocoding optional
- **Filter nach Ort**: "Alle Fotos von Venedig" schnell filtern
- **Verwandtschaft**: Auto-Gruppierung nach geografischer Nähe

#### Batch-Rename nach EXIF-Schema
- **Präsets Beispiele**:
  - `YYYY-MM-DD_Location_###.jpg`
  - `YYYY_Month_CameraModel_###.jpg`
  - `Event_YYYY-MM-DD_###.jpg`
- **Vor-Vorschau**: Zeige umbenenntes Ergebnis vor Ausführung
- **Duplikat-Handling**: Automatisch hochzählen bei Konflikten
- **Rollback-Option**: Falls Fehler, rückgängig machen

#### Folder-Watcher / Auto-Import
- **Directory Monitoring**: Überwachen eines Ordners auf neue Fotos
- **Auto-Analyse**: Neue Bilder automatisch indexieren & analysieren
- **Background-Modus**: Läuft im Hintergrund, optional als Tray-Anwendung
- **Benachrichtigungen**: "5 neue Fotos hinzugefügt, analysiert"
- **Scheduling**: Zeitgesteuerte Indexing-Runs (z.B. täglich nachts)

---

### 🎨 UX-Verbesserungen

#### "Regret Protection" – Rückgängig nach Löschen
- **Undo-Dialog-Widget**: Im Abschluss-Dialog nach dem Löschen anzeigen
- **Zeitlich begrenzt**: Z.B. 60 Sekunden, dann automatisch commited
- **Rückgängig-Button**: "Löschen rückgängig machen" – send2trash zurück
- **Mehrfach-Nutzbar**: Mehrere Serien nacheinander rückgängig machen
- **Voraus-Bestätigung**: "Wirklich endgültig unwiederbringlich?"

#### Vergleichsmodus mit Referenzbild
- **Benchmark-Pin**: Ein Foto der Gruppe als Referenz festpinnen (📌)
- **Side-by-Side Layout**: Benchmark vs. andere, über alle wechseln
- **Vergleichs-Metriken**: Zeige Unterschiede (Qualität, Schärfe, Belichtung)
- **Schnelle Navigation**: Pfeile um durch Gruppe neben Benchmark zu gehen
- **Batch-Decision**: "Alle besser als Benchmark" → alle behalten
- **Nützlich für**: Duplikat-Auswahl, qualitativ beste herausfiltern

#### Speicherplatz-Preview (Vorher/Nachher)
- **Vorher-Größe**: Aktuelle Gesamtgröße anzeigen
- **Nachher-Berechnung**: Größe nach geplanten Löschungen
- **Freiwerdender Platz**: Prominente Anzeige (z.B. "Freigeben: 3.5 GB")
- **Visueller Progress-Bar**: Balken, der Speicherreduktion zeigt
- **Impact-Visualisierung**: Macht Nutzen greifbar ("Das sind X Spielfilme")
- **Platzierung**: Im Cleanup-Abschluss-Dialog über Delete-Button

---

### 📊 Pro-Features für Monetarisierung

#### Statistik-Dashboard (PRO-only)
- **KPI-Visualisierung**:
  - Fotos pro Monat (Zeitreihe)
  - Top Kameras nach Anzahl
  - Durchschnittliche Qualität (pro Monat / pro Kamera)
  - Duplikat-Rate (%)
  - Speicherplatz-Erweiterung over time
- **Charting**: Graphs, Pie-Charts, Bar-Charts
- **Export**: Statistik als PDF/CSV
- **Zeitfilter**: Nach Datum-Range filtern
- **Camera-Profiling**: Welche Kamera macht best/worst Fotos?
- **Trend-Analyse**: "Qualität steigt mit neuer Kamera" Inferenz
- **Motivations-Hook**: Gamification (z.B. "Deine besten 100 Fotos diesen Monat")

---

### 🔮 Weitere Langzeit-Ideen

- 🌐 **Web-Interface**: Photocleaner im Browser (Supabase Backend)
- 📱 **Mobile Companion App**: iOS/Android Kontrolle & Preview
- 🎬 **Video Import Support**: Full-featured für Videoclips
- 🤖 **Scene Detection**: "Essentials" (Urlaub Highlights) automatisch
- 💾 **Cloud Sync**: Einstellungen & Presets in der Cloud speichern
- 🔐 **Encrypted Export**: Sichere ZIP nach Passwort
- 📌 **Smart Collections**: Dynamische Galerien nach Regeln
- 🎯 **A/B Testing UI**: Verschiedene Ranking-Algorithmen testen

---

## 📈 VERSIONS-HIGHLIGHTS

### v0.8.7 (Aktuell)
- ✨ Live Analysis Log Panel mit per-Bild-Nachrichten
- 🔧 Finalize Hang Fix
- 📊 Detaillierte per-Image Logs mit Emoji-Präfixe

### v0.8.5
- 🎨 Animated Completion Dialog
- 📁 Dated Folder Export (YYYY/MM/DD)
- 🔢 Auto-Padding Counter

### v0.8.0+
- Multilingual Support (6 languages)
- Trial/Licensing System
- Quality Presets
- Batch Operations

---

## 🎯 ROADMAP-HIGHLIGHTS (2026)

- 🔮 Extended AI Models
- 🌐 Web-Interface (Planned)
- 📱 Mobile Companion (Planned)
- 🚀 Performance Optimization Phase 2

---

*Dokumentation aktualisiert: April 2026 | Version 0.8.7*
*Feature-Roadmap erweitert mit Community-Ideen & KI-Vorschlägen*
