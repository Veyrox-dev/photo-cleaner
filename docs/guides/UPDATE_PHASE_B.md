# Update-Logik Phase B – Spezifikation

**Stand:** 10. April 2026  
**Status:** Spezifiziert, noch nicht implementiert (v1.1-Kandidat)  
**Abhängigkeit:** Phase A (Manifest-Check + Download-Link) muss produktiv sein → ✅ seit 2026-04-10

---

## Ziel

Phase A zeigt dem Nutzer lediglich ein Hinweisdialog mit einem "Download öffnen"-Link.
Phase B fügt einen vollständigen **In-App-Download-Flow** hinzu:

1. App lädt den neuen Installer direkt herunter (kein Browser-Sprung).
2. Optionaler MSI-Start direkt aus der App heraus.
3. Klarer Fortschrittsindikator + Fehlerbehandlung.

---

## UX-Flow (Soll)

```
[Update verfügbar]-Dialog
        │
        ├─ [Jetzt herunterladen]  ──► Download-Fortschritt (Progress-Dialog)
        │                                    │
        │                          ┌─────────┴──────────┐
        │                          │  Download abgeschl.│
        │                          └─────────┬──────────┘
        │                                    │
        │                          [Installer jetzt starten?]
        │                             ├─ [Ja]  → subprocess.Popen(msi_path)
        │                             │          → App zeigt Hinweis "App wird neu gestartet"
        │                             └─ [Nein] → gespeicherter Pfad für späteres manuelles Starten
        │
        └─ [Später]  ──► keine Aktion (nächste Prüfung nach 12h)
```

---

## Manifest-Erweiterung (latest.json)

Für Phase B muss das bestehende Manifest um ein `installer_url`-Feld ergänzt werden:

```json
{
  "latest_version": "1.0.1",
  "download_url": "https://example.com/download",
  "installer_url": "https://example.com/releases/PhotoCleaner-1.0.1.msi",
  "installer_sha256": "abc123...",
  "installer_size_bytes": 45678901,
  "release_notes_url": "https://example.com/changelog",
  "published_at": "2026-05-01T10:00:00Z"
}
```

Neue Felder:
| Feld | Typ | Beschreibung |
|---|---|---|
| `installer_url` | string | Direktlink zum MSI-Installer |
| `installer_sha256` | string | SHA-256-Hash des MSI für Integritätsprüfung |
| `installer_size_bytes` | int | Dateigröße für Fortschrittsanzeige |

---

## Download-Implementierung

### Datei-Ablage
- Zielordner: `%APPDATA%\PhotoCleaner\updates\` (schreibbar, kein temp-Delete durch Windows)
- Dateiname: `PhotoCleaner-{version}.msi`

### Download-Methode
- `urllib.request.urlretrieve` mit Fortschrittscallback → `QProgressDialog`
- Timeout: 60 Sekunden connect, kein Read-Timeout (Datei kann groß sein)
- Download in eigenem `QThread` (nie im UI-Thread)

### Integritätsprüfung
```python
import hashlib, pathlib

def verify_sha256(file_path: pathlib.Path, expected: str) -> bool:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest().lower() == expected.lower()
```

---

## Fehlerbehandlung

| Fehler | Verhalten |
|---|---|
| Netzwerkfehler während Download | Fehlerdialog + "Manuell herunterladen"-Link (Phase A Fallback) |
| SHA-256-Mismatch | Datei löschen, Fehlerdialog: "Datei beschädigt, bitte erneut versuchen" |
| Zu wenig Speicherplatz | Check vor Download: `shutil.disk_usage()` → Fehlerdialog mit Hinweis |
| MSI-Start schlägt fehl | subprocess.Popen mit detach → bei Exception: Fehlerdialog + Explorer-Fenster zum Update-Ordner |
| Download-Ordner nicht schreibbar | Fallback auf %TEMP% |

---

## Rollback

- Es gibt keinen programmatischen Rollback durch die App (WiX MSI-Upgrade mit `MajorUpgrade`-Element stellt sicher, dass die alte Version deinstalliert wird).
- Der heruntergeladene Installer wird **nicht automatisch gelöscht** — er bleibt im Update-Ordner, damit der Nutzer ihn manuell erneut ausführen kann.
- Bei fehlerhafter neuer Version → Nutzer muss alten MSI manuell installieren (Installer nicht im Update-Ordner, aber auf der Website verfügbar).

---

## Sicherheitsaspekte

- Kein Ausführen von Dateien aus nicht-verifizierten Quellen (sha256-Check Pflicht).
- `installer_url` muss HTTPS sein; HTTP-URLs werden abgelehnt.
- `subprocess.Popen([str(msi_path)])` mit absolutem Pfad und explizitem Dateiname — kein Shell=True.
- Kein Übergeben von Nutzer-Input an den Prozess.

---

## Testplan

| Test | Typ | Beschreibung |
|---|---|---|
| Download-Fortschritt wird angezeigt | UI-Test | Mock-URL, simulierte Verzögerung |
| SHA-256-Mismatch wird erkannt | Unit-Test | falsche Hash-Expectation |
| Netzwerktrennung während Download | Unit-Test | Exception im Callback |
| Speicherplatz-Check schlägt fehl | Unit-Test | Mock `disk_usage()` |
| MSI-Pfad ist absolut, kein Shell=True | Code-Review | statische Analyse |

---

## Abhängige Arbeiten

- `modern_window.py`: `_check_for_updates()` um `installer_url` + `installer_sha256` + `installer_size_bytes` erweitern
- Neues Widget: `UpdateDownloadDialog(QProgressDialog)` in eigenem Modul `src/photo_cleaner/ui/update_download_dialog.py`
- `website/updates/latest.json`: `installer_url`, `installer_sha256`, `installer_size_bytes` ergänzen
- CI: SHA-256-Hash nach MSI-Build automatisch generieren und in `latest.json`-Template schreiben

---

## Abgrenzung Phase C

Phase C (MSIX/AppInstaller) würde einen separaten Distributions-Kanal aufbauen, der Windows 10/11
nativ für Delta-Updates nutzt. Phase B ist bewusst MSI-only und ändert nichts am Signing- oder
Packaging-Modell.
