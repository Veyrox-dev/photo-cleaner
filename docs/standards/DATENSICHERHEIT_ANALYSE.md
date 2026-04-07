# 🔒 PhotoCleaner - Datensicherheit & Privacy Analyse

**Erstellt:** 3. Februar 2026  
**Version:** v0.6.0  
**Status:** ✅ Für Endnutzer-Perspektive optimiert

---

## Zusammenfassung (Executive Summary)

**Kernaussage:** PhotoCleaner ist **bewusst als 100% lokale Anwendung** entwickelt. Alle Bilder bleiben **vollständig offline** auf dem Computer des Nutzers.

### 🎯 Sicherheits-Level: **Sehr Hoch** ⭐⭐⭐⭐⭐

| Kriterium | Status | Bewertung |
|-----------|--------|-----------|
| **Offline-Verarbeitung** | ✅ 100% lokal | Exzellent |
| **Keine Cloud-Uploads** | ✅ Niemals | Exzellent |
| **Datenverschlüsselung** | ⚠️ Filesystem-abhängig | Gut |
| **Netzwerkzugriff** | ⚠️ Nur Lizenz-Check | Akzeptabel |
| **Temp-Dateien** | ✅ Lokal, keine Leaks | Sehr gut |
| **Code-Sicherheit** | ✅ PyInstaller kompiliert | Gut |
| **Logging-Sicherheit** | ⚠️ Dateipfade in Logs | Verbesserbar |

---

## 1. Aktuelle Sicherheitsarchitektur

### 1.1 Datenverarbeitung: 100% Offline ✅

**Alle Bildanalysen passieren lokal:**

```
Benutzer-PC
├── Bilder-Ordner (Input) 
│   └── Fotos bleiben IMMER hier, werden nicht kopiert
├── SQLite-Datenbank (Lokal)
│   ├── Nur Metadaten (Pfade, Scores, Hashes)
│   └── KEINE Bildpixel, nur Analyse-Ergebnisse
└── Cache-Ordner (.cache/thumbnails)
    └── Kleine Vorschaubilder für schnellere UI

KEINE Verbindung zu PhotoCleaner-Servern!
```

**Genutzte Technologien (Alle offline):**
- **MediaPipe**: Gesichtserkennung (lokal trainierte Modelle)
- **OpenCV**: Bildverarbeitung (lokale Algorithmen)
- **TensorFlow/MTCNN**: Face Detection (lokale Modelle)
- **ImageHash**: Duplikaterkennung (lokaler Vergleich)

**✅ Vorteil:** Selbst bei Internetausfall funktioniert alles!

---

### 1.2 Netzwerkzugriffe: Nur Lizenzsystem ⚠️

**Einziger Netzwerkverkehr:**

| Zeitpunkt | Ziel | Daten | Zweck |
|-----------|------|-------|-------|
| **Lizenz-Aktivierung** | Supabase Cloud | Lizenz-Key + Geräte-ID | Lizenz validieren |
| **App-Start (Optional)** | Supabase Cloud | Lizenz-ID (kein Bildinhalt!) | Gültigkeit prüfen |

**Gesendete Daten (Beispiel):**
```json
{
  "license_key": "PC-PRO-ABC123...",
  "device_info": {
    "device_id": "a3f8d92...",     // Anonyme UUID
    "device_name": "CHRIS-PC",       // Hostname
    "os": "Windows 11"
  }
}
```

**❌ Niemals gesendet:**
- Bildpixel oder Thumbnails
- Dateipfade oder Ordnerstrukturen
- EXIF-Metadaten (GPS, Kamera-Modell, etc.)
- Analyseergebnisse oder Scores

**Offline-Modus:**
- Grace Period: 7 Tage ohne Internet nutzbar
- Gecachte Lizenz bleibt gültig
- Keine Funktionseinschränkung

**📍 Lizenz-Server Location:** EU (Supabase Frankfurt/Irland)

---

### 1.3 Lokale Datenspeicherung

**Alle Daten bleiben auf dem PC des Nutzers:**

#### Windows (Standard):
```
C:\Users\[Username]\AppData\Roaming\PhotoCleaner\
├── db\                          # Datenbanken
│   └── photo_cleaner.db         # SQLite (Metadaten)
├── cache\                       # Thumbnails
│   └── thumbnails\
│       └── [hash].png           # 200x200px Vorschaubilder
├── settings.json                # Benutzer-Einstellungen
├── license_snapshot.json        # Gecachte Lizenz
└── .device_salt                 # Geräte-ID (UUID)
```

#### macOS:
```
~/Library/Application Support/PhotoCleaner/
```

#### Linux:
```
~/.local/share/PhotoCleaner/
```

**Datenbankinhalt (SQLite):**
- Dateipfade (z.B. `C:\Users\Chris\Pictures\vacation.jpg`)
- Perceptual Hashes (für Duplikaterkennung)
- Quality Scores (0-100)
- Timestamps, Gesichtszahl, Schärfewerte
- **KEINE Bilder**, nur Zahlen und Text!

**Thumbnail-Cache:**
- Kleine Vorschaubilder (200x200px)
- Schnellere UI-Performance
- Kann jederzeit gelöscht werden (regeneriert automatisch)

**⚠️ Privacy-Hinweis:** 
Wer Zugriff auf `AppData\Roaming\PhotoCleaner\` hat, kann:
- Sehen, welche Ordner gescannt wurden
- Quality Scores einsehen
- Thumbnails anschauen (niedrige Auflösung)
- **NICHT:** Originale Bilder sehen (außer Ordner-Zugriff)

---

### 1.4 Temporäre Dateien

**Keine kritischen Temp-Dateien:**
- Keine Uploads in %TEMP%
- Keine entpackten Bilder
- Kein RAM-Dumping sensibler Daten

**Bei PyInstaller (OneDIR-Modus):**
```
dist\PhotoCleaner\
├── PhotoCleaner.exe          # Hauptprogramm
├── *.dll                     # System-Bibliotheken
└── _internal\                # Python-Runtime + Libraries
    └── Keine User-Daten gespeichert!
```

---

## 2. Threat Model (Was könnte schiefgehen?)

### ❌ Bedrohung 1: Malware liest PhotoCleaner-Datenbank

**Szenario:** Virus auf dem PC liest `photo_cleaner.db`

**Risiko:** Mittel
- Angreifer sieht Ordnerstrukturen (z.B. `C:\Users\Chris\Urlaub2025\`)
- Angreifer sieht Quality Scores
- **Angreifer hat KEINEN Zugriff auf Bilder** (außer er hat bereits Dateisystem-Zugriff)

**Gegenmaßnahme:**
- Antivirus auf dem PC des Nutzers
- Windows Defender (Standard) reicht meistens

---

### ❌ Bedrohung 2: Man-in-the-Middle bei Lizenz-Aktivierung

**Szenario:** Angreifer im WLAN fängt Lizenz-Traffic ab

**Risiko:** Niedrig
- Lizenz-Key könnte abgefangen werden
- **KEINE Bilddaten** im Traffic (siehe 1.2)
- Supabase nutzt HTTPS (verschlüsselt)

**Gegenmaßnahme:**
- Certificate Pinning (zukünftig)
- Nutzer sollte bei Aktivierung sicheres WLAN nutzen

---

### ❌ Bedrohung 3: Jemand findet PhotoCleaner-Ordner

**Szenario:** Gemeinsam genutzter PC, anderer Nutzer findet AppData-Ordner

**Risiko:** Niedrig-Mittel
- Thumbnails (200x200px) könnten gesehen werden
- Dateipfade zeigen Ordnerstruktur
- **Originale Bilder sicher**, wenn Ordner getrennt

**Gegenmaßnahme:**
- Windows-Benutzerkonto mit Passwort
- AppData-Ordner ist standardmäßig versteckt

---

### ❌ Bedrohung 4: PhotoCleaner wird gehackt (Supply Chain Attack)

**Szenario:** Angreifer manipuliert PhotoCleaner.exe und verteilt Fake-Version

**Risiko:** Hoch (wenn es passiert)
- Nutzer lädt gefälschte Version herunter
- Malware könnte Bilder stehlen

**Gegenmaßnahme:**
- ✅ **Code Signing** (für v1.0.0 geplant, kostet ~200€/Jahr)
- ✅ **Checksum-Verifikation** (SHA256 auf Website)
- ✅ **Download nur von photocleaner.de** (offizielle Website)

---

## 3. Sicherheitsverbesserungen (Roadmap)

### 🔵 Phase 1: Sofort umsetzbar (März 2026)

#### 1.1 Datenbank-Verschlüsselung (Optional)

**Problem:** SQLite-Datenbank liegt unverschlüsselt auf Disk

**Lösung:** SQLCipher-Integration

```python
# Vor (Aktuell):
conn = sqlite3.connect("photo_cleaner.db")

# Nach (Optional):
import sqlcipher
conn = sqlcipher.connect("photo_cleaner.db")
conn.execute("PRAGMA key = 'user_passwort'")
```

**Vorteile:**
- ✅ Datenbank nur mit Passwort lesbar
- ✅ Schützt gegen Malware-Scans
- ✅ Compliance für DSGVO-sensible Umgebungen

**Nachteile:**
- ❌ Zusätzliche Dependency (~2 MB)
- ❌ Nutzer muss Passwort eingeben (UX-Impact)
- ❌ Passwort vergessen = Daten verloren

**Empfehlung:** Als **opt-in Feature** fuer PRO oder fuer spaetere Business-/Team-Pakete

---

#### 1.2 Log-Sanitization

**Problem:** Logs enthalten Dateipfade

```python
# Aktuell:
logger.info(f"Analyzing: C:/Users/Chris/Private/Family/photo.jpg")

# Besser:
logger.info(f"Analyzing: [REDACTED]/photo.jpg")
```

**Umsetzung:** Logging-Filter für sensible Pfade

```python
class PrivacyFilter(logging.Filter):
    def filter(self, record):
        # Ersetze Benutzernamen in Pfaden
        record.msg = re.sub(r'C:/Users/[^/]+/', 'C:/Users/[USER]/', record.msg)
        return True

logger.addFilter(PrivacyFilter())
```

**Aufwand:** 2-3 Stunden  
**Priorität:** Mittel (nicht kritisch, aber nice-to-have)

---

#### 1.3 Secure Thumbnail Cache

**Problem:** Thumbnails könnten gelesen werden

**Lösung:** Verschlüsselte Thumbnails mit AES

```python
from cryptography.fernet import Fernet

def save_thumbnail(image, path, key):
    # Thumbnail als bytes
    buffer = io.BytesIO()
    image.save(buffer, format='PNG')
    encrypted = Fernet(key).encrypt(buffer.getvalue())
    path.write_bytes(encrypted)
```

**Aufwand:** 4-6 Stunden  
**Priorität:** Niedrig (Thumbnails sind ohnehin niedrige Auflösung)

---

### 🟢 Phase 2: Mittelfristig (Juni 2026)

#### 2.1 Code Signing Zertifikat

**Problem:** Windows SmartScreen blockiert exe ohne Signatur

**Lösung:** EV Code Signing Zertifikat kaufen

**Anbieter:**
- Sectigo: ~200€/Jahr
- DigiCert: ~300€/Jahr
- Komodo: ~150€/Jahr

**Vorteil:**
- ✅ Keine SmartScreen-Warnung
- ✅ Verifizierter Publisher ("Chris [Nachname]")
- ✅ Verhindert Tamper-Detection

**Prozess:**
1. Zertifikat kaufen (Ausweis/Gewerbe nötig)
2. SignTool.exe nutzen
3. Jede .exe signieren vor Release

---

#### 2.2 Certificate Pinning für Lizenz-Server

**Problem:** HTTPS schützt, aber gefälschtes Zertifikat möglich

**Lösung:** Hart-codierter Server-Fingerprint

```python
import ssl
import hashlib

SUPABASE_CERT_SHA256 = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"

def verify_certificate(cert):
    fingerprint = hashlib.sha256(cert).hexdigest()
    if fingerprint != SUPABASE_CERT_SHA256:
        raise SecurityError("Invalid certificate!")
```

**Aufwand:** 3-4 Stunden  
**Priorität:** Mittel (für v1.0.0)

---

#### 2.3 Privacy-First Mode (Ultra-Paranoid)

**Feature:** Kompletter Offline-Modus

- ❌ Keine Lizenz-Checks (nur lokale Validierung)
- ❌ Keine Analytics/Telemetrie
- ✅ Datenbank-Verschlüsselung mandatory
- ✅ Thumbnails verschlüsselt
- ✅ Alle Logs deaktiviert

**Zielgruppe:** 
- Journalisten
- Juristen (Mandanten-Fotos)
- Behörden (DSGVO-Compliance)

**Preis:** spaeteres Add-on oder Business-Paket, nicht Teil des aktuellen Launch-Modells

---

### 🔴 Phase 3: Langfristig (Oktober 2026+)

#### 3.1 Security Audit (Extern)

**Kosten:** 3.000-5.000€  
**Nutzen:** Professionelle Penetration Tests

**Anbieter:**
- cure53.de (Deutscher Sicherheits-Audit)
- HackerOne Bug Bounty

---

#### 3.2 DSGVO-Zertifizierung

**Fuer spaetere Business-Kunden wichtig:**
- Privacy Impact Assessment (PIA)
- Data Processing Agreement (DPA)
- ISO 27001 Compliance

**Kosten:** 10.000-15.000€  
**Zeitaufwand:** 3-6 Monate

---

## 4. Nutzer-Empfehlungen (Best Practices)

### Für Privatnutzer (FREE/PRO)

✅ **DO:**
- Windows mit Passwort schützen
- Antivirus aktiv halten (Defender reicht)
- PhotoCleaner von offizieller Website laden
- Regelmäßige Windows Updates

❌ **DON'T:**
- PhotoCleaner auf öffentlichen/gemeinsamen PCs nutzen
- Über Tor/VPN aktivieren (Lizenz-Check könnte fehlschlagen)
- PhotoCleaner aus Foren/Filehostern laden (Fake-Versionen!)

---

### Fuer Firmenumgebungen

✅ **DO:**
- Separate Benutzerkonten pro Mitarbeiter
- Firmen-Lizenz mit Multi-Device-Management
- Netzwerk-Firewall: Nur Supabase-Domains erlauben
- BitLocker für Festplattenverschlüsselung

❌ **DON'T:**
- Gemeinsame Lizenz auf Server (Lizenz = pro Device)
- Cloud-Sync für PhotoCleaner-DB (Dropbox/OneDrive)

---

## 5. Vergleich mit Konkurrenz

### PhotoCleaner vs. Google Photos

| Kriterium | PhotoCleaner | Google Photos |
|-----------|--------------|---------------|
| **Daten-Location** | ✅ Lokal (PC) | ❌ Cloud (Google Server) |
| **Privacy** | ⭐⭐⭐⭐⭐ | ⭐⭐ (Google scannt Bilder) |
| **Offline-Nutzung** | ✅ 100% | ❌ Nur mit Sync |
| **DSGVO-Konform** | ✅ Ja | ⚠️ Komplex (USA) |

---

### PhotoCleaner vs. Apple Photos

| Kriterium | PhotoCleaner | Apple Photos |
|-----------|--------------|---------------|
| **Daten-Location** | ✅ Lokal | ⚠️ iCloud (optional) |
| **Privacy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ (E2E wenn ohne iCloud) |
| **Plattform** | Windows/Mac/Linux | ❌ Nur Mac/iOS |

---

### PhotoCleaner vs. Adobe Lightroom

| Kriterium | PhotoCleaner | Lightroom |
|-----------|--------------|-----------|
| **Daten-Location** | ✅ Lokal | ⚠️ Creative Cloud Sync |
| **Privacy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ (Adobe Analytics) |
| **Preis** | 29€ einmalig | 12€/Monat (144€/Jahr) |

**✅ PhotoCleaner Alleinstellungsmerkmal:** Absolute Privacy + Offline-First

---

## 6. Technische Details (für Entwickler)

### 6.1 Verwendete Kryptographie

```python
# Lizenz-Validierung (HMAC-SHA256)
signature = hmac.new(
    SECRET_KEY.encode('utf-8'),
    f"{license_id}|{device_id}|{timestamp}".encode('utf-8'),
    hashlib.sha256
).digest()

# Perceptual Hashing (Duplikaterkennung)
image_hash = imagehash.phash(image, hash_size=8)  # 64-bit hash

# Thumbnail-Cache (SHA1 für Dateinamen)
cache_key = hashlib.sha1(f"{path}|{mtime}|{size}".encode()).hexdigest()
```

**Verwendete Algorithmen:**
- **HMAC-SHA256:** Lizenz-Signatur (kryptographisch sicher)
- **SHA1:** Cache-Keys (nicht sicherheitskritisch, nur Deduplizierung)
- **pHash:** Bildvergleich (perceptual, nicht kryptographisch)

---

### 6.2 Netzwerk-Endpoints

**Alle HTTPS-verschlüsselt:**

```
POST https://[project].supabase.co/functions/v1/exchange-license-key
  → Aktivierung (einmalig)

GET https://[project].supabase.co/rest/v1/licenses?license_id=eq.[ID]
  → Validierung (bei App-Start, optional)

POST https://[project].supabase.co/rest/v1/active_devices
  → Geräte-Registrierung
```

**Header:**
```http
Authorization: Bearer [ANON_KEY]
Content-Type: application/json
```

**❌ Keine Analytics/Telemetrie:**
- Kein Google Analytics
- Kein Sentry Error Tracking
- Kein Mixpanel/Amplitude

---

### 6.3 Dependency Security

**Kritische Dependencies:**
- **Pillow:** Image Processing (CVE-Historie vorhanden)
- **OpenCV:** C++ Bindings (Buffer Overflow-Risiken)
- **NumPy:** Numerics (sehr stabil)

**Mitigation:**
- ✅ Requirements.txt mit gepinnten Versionen
- ✅ Dependabot Security Alerts (GitHub)
- ⏳ Monatliche Dependency-Updates (ab Phase 2)

---

## 7. FAQ - Häufige Nutzerfragen

### "Kann PhotoCleaner meine Bilder ins Internet hochladen?"

**❌ NEIN.** PhotoCleaner hat **keinen Code** für Bild-Uploads. Die einzige Netzwerkverbindung ist die Lizenz-Aktivierung (siehe Abschnitt 1.2).

**Beweis:** Open-Source-Code kann auditiert werden (ab v1.0.0 veröffentlichen wir Teile).

---

### "Was passiert, wenn PhotoCleaner gehackt wird?"

Deine **Bilder bleiben sicher**, weil:
1. PhotoCleaner lädt keine Bilder hoch
2. Ein gehackter Lizenz-Server hat keinen Zugriff auf deinen PC
3. PhotoCleaner kann auch offline genutzt werden (Grace Period)

**Worst Case:** Lizenz-Key wird gestohlen → Wir ersetzen ihn kostenlos.

---

### "Muss ich PhotoCleaner vertrauen?"

**Vertrauen reduzieren durch:**
- ✅ Firewall: Blockiere alle Verbindungen außer zu `*.supabase.co`
- ✅ Offline-Modus: Aktiviere Lizenz einmalig, dann Netzwerk trennen
- ✅ Code-Audit: Ab v1.0.0 Teile des Codes Open Source

**Vergleich:**
- Google Photos verlangt **100% Vertrauen** (Closed Source + Cloud)
- PhotoCleaner verlangt **5% Vertrauen** (nur Lizenzsystem)

---

### "Was ist mit DSGVO?"

✅ **PhotoCleaner ist DSGVO-konform:**

| Anforderung | Status |
|-------------|--------|
| **Art. 5 - Datenminimierung** | ✅ Nur nötige Daten (Pfade, Scores) |
| **Art. 6 - Rechtsgrundlage** | ✅ Vertragserfüllung (Lizenz) |
| **Art. 17 - Recht auf Löschung** | ✅ User kann DB löschen |
| **Art. 25 - Privacy by Design** | ✅ Offline-First-Architektur |
| **Art. 32 - Sicherheit** | ✅ Verschlüsselung (HTTPS) |

**Data Processing Location:** EU (Supabase Frankfurt)

---

### "Was sieht PhotoCleaner über mich?"

**Bei Lizenz-Aktivierung:**
- Lizenz-Key (z.B. `PC-PRO-ABC123...`)
- Geräte-ID (anonyme UUID, z.B. `a3f8d92...`)
- Hostname (z.B. `CHRIS-PC`)
- Betriebssystem (z.B. `Windows 11`)

**Nie gesammelt:**
- ❌ Bildinhalte
- ❌ Dateipfade
- ❌ GPS-Koordinaten
- ❌ Namen/Gesichter in Bildern
- ❌ Nutzungsstatistiken

---

## 8. Roadmap für Sicherheit

### März 2026 (v0.7.0)
- [ ] Log-Sanitization (Pfade anonymisieren)
- [ ] Security.md im Projekt veröffentlichen
- [ ] Checksum (SHA256) für Downloads

### Juni 2026 (v0.8.2)
- [ ] Code Signing Zertifikat kaufen + anwenden
- [ ] Certificate Pinning für Lizenz-Server
- [ ] Opt-in Datenbank-Verschlüsselung (SQLCipher)

### Oktober 2026 (v1.0.0)
- [ ] Privacy-First Mode (separates Business-Add-on, falls spaeter noetig)
- [ ] Externe Security Audit (cure53)
- [ ] Bug Bounty Programm (HackerOne)

### 2027 (v1.1.0+)
- [ ] ISO 27001 Zertifizierung (fuer spaetere Business-Anforderungen)
- [ ] Data Processing Agreement (DPA) für Firmen
- [ ] E2E-verschlüsselte Backups (optional)

---

## 9. Kontakt & Responsible Disclosure

### Sicherheitslücke gefunden?

**Bitte NICHT öffentlich melden!**

**Kontakt:**
- Email: security@photocleaner.de (ab Oktober 2026)
- PGP-Key: [wird veröffentlicht]

**Response Time:**
- Kritisch (RCE, Data Leak): 24 Stunden
- Hoch (Privilege Escalation): 72 Stunden
- Mittel (DoS, Info Leak): 1 Woche

**Belohnung:**
- Hall of Fame auf Website
- Kostenlose PRO-Lizenz (1 Jahr) oder spaeterer Business-Zugang
- Bug Bounty: 50-500€ (ab v1.0.0)

---

## 10. Fazit

### ✅ PhotoCleaner ist sicher für:
- ✅ **Privatnutzer** mit Familienfotos
- ✅ **Hobby-Fotografen** mit 10k+ Bildern
- ✅ **Freelancer** (Kunden-Shootings)
- ⚠️ **Kleine Unternehmen** (mit Einschränkungen)

### ⚠️ Aktuell NICHT geeignet für:
- ❌ Hochsicherheits-Umgebungen (Militär, Geheimdienste)
- ❌ Medical Imaging (HIPAA-Compliance fehlt)
- ❌ Forensik (keine Chain-of-Custody)

**Diese Features kommen spaeter als optionale Business-/Compliance-Erweiterungen**

---

## Änderungshistorie

| Datum | Version | Änderung |
|-------|---------|----------|
| 2026-02-03 | 1.0 | Initiale Analyse für v0.6.0 |

---

**Dokument erstellt von:** GitHub Copilot (Claude Sonnet 4.5)  
**Geprüft durch:** Chris [Nachname]  
**Nächste Review:** März 2026 (vor Phase 2)
