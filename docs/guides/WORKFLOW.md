# Photo Cleaner - Neuer Geführter Workflow

## Übersicht

Der Photo Cleaner wurde komplett überarbeitet mit einem klaren, geführten Workflow:

1. **Start-Dialog**: Ordnerauswahl
2. **Analyse-Phase**: Automatische Verarbeitung mit Fortschrittsanzeige  
3. **Review-Phase**: Manuelle Kontrolle mit automatischen Empfehlungen
4. **Finalisierung**: Export in strukturierte Ordner

---

## Phase 1: Start-Dialog

**Beim Start der Anwendung:**

```bash
python run_ui.py
```

**Dialog-Fenster öffnet sich:**

- **Input-Ordner (Pflicht)**: Ordner mit zu sortierenden Bildern
- **Output-Ordner (Pflicht)**: Zielordner für sortierte Bilder

**Validierung:**
- Input- und Output-Ordner dürfen nicht identisch sein
- Output darf nicht in Input liegen (und umgekehrt)
- Output-Ordner wird automatisch erstellt falls nicht vorhanden

**Buttons:**
- **Abbrechen**: Beendet die Anwendung
- **Starten**: Beginnt mit der Analyse

---

## Phase 2: Analyse mit Fortschrittsanzeige

**Nach Klick auf "Starten":**

Die Pipeline läuft automatisch im Hintergrund:

1. **Indexierung** (10%): Alle Bilder werden eingelesen
2. **Duplikat-Erkennung** (30%): Ähnliche Bilder werden gruppiert
3. **Bildeigenschaften** (50%): Auflösung, Schärfe, Helligkeit
4. **Bildqualität** (70%): Detaillierte Qualitätsanalyse (OpenCV)
5. **Auto-Auswahl** (90%): Beste Bilder werden automatisch markiert
6. **Fertig** (100%): Analyse abgeschlossen

**Features:**
- Fortschrittsbalken mit Prozent
- Statustext zeigt aktuellen Schritt
- "Abbrechen"-Button während Analyse
- UI ist nicht interaktiv (blockiert)
- Automatischer Übergang zur Review-Phase bei Erfolg

**Technische Details:**
- Pipeline läuft in separatem Thread (nicht-blockierend)
- Datenbank: `{output_path}/photo_cleaner_session.db`
- Logging in Console (INFO-Level)

---

## Phase 3: Review-Phase

**Nach erfolgreicher Analyse:**

Das Review-Fenster öffnet sich automatisch.

### Gruppenansicht (links)

- Liste aller Duplikat-Gruppen
- Sortierung: Offene Gruppen zuerst
- Fortschrittsanzeige unten

### Bildvorschau (Mitte)

**Thumbnail-Liste:**
- ⭐ **Stern-Badge**: Automatisch empfohlenes Bild (gelbes Stern-Symbol)
- **Grüner Hintergrund**: Markiert das empfohlene Bild visuell
- Tooltip zeigt "(EMPFOHLEN)" an

**Große Vorschau:**
- Zeigt ausgewähltes Bild in hoher Qualität

**Aktions-Buttons:**
- **Keep (K)**: Als Behalten markieren
  - Setzt dieses Bild als neues empfohlenes Bild
  - Nur KEEP-Bilder werden exportiert
- **Delete (D)**: Als Löschen markieren
- **Unsure (U)**: Als Unsicher markieren
- **Lock (Space)**: Gegen Auto-Markierung schützen
- **Undo (Z)**: Letzte Aktion rückgängig

**Hotkeys:**
- `K` = Keep
- `D` = Delete
- `U` = Unsure
- `Space` = Lock/Unlock
- `Z` = Undo
- `Ctrl+J` / `Ctrl+K` = Gruppe wechseln
- `J` / `L` = Bild wechseln
- `?` = Hilfe-Overlay

### Details-Panel (rechts)

**Info-Tab:**
- Dateiname, Pfad, Größe
- Status (KEEP/DELETE/UNSURE/UNDECIDED)
- Lock-Status
- ⭐ **"EMPFOHLEN (Auto-Auswahl)"** wenn automatisch gewählt

**EXIF-Tab:**
- Kamera, Datum, GPS, etc.

**Aktionen-Tab:**
- Historie der Statusänderungen

### Fortschrittsanzeige (unten)

- **Fortschrittsbalken**: Zeigt % entschiedener Bilder
- **Status-Label**: Anzahl KEEP/DELETE/UNSURE
- **✓ Fertigstellen & Exportieren**: Grüner Button (rechts)

---

## Phase 4: Finalisierung & Export

**Nach Review-Phase:**

Klick auf **"✓ Fertigstellen & Exportieren"**

### Bestätigungsdialog

Zeigt an:
- Anzahl der als KEEP markierten Bilder
- Zielstruktur: `{output_path}/YYYY/MM/DD/`
- Bestätigung erforderlich (Ja/Nein)

### Export-Prozess

**Nur KEEP-Bilder werden exportiert:**
- Status = KEEP → wird kopiert
- Status = DELETE/UNSURE/UNDECIDED → wird ignoriert

**Zielstruktur:**

```
Output/
├── 2026/
│   ├── 01/
│   │   ├── 02/
│   │   │   ├── IMG_1234.heic
│   │   │   └── IMG_1235.heic
│   │   └── 03/
│   │       └── IMG_1236.heic
│   └── 02/
│       └── 05/
│           └── IMG_1237.heic
```

**Datumsermittlung (Priorität):**

1. **EXIF DateTimeOriginal** (Aufnahmedatum)
2. **EXIF DateTime** (Erstellungsdatum)
3. **EXIF DateTimeDigitized** (Digitalisierungsdatum)
4. **Dateisystem mtime** (Fallback)

**Kollisionsvermeidung:**
- Existiert Datei bereits: `IMG_1234_1.heic`, `IMG_1234_2.heic`, ...

**Erfolgsmeldung:**
- ✓ Anzahl erfolgreich exportierter Bilder
- Pfad zum Output-Ordner
- Bei Fehlern: Liste der ersten 5 Fehler

### Nicht ausgewählte Bilder

**Wichtig:**
- Werden **NICHT gelöscht**
- Verbleiben im Input-Ordner unverändert
- Werden **NICHT in Output kopiert**

Optional (manuell):
- Archiv-Ordner für nicht-exportierte Bilder erstellen
- Oder im Input-Ordner belassen für spätere Entscheidung

---

## Verwendung

### Standard-Workflow

```bash
# Start mit Dialog
python run_ui.py
```

1. Dialog öffnet sich
2. Input-Ordner wählen (z.B. `C:\Photos\Unsorted`)
3. Output-Ordner wählen (z.B. `C:\Photos\Sorted`)
4. "Starten" klicken
5. Warten während Analyse läuft (~30 Sekunden - 5 Minuten)
6. Review-Fenster öffnet sich automatisch
7. Gruppen durchgehen, ⭐ empfohlene Bilder prüfen
8. Bei Bedarf manuell anpassen (K/D/U)
9. "Fertigstellen & Exportieren" klicken
10. Fertig! Bilder sind in YYYY/MM/DD Struktur sortiert

### Kommandozeilen-Modus (ohne Dialog)

```bash
# Für Scripting / Automation
python run_ui.py --input C:\Photos\Unsorted --output C:\Photos\Sorted
```

Überspringt Start-Dialog, startet direkt mit Analyse.

---

## Technische Details

### Komponenten

**Neue Dateien:**
- `src/photo_cleaner/start_dialog.py` - Ordnerauswahl-Dialog
- `src/photo_cleaner/ui/analysis_dialog.py` - Analyse mit Fortschritt
- `src/photo_cleaner/exporter.py` - EXIF-basierter Export

**Modifizierte Dateien:**
- `src/photo_cleaner/ui/main_window.py` - Finalisierungs-Button & Export
- `run_ui.py` - Geführter Workflow-Launcher

### Workflow-States

1. **STARTUP** → Start-Dialog
2. **ANALYSIS** → Pipeline läuft (nicht-interaktiv)
3. **REVIEW** → Manuelle Kontrolle (interaktiv)
4. **FINALIZE** → Export & Fertigstellung

### Datenbank

**Temporäre Session-DB:**
- Pfad: `{output_path}/photo_cleaner_session.db`
- Schema Version 4 (mit `is_recommended`, `keeper_source`)
- Wird bei jeder Analyse neu erstellt

**Wichtige Felder:**
- `file_status`: KEEP/DELETE/UNSURE/UNDECIDED
- `is_recommended`: Boolean (Auto-Auswahl)
- `keeper_source`: 'auto' | 'manual' | 'undecided'

### Auto-Auswahl Algorithmus

**Scoring-Formel:**

```
total_score = 
  0.35 * sharpness_score +      # Laplacian variance
  0.25 * lighting_score +        # Exposure balance
  0.20 * resolution_score +      # Megapixels
  0.15 * face_quality_score +    # Eyes open detection
  0.05 * recency_score           # EXIF datetime
```

**Pro Gruppe:**
- Genau 1 Bild wird als empfohlen markiert
- Höchster Score gewinnt
- `is_recommended = 1`, `keeper_source = 'auto'`

**Manuelle Override:**
- Nutzer drückt `K` auf anderem Bild
- Empfehlung wechselt zu diesem Bild
- `keeper_source` ändert sich zu `'manual'`

---

## Fehlerbehandlung

### Analyse-Phase

**Pipeline-Fehler:**
- Fehlermeldung im Dialog
- Log-Ausgabe in Console
- "Schließen"-Button wird angezeigt
- Workflow wird abgebrochen

**Abbruch durch Nutzer:**
- "Abbrechen"-Button während Analyse
- Worker-Thread wird gestoppt
- Workflow wird beendet

### Export-Phase

**Keine KEEP-Bilder:**
- Info-Dialog: "Keine Auswahl"
- Export wird übersprungen

**IO-Fehler:**
- Fehler werden geloggt
- Export läuft weiter für andere Bilder
- Zusammenfassung zeigt Erfolgs-/Fehleranzahl
- Erste 5 Fehlermeldungen werden angezeigt

**Fehlende EXIF-Daten:**
- Fallback auf Dateisystem-Datum (mtime)
- Export läuft normal weiter

---

## Unterschiede zur alten Version

### Alt (Vor Überarbeitung)

- ❌ Kein Start-Dialog (DB-Pfad per Parameter)
- ❌ Keine Fortschrittsanzeige während Pipeline
- ❌ Unklarer Export-Prozess
- ❌ Manuelles File-Management erforderlich
- ❌ Keine klare Trennung der Workflow-Phasen

### Neu (Nach Überarbeitung)

- ✅ **Geführter Workflow**: Start-Dialog → Analyse → Review → Export
- ✅ **Fortschrittsanzeige**: Echtzeit-Fortschritt während Analyse
- ✅ **Automatischer Export**: EXIF-basierte YYYY/MM/DD Struktur
- ✅ **Nur KEEP-Bilder**: Nur explizit ausgewählte Bilder exportiert
- ✅ **Klare Phasen**: 4-Phasen-Workflow mit eindeutigen Übergängen
- ✅ **Automatische Empfehlungen**: ⭐ Stern-Badge für beste Bilder
- ✅ **Robuste Fehlerbehandlung**: Alle Phasen mit Validierung & Logging

---

## Troubleshooting

### Dialog öffnet sich nicht

**Problem:** `run_ui.py` läuft, aber kein Fenster erscheint

**Lösung:**
```bash
# Prüfe ob PySide6 installiert ist
python -c "import PySide6; print('OK')"

# Falls Fehler:
pip install PySide6
```

### Pipeline bleibt bei 10% hängen

**Problem:** Analyse-Dialog zeigt "Indexiere Bilder..." dauerhaft

**Ursachen:**
- Sehr viele Bilder (>10.000)
- Langsame Festplatte / Netzwerklaufwerk
- HEIC-Support fehlt

**Lösung:**
```bash
# Prüfe pillow-heif
python -c "import pillow_heif; print('OK')"

# Falls Fehler:
pip install pillow-heif

# Prüfe Console-Logs:
# Sollte "Indexing..." Progress zeigen
```

### Keine Duplikate gefunden

**Problem:** Review-Fenster zeigt "Keine Gruppen"

**Ursachen:**
- Alle Bilder sind einzigartig (keine Duplikate)
- Hash-Schwellwert zu strikt

**Lösung:**
- Normal wenn keine Duplikate vorhanden
- Review-Fenster zeigt dann Einzelbilder
- Export funktioniert trotzdem

### Export schlägt fehl

**Problem:** "Export fehlgeschlagen" Dialog

**Ursachen:**
- Output-Ordner nicht beschreibbar
- Laufwerk voll
- Netzwerk-Timeout

**Lösung:**
1. Prüfe Schreibrechte auf Output-Ordner
2. Prüfe freien Speicherplatz
3. Bei Netzwerklaufwerk: Lokalen Ordner verwenden

### Empfehlungen fehlen

**Problem:** Keine ⭐ Badges in Review-Phase

**Ursachen:**
- Auto-Auswahl nicht aktiv
- Pipeline-Scoring nicht abgeschlossen

**Lösung:**
1. Sicherstellen, dass die Analyse vollständig durchgelaufen ist
2. Prüfe DB: `SELECT * FROM files WHERE is_recommended = 1`
3. Logs prüfen: sollten Auto-Auswahl ausgeben

---

## Nächste Schritte

- Weitere Dokumentation: `docs/README.md`
- Detaillierte UI-Docs: `docs/MODERN_UI.md`
- Support & Help: Siehe `docs/README.md`
