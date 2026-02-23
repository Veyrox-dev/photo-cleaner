# Phase B Quick Start – Supabase Lizenz-Integration

## 1. Test-Lizenzen erstellen (5 Min)

```bash
# Zuerst: Service Role Key herunterladen
# In Supabase: Settings > API > Project API keys > service_role key
# Speichere ihn lokal (nicht committen!)

# Setze die Keys als Umgebungsvariablen (PowerShell):
$env:SUPABASE_PROJECT_URL = "https://uxkbolrinptxyullfowo.supabase.co"
$env:SUPABASE_SERVICE_ROLE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV4a2JvbHJpbnB0eHl1bGxmb3dvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTQ0MjI1OSwiZXhwIjoyMDg1MDE4MjU5fQ.FvLwxEYoa3Npth55nKziaCJD8bZHl8BuW9Msqc6UWAU"

# Erstelle 5 aktive Test-Lizenzen + 1 abgelaufen + 1 gesperrt:
python create_test_licenses.py --count 5 --expired --suspended
```

Output sieht so aus:
```
Creating test licenses in Supabase...

✓ Created: TEST-20260126-001
✓ Created: TEST-20260126-002
...
✓ Created expired license: EXPIRED-20260126-161542
✓ Created suspended license: SUSPENDED-20260126-161542

5 licenses created successfully

Available test license keys:
  - TEST-20260126-001
  - TEST-20260126-002
  - ...
```

## 2. Unit-Tests ausführen (5 Min)

```bash
# Installiere pytest (falls noch nicht done):
pip install pytest pytest-mock

# Führe Tests aus:
pytest tests/test_license_client.py -v
```

Output:
```
test_license_client.py::TestDeviceInfo::test_get_device_id_creates_stable_id PASSED
test_license_client.py::TestDeviceInfo::test_get_device_name_returns_hostname PASSED
...
test_license_client.py::TestLicenseManager::test_activate_with_key_success PASSED

======================== 15 passed in 0.85s ========================
```

## 3. Edge Function Deployment (10 Min)

### 3.1 Supabase CLI installieren

```bash
npm install -g supabase
```

### 3.2 Supabase-Projekt initialisieren

```bash
cd c:\Users\chris\projects\photo-cleaner

# Login
supabase login

# Verbinde mit deinem Projekt
supabase link --project-ref uxkbolrinptxyullfowo
```

### 3.3 Edge Function erstellen

```bash
# Neue Function:
supabase functions new exchange-license-key

# Das erstellt: supabase/functions/exchange-license-key/index.ts
```

### 3.4 Code eingeben

Kopiere den Code aus `docs/supabase_edge_function_example.ts` in `supabase/functions/exchange-license-key/index.ts`.

### 3.5 Lokal testen (Emulator)

```bash
# Starte Emulator:
supabase start

# In neuem Terminal: Teste Function
curl -X POST http://localhost:54321/functions/v1/exchange-license-key \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc191c2VyIjp0cnVlfQ.demo" \
  -H "Content-Type: application/json" \
  -d '{
    "license_key": "TEST-20260126-001",
    "device_info": {
      "deviceId": "test-device-123",
      "name": "TestPC",
      "os": "Windows"
    }
  }'
```

### 3.6 In Production deployen

```bash
supabase functions deploy exchange-license-key

# Verifiziere Deployment:
supabase functions list
```

## 4. Python Client lokal testen (10 Min)

Erstelle `test_license_integration.py`:

```python
from photo_cleaner.license_client import LicenseConfig, LicenseManager
from pathlib import Path
import os

# Config aus .env
config = LicenseConfig(
    project_url=os.getenv("SUPABASE_PROJECT_URL", "https://uxkbolrinptxyullfowo.supabase.co"),
    anon_key=os.getenv("SUPABASE_ANON_KEY", "sb_publishable_ekEUCJkHRCOvNcnMoO_q2w_RrhDWpBl"),
)

manager = LicenseManager(config, cache_dir=Path.home() / ".photocleaner_test")

# Test mit einer deiner Test-Lizenzen:
success, message = manager.activate_with_key("TEST-20260126-001")
print(f"Aktivierung: {message}")

if success:
    print(f"Status: {manager.get_status()}")
else:
    print(f"Fehler: {message}")
```

Führe aus:
```bash
python test_license_integration.py
```

## 5. UI Integration vorbereiten (15 Min)

Erstelle `src/photo_cleaner/ui/license_dialog.py`:

```python
"""Dialog für Lizenz-Aktivierung."""

from PySide6.QtWidgets import (
    QDialog, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox
)

from photo_cleaner.license_client import LicenseManager, LicenseConfig
import os

class LicenseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("PhotoCleaner - Lizenzaktivierung")
        self.setGeometry(200, 200, 400, 150)
        
        config = LicenseConfig(
            project_url=os.getenv("SUPABASE_PROJECT_URL"),
            anon_key=os.getenv("SUPABASE_ANON_KEY"),
        )
        self.manager = LicenseManager(config)
        
        layout = QVBoxLayout()
        
        # Label
        label = QLabel("Geben Sie Ihren Lizenzschlüssel ein:")
        layout.addWidget(label)
        
        # Input
        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("z.B. TEST-20260126-001")
        layout.addWidget(self.license_key_input)
        
        # Button
        btn = QPushButton("Aktivieren")
        btn.clicked.connect(self.activate)
        layout.addWidget(btn)
        
        self.setLayout(layout)
    
    def activate(self):
        key = self.license_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Fehler", "Bitte Lizenzschlüssel eingeben")
            return
        
        success, message = self.manager.activate_with_key(key)
        
        if success:
            QMessageBox.information(self, "Erfolg", message)
            self.accept()
        else:
            QMessageBox.critical(self, "Fehler", message)
```

## 6. Nächste Schritte

- [ ] Service Role Key speichern + Test-Lizenzen erstellen
- [ ] Unit-Tests laufen lassen
- [ ] Edge Function lokal testen
- [ ] Edge Function deployen
- [ ] License Dialog in UI integrieren (moderne_window.py)
- [ ] Status-Badge im Header zeigen
- [ ] Fehlerbehandlung (keine Lizenz → Indexing/Export sperren)
- [ ] E2E-Test: Kompletter Workflow (Schlüssel → Gerät → Export)

## Troubleshooting

**"Invalid license key" bei Authentication:**
- Prüfe: `CREATE_test_licenses.py` hat die Lizenz wirklich erstellt
- Prüfe in Supabase > SQL Editor: `SELECT * FROM licenses;`

**Function gibt 404:**
- Prüfe: `supabase functions list` zeigt `exchange-license-key`
- Prüfe: `supabase start` läuft (für Emulator)

**Device-Limit wurde sofort erreicht:**
- Das ist normal bei Geräte-Wechsel
- Lösung: In Supabase > `active_devices` Tabelle alte Geräte löschen

**Cache ist älter als 7 Tage (Grace ablaufen)?**
- Die `.photocleaner/license_snapshot.json` wird dann nicht mehr akzeptiert
- Lösung: Einmal Online gehen oder Cache löschen
