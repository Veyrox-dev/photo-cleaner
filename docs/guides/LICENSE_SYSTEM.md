# PhotoCleaner License System

## Uebersicht

Das aktuelle Lizenzsystem von PhotoCleaner kombiniert lokale Lizenzverwaltung mit serverseitig signierten Lizenzdaten.

Es deckt vier Anforderungen ab:

- lokale Speicherung und Aktivierung
- Online-Validierung fuer aktive Lizenzen
- Offline-Nutzung ueber signierten Snapshot mit Grace Period
- saubere Feature-Gates fuer FREE und PRO

Die fruehere Dokumentation mit TRIAL- und ENTERPRISE-Tier ist veraltet. Aktiv ist nur noch das Modell **FREE + PRO**.

---

## Lizenzmodell

### FREE
- Standardmodus nach Installation oder ohne gueltige bezahlte Lizenz
- Aktivierung per E-Mail-/Lizenzfluss moeglich
- **einmalig insgesamt 250 Bilder**
- geeignet fuer Test und ersten echten Produktkontakt

### PRO
- jaehrliche bezahlte Lizenz
- **unbegrenzte Analyse**
- Premium-Features fuer produktiven Einsatz

### Kompatibilitaet
- Alte ENTERPRISE-Daten werden aus Kompatibilitaetsgruenden weiterhin akzeptiert, intern aber wie **PRO** behandelt.
- Neue aktive Dokumentation, UI-Texte und Kauf-Fluesse referenzieren nur noch **FREE** und **PRO**.

---

## Feature-Freigaben

| Feature | FREE | PRO |
|---|:-:|:-:|
| Duplikaterkennung | ✅ | ✅ |
| Basis-Qualitaetsanalyse | ✅ | ✅ |
| Face Detection | ❌ | ✅ |
| Batch-Processing fuer grosse Archive | ❌ | ✅ |
| HEIC/HEIF-Support | ❌ | ✅ |
| Erweiterte Analyse-/Komfortfunktionen | ❌ | ✅ |
| Unbegrenzte Bilder | ❌ | ✅ |

Hinweis: Die exakten Flags werden im Code ueber `FeatureFlag` und die jeweilige Lizenzinformation ausgewertet.

---

## Architektur

### Lokale Komponenten
- `license_manager.py` verwaltet den effektiven Lizenzstatus in der App.
- `license_client.py` spricht mit Supabase fuer Austausch, Aktivierung und Free-Quota-Verbrauch.
- `crypto_utils.py` verifiziert Ed25519-Signaturen.

### Serverseitige Komponenten
- `exchange-license-key` liefert serverseitig signierte `license_data`.
- `license-webhook` verarbeitet Stripe-Kaeufe und erzeugt bezahlte Lizenzen.
- `consume_free_images` verwaltet das FREE-Gesamtkontingent in Supabase.

### Wichtige Eigenschaft
Die App akzeptiert Offline-Daten nicht blind. Fuer den Offline-Betrieb muss ein gueltiger signierter Snapshot vorliegen.

---

## Typischer Ablauf

### 1. Aktivierung / Austausch
1. Die App sendet Lizenzdaten und Geraeteinformationen an den Server.
2. Der Server prueft Status, Laufzeit und Geraetebindung.
3. Der Server liefert signierte `license_data` zurueck.
4. Die App verifiziert die Signatur und speichert einen Snapshot fuer Offline-Nutzung.

### 2. FREE-Nutzung
1. Die App oder Pipeline meldet den Bildverbrauch.
2. Der Server reduziert das verbleibende Gesamtkontingent.
3. Bei Erreichen des Limits erscheint ein Upgrade-Hinweis auf PRO.

### 3. PRO-Nutzung
- Keine Bildmengenbegrenzung
- Premium-Features werden lokal freigeschaltet
- Offline-Grace wird ueber den signierten Snapshot abgesichert

---

## API-Beispiele

### LicenseManager nutzen

```python
from photo_cleaner.license import LicenseManager, FeatureFlag

manager = LicenseManager(app_dir)

info = manager.get_license_info()
print(info.license_type)
print(info.max_images)

if manager.is_feature_enabled(FeatureFlag.HEIC_SUPPORT):
    print("HEIC ist verfuegbar")
```

### Bildlimit pruefen

```python
image_count = 400

if not manager.can_process_images(image_count):
    raise ValueError("FREE-Limit erreicht. Upgrade auf PRO erforderlich.")
```

### Lizenzstatus lesen

```python
status = manager.get_license_status()
# Beispiel:
# {
#   "license_type": "free",
#   "max_images": 250,
#   "enabled_features": [...],
#   "days_remaining": null
# }
```

---

## Lokales Lizenzformat

### Speicherort

```text
<app_dir>/photo_cleaner.license
```

### Beispielinhalt

```text
PC-PRO-1769353765-a2a2ee22bd00c337
```

Format:

- `PC` = Prefix
- `TYPE` = `free` oder `pro`
- `TIMESTAMP` = Ausstellungszeitpunkt
- `SIGNATURE` = lokaler Signaturteil fuer das Lizenzformat

Hinweis: Fuer Offline-Vertrauen ist inzwischen der serverseitig signierte Snapshot wichtiger als die alte Beschreibung eines rein lokalen HMAC-Modells.

---

## Sicherheit

### Aktueller Stand
- Serverantworten fuer Lizenzdaten werden mit **Ed25519** signiert.
- Offline-Snapshots werden nur akzeptiert, wenn die Signatur valide ist.
- Ungueltige oder beschaedigte Lizenzdaten fallen sicher auf FREE zurueck.
- Fehlende Online-Verbindung fuehrt bei vorhandenem gueltigem Snapshot nicht sofort zum Funktionsverlust.

### Wichtig
Die Details zur Signaturpruefung und zum Offline-Cache stehen in [LICENSE_SIGNATURES.md](LICENSE_SIGNATURES.md).

---

## UI- und CLI-Integration

### UI
- Lizenzdialog zeigt aktuellen Status und Aktivierungsmoeglichkeiten.
- Upgrade-Texte verweisen nur noch auf **PRO**.

### CLI

```bash
python -m photo_cleaner.license.cli --db db.sqlite show-license
python -m photo_cleaner.license.cli --db db.sqlite save-license PC-PRO-...
python -m photo_cleaner.license.cli --db db.sqlite remove-license
```

---

## Fehlerbehebung

### Problem: Lizenzdatei fehlt
Loesung: Erwartetes Verhalten. Die App laeuft dann im FREE-Modus.

### Problem: Aktivierung oder Austausch schlaegt fehl
Loesung: Internetverbindung, Systemzeit und Serverstatus pruefen; danach erneut versuchen.

### Problem: FREE-Limit erreicht
Loesung: Upgrade auf PRO. Das aktuelle Modell kennt kein Trial- oder Enterprise-Upgrade mehr.

### Problem: Offline funktioniert nicht
Loesung: Pruefen, ob bereits ein gueltiger signierter Snapshot vorhanden ist. Details in [LICENSE_SIGNATURES.md](LICENSE_SIGNATURES.md).

---

## Zusammenfassung

| Aspekt | Details |
|---|---|
| Aktive Typen | FREE, PRO |
| FREE-Limit | 250 Bilder insgesamt |
| PRO-Limit | unbegrenzt |
| Offline-Nutzung | ueber signierten Snapshot |
| Signaturen | Ed25519 fuer Server-Payloads |
| Fallback | ungueltig oder fehlend -> FREE |

Das aktuelle Lizenzsystem ist kein losgeloester Schluesselmechanismus mehr, sondern ein kombinierter Online-/Offline-Fluss mit serverseitigem Vertrauensanker.
