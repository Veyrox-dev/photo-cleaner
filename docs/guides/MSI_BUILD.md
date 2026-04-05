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

Optional mit expliziter Version und Clean-Output:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_msi.ps1 -Version 0.8.4 -Clean
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

4. Upgrade
   - Neue MSI-Version installieren
   - Pruefen: MajorUpgrade greift, alte Version wird ersetzt

5. Uninstall
   - Deinstallation ueber Windows Apps
   - Pruefen: Startmenue-Shortcut entfernt

6. Log-Hinweis
   - Bei Fehlern Installer- und App-Logs in `results/` oder QA-Protokoll dokumentieren

## Hinweise

- Dieser Track paketiert den bestehenden PyInstaller-Output als MSI.
- Frozen-Build-Smoketests auf mehreren clean Maschinen bleiben als separater P0/P1-Risikopunkt bestehen.