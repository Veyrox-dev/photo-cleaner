# MSI Build Guide (WiX)

Stand: 2026-04-04

## Ziel

Reproduzierbarer MSI-Build fuer den Windows-Distribution-Track auf Basis des vorhandenen `dist/PhotoCleaner`-Outputs.

## Tooling-Entscheidung

- Gewaehlt: WiX Toolset v4 (echtes MSI statt Setup-EXE)
- Begruendung: native MSI-Unterstuetzung fuer Upgrade/Uninstall, besser fuer Enterprise-Trust und standardisierte Deployment-Pfade

## Voraussetzungen

1. Build-Artefakt vorhanden: `dist/PhotoCleaner/PhotoCleaner.exe`
2. WiX CLI installiert:

```powershell
dotnet tool install --global wix
```

3. Optional Upgrade:

```powershell
dotnet tool update --global wix
```

## Reproduzierbarer Build-Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_msi.ps1
```

Cloud-Lizenzparameter werden beim MSI-Build automatisch in den Installer payload geschrieben,
wenn auf dem Build-Rechner folgende Werte vorhanden sind (Umgebungsvariablen oder Root-.env):

- `SUPABASE_PROJECT_URL`
- `SUPABASE_ANON_KEY`

Beispiel (Build-Rechner):

```powershell
$env:SUPABASE_PROJECT_URL = "https://<your-project-ref>.supabase.co"
$env:SUPABASE_ANON_KEY = "<your-anon-key>"
powershell -ExecutionPolicy Bypass -File scripts/build_msi.ps1
```

Hinweis:

- Es wird nur der `ANON_KEY` verwendet (kein Service-Role-Key).
- Endnutzer muessen dadurch keine `cloud.env` manuell anlegen.

Optional mit expliziter Version und Clean-Output:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_msi.ps1 -Version 0.8.6 -Clean
```

Output:

- `releases/msi/PhotoCleaner-<version>-x64.msi`

## Smoke-Test-Protokoll (Clean Windows)

1. Install
   - MSI starten
   - Pruefen: Installation nach `C:\Program Files\PhotoCleaner`
   - Pruefen: Startmenue-Eintrag `PhotoCleaner`

2. App-Start
   - App ueber Startmenue starten
   - Pruefen: Fenster startet ohne Crash

3. Basis-Workflow
   - Mini-Import aus Testdaten
   - Rating starten
   - Pruefen: keine Blocker/Crashs

4. Lizenzfaelle (Slice 4)
   - FREE pruefen: bei >250 Bildern muss ein klarer Limit-/Upgrade-Hinweis erscheinen
   - PRO pruefen: nach Aktivierung ist die gleiche Verarbeitung ohne Bildlimit moeglich
   - Kompatibilitaet pruefen: bestehende Alt-Lizenzdaten mit Enterprise-Herkunft werden als PRO akzeptiert

5. Delete-Safety
   - SAFE pruefen: Delete fuer Nicht-Duplikate bleibt blockiert
   - Gesperrte Dateien pruefen: Batch-Delete ueberspringt gelockte Dateien nachvollziehbar

6. Upgrade
   - Neue MSI-Version installieren
   - Pruefen: MajorUpgrade greift, alte Version wird ersetzt

7. Uninstall
   - Deinstallation ueber Windows Apps
   - Pruefen: Startmenue-Shortcut entfernt

8. Log-Hinweis
   - Bei Fehlern Installer- und App-Logs in `results/` oder QA-Protokoll dokumentieren

## Hinweise

- Dieser Track paketiert den bestehenden PyInstaller-Output als MSI.
- Frozen-Build-Smoketests auf mehreren clean Maschinen bleiben als separater P0/P1-Risikopunkt bestehen.
- Praktische Testunterlagen:
   - `docs/guides/WIN11_TEST_CHECKLIST.md`
   - `feedback/TEST_SESSION_TEMPLATE.md`

## In-App Update-Check (Stage A: nur Hinweis + Link)

Ziel: App prueft nur auf neuere Version und bietet einen Link zur Download-Seite an.
Kein Auto-Download, keine stille Installation.

### 1) Update-Manifest bereitstellen

Lege auf der Website eine JSON-Datei ab, z. B. unter einer nicht verlinkten URL:

- `https://<deine-domain>/updates/latest.json`

Beispielstruktur:

```json
{
   "latest_version": "1.0.1",
   "download_url": "https://<deine-domain>/download.html",
   "release_notes_url": "https://<deine-domain>/changelog.html",
   "published_at": "2026-04-10T08:00:00Z"
}
```

### 2) App auf Manifest-URL zeigen lassen

Variante A (pro User in settings.json):

- `%APPDATA%/PhotoCleaner/settings.json`
- Key: `update_manifest_url`

Beispiel:

```json
{
   "update_manifest_url": "https://<deine-domain>/updates/latest.json"
}
```

Variante B (global per Environment):

```powershell
$env:PHOTOCLEANER_UPDATE_MANIFEST_URL = "https://<deine-domain>/updates/latest.json"
```

### 3) Verhalten in der App

- Beim Start: stiller Check (max. alle 12h)
- Im Menue: "Nach Updates suchen" fuer manuellen Sofort-Check
- Bei neuer Version: Dialog mit Button "Download oeffnen"

Hinweis: Durch eure Active-Device-/Cloud-Lizenz bleibt die Lizenz nach Upgrade erhalten; Nutzer muessen nicht erneut manuell aktivieren.