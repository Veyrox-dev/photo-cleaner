# PhotoCleaner Go-to-Market-Strategie 2026

**Dokumentversion:** 2.0  
**Datum:** 7. April 2026  
**Status:** Aktive Strategie (FREE/PRO-Modell)

---

## Executive Summary

PhotoCleaner ist eine Windows-Desktop-App fuer intelligente Foto-Bereinigung mit klarem Privacy-First-Fokus. Das aktuelle Vermarktungsmodell ist bewusst einfach:

- **FREE:** Lizenz per E-Mail, einmalig insgesamt 250 Bilder
- **PRO:** jaehrliches Abo, unbegrenzte Analyse, Premium-Features

Die Strategie konzentriert sich auf drei Dinge:

1. moeglichst wenig Reibung bis zur ersten erfolgreichen Analyse,
2. klare Upgrade-Ausloeser beim FREE-Limit,
3. glaubwuerdige Positionierung gegenueber cloudlastigen oder ueberladenen Alternativen.

**Strategisches Ziel:** Ein belastbarer Launch mit nachvollziehbarer FREE→PRO-Conversion und einem wiederholbaren organischen Akquisekanal bis Q3 2026.

---

## Produkt- und Angebotsstruktur

### FREE
- Preis: **0 EUR**
- Aktivierung: E-Mail-Lizenz
- Nutzung: **einmalig insgesamt 250 Bilder** pro Nutzer/Geraetebindung
- Zweck: Produkt ausprobieren, Vertrauen aufbauen, echten Mehrwert zeigen

### PRO
- Preis: **jaehrliches Abo**
- Nutzung: **unbegrenzte Analyse**
- Enthalten:
  - Face Detection
  - Batch-Processing fuer grosse Archive
  - HEIC-Support
  - erweiterte Analyse- und Komfortfunktionen
  - Online-Validierung mit Offline-Grace-Mechanik

### Konsequenz fuer Messaging
- Kein Trial-Tier
- Kein Enterprise-Tier
- Keine komplexe Preis-Tabelle mit Team-Varianten in der Launch-Phase
- Ein klares Upgrade-Narrativ: **FREE zum Verstehen, PRO fuer echten Regelbetrieb**

---

## Zielsegmente

### 1. Fotografen und Power-User
- grosse, unaufgeraeumte Fotoarchive
- wiederkehrende Dubletten durch Burst, Backups, Exporte
- hohe Zahlungsbereitschaft fuer lokale, schnelle, praezise Bereinigung

### 2. Content Creator
- viele Serien mit kleinen Variationen
- Bedarf an schneller visueller Vorauswahl
- hoher Nutzen durch Face Detection und Batch-Workflows

### 3. Datenschutzsensible Privatnutzer
- moechten keine Cloud-Pflicht fuer Fotoanalyse
- reagieren gut auf lokales Processing und transparentes Lizenzmodell

---

## Positionierung

**Kernbotschaft:**  
"PhotoCleaner hilft dir, grosse Fotoarchive lokal, schnell und nachvollziehbar aufzuraeumen, ohne deine Bilddaten in eine Cloud zu schieben."

### Differenzierung
- **Offline-First:** Analyse lokal statt Cloud-Zwang
- **Klare Upgrade-Grenze:** FREE mit echter Nutzung, aber bewusst begrenzt
- **Praxisnutzen statt Feature-Liste:** Duplikate, Qualitaet, Gesichter, schnellere Entscheidung
- **Windows-Fokus:** kein generisches Massenprodukt, sondern ein spezialisiertes Desktop-Tool

---

## Pricing-Hypothese

### FREE
- Das Limit von **250 Bildern insgesamt** ist gross genug fuer einen realen Testlauf.
- Gleichzeitig ist es klein genug, um Power-User nicht dauerhaft im Free-Tier zu halten.

### PRO
- Das Abo muss klar als Produktivmodus erkennbar sein.
- Die Zahlungsbereitschaft entsteht nicht aus "noch ein Feature", sondern aus:
  - unbegrenzter Analyse,
  - Zeitersparnis bei grossen Bibliotheken,
  - weniger manueller Sichtung,
  - robusterem Alltagseinsatz.

### Preis-Kommunikation
- Preis in allen aktiven Kanaelen einheitlich fuehren.
- Keine veralteten Referenzen auf alte Tier-Modelle, Monatslimits oder Enterprise-Angebote.

---

## Launch-Funnel

### 1. Einstieg
- Website oder GitHub-Release erklaert den Nutzen in einem Satz.
- Installer/README fuehren schnell zur ersten Analyse.
- FREE-Lizenz per E-Mail ist einfach genug, um Einstiegshuerden niedrig zu halten.

### 2. Aktivierung
- Nutzer aktiviert FREE.
- Erste Analyse liefert sofort sichtbaren Mehrwert.
- App kommuniziert transparent, wie viel FREE-Kontingent verbleibt.

### 3. Upgrade
- Upgrade-Moment ist nicht abstrakt, sondern konkret:
  - Limit erreicht,
  - Face Detection benoetigt,
  - grosse Bibliothek in einem Durchlauf bearbeiten,
  - HEIC oder Komfortfunktionen gewuenscht.

### 4. Retention
- PRO muss sich im Alltag rechtfertigen durch Zuverlaessigkeit, Geschwindigkeit und geringe Reibung.
- Die wichtigsten Hebel sind Stabilitaet, klare UI und schnelle Builds/Installer.

---

## Vertriebskanaele

### Kurzfristig
- GitHub Releases und Projektseite
- Reddit / Foto-Communities / Windows-Communities
- kurze Demo-Clips mit Vorher-Nachher-Effekt
- direkte Ansprache von Power-Usern und Fotografen im privaten Netzwerk

### Mittelfristig
- Content-Marketing mit konkreten Problemloesungen
- SEO rund um Dubletten, Foto-Auswahl, HEIC, lokales Aufraeumen
- einfache E-Mail-Sequenz fuer FREE-Nutzer mit echtem Produktfokus statt Marketing-Floskeln

---

## Kernmetriken

### Produkt
- Aktivierungen der FREE-Lizenz
- Anteil erfolgreicher Erstanalysen
- Zeit bis zum ersten sichtbaren Ergebnis
- Fehlerquote in Aktivierung und Checkout

### Kommerziell
- FREE→PRO-Conversion
- Anteil der Upgrades nach Limit-Erreichen
- Refund-Rate / fruehe Kuendigungen
- Support-Aufwand pro zahlendem Nutzer

### Operativ
- Build- und Installer-Stabilitaet
- Lizenzserver-Verfuegbarkeit
- Erfolgsquote bei Checkout, Webhook und Lizenzzustellung

---

## Risiken und Gegenmassnahmen

| Risiko | Gegenmassnahme |
|---|---|
| FREE-Limit wirkt zu knapp | In Kommunikation auf realen Testfall fokussieren; falls noetig spaeter anheben, aber nicht vor belastbaren Daten |
| PRO wirkt zu abstrakt | Upgrade-Texte immer an konkrete Vorteile koppeln: unbegrenzt, Face Detection, grosse Archive |
| Aktivierung/Checkout frustriert | Stripe/Supabase-Fluss automatisiert testen und Smoke-Checks beibehalten |
| Produkt wirkt wie "noch ein Dedupe-Tool" | Offline-First, Gesichtsanalyse und Workflow-Geschwindigkeit offensiv zeigen |
| Zu viele GTM-Ideen gleichzeitig | Erst einen funktionierenden Kernkanal aufbauen, dann skalieren |

---

## Prioritaeten fuer die naechsten 90 Tage

1. **Launch-Dokumentation konsistent halten**  
   Keine alten Tier-Modelle oder Preise mehr in aktiven Dokumenten, UI-Texten oder Website-Assets.

2. **Checkout- und Aktivierungsfluss haerten**  
   Stripe-Testmodus, Webhook, Mail-Zustellung und Aktivierung reproduzierbar pruefen.

3. **Upgrade-Messaging in App und Website schaerfen**  
   Nicht generisch "Premium", sondern klar: unbegrenzt, schneller, fuer grosse Archive.

4. **Einen organischen Akquisekanal sauber bespielen**  
   Lieber ein funktionierender Kanal mit Feedback-Loop als viele halb gepflegte Kanaele.

---

## Fazit

Die neue GTM-Logik ist absichtlich einfacher als die alte Planung. Kein Trial, kein Enterprise, kein kompliziertes Seat-Modell. Stattdessen ein klarer Trichter: **FREE mit echter Produkterfahrung, PRO fuer unbegrenzten produktiven Einsatz.**

Wenn Produkt, Aktivierung und Upgrade-Kommunikation sauber ineinandergreifen, ist dieses Modell deutlich leichter zu testen, zu erklaeren und iterativ zu verbessern als die vorherige Mehr-Tier-Struktur.

---

**Dokumentverantwortung:** Development Team  
**Naechste Review:** nach den ersten belastbaren FREE→PRO-Daten  
**Kontakt:** chris@photocleaner.local
