# PhotoCleaner Beta Feedback System

**Version:** 0.8.3  
**Erstellt:** 5. Februar 2026  
**Zweck:** Systematisches Sammeln von User Feedback für Algorithm Improvements

---

## 📋 ÜBERSICHT

Drei verschiedene Optionen zum Sammeln von Beta-Feedback:

1. **HTML-Formular** (Lokal, keine externe Abhängigkeit)
2. **Microsoft Forms** (Cloud, einfach für User)
3. **Google Forms** (Cloud, Alternative)

---

## 🎯 OPTION 1: HTML FORMULAR (Empfohlen für Beta)

### Vorteile
- ✅ Keine externen Services nötig
- ✅ Vollständige Kontrolle über Daten
- ✅ Export als JSON für einfache Analyse
- ✅ Funktioniert offline
- ✅ Kein Tracking, kein Google/Microsoft Account nötig

### Setup

1. **Formular verteilen:**
   ```bash
   # HTML-Datei an Beta-Tester senden
   feedback_form.html
   ```

2. **User öffnet Datei im Browser:**
   - Doppelklick auf `feedback_form.html`
   - Formular ausfüllen
   - "Feedback absenden" → JSON-Datei wird heruntergeladen

3. **JSON-Dateien sammeln:**
   - Beta-Tester schickt JSON-Datei per Email zurück
   - Du sammelst alle in `feedback_results/`

4. **Feedback analysieren:**
   ```bash
   python scripts/analyze_feedback.py feedback_results/
   ```

### Beispiel-Workflow

```
Beta-Tester:
1. Erhält feedback_form.html per Email
2. Öffnet in Browser
3. Füllt aus (5-10 Min)
4. Download feedback_[email]_[timestamp].json
5. Schickt JSON per Email zurück

Du:
1. Sammelst alle JSON-Dateien in feedback_results/
2. Lässt analyze_feedback.py laufen
3. Erhältst detaillierte Statistiken
```

---

## 🎯 OPTION 2: MICROSOFT FORMS

### Vorteile
- ✅ Professionell & einfach für User
- ✅ Automatische Sammlung
- ✅ Excel-Export mit Statistiken
- ✅ Kein Email hin- und herschicken

### Setup

1. **Gehe zu:** https://forms.office.com

2. **Erstelle neues Formular:**
   - "Neues Formular"
   - Titel: "PhotoCleaner v0.8.2 Beta Feedback"

3. **Fragen übernehmen aus:**
   - `docs/FEEDBACK_QUESTIONS.md` (alle Fragen strukturiert)

4. **Formular-Link teilen:**
   - Link kopieren
   - An Beta-Tester per Email senden

5. **Antworten exportieren:**
   - "Antworten" → "In Excel öffnen"
   - Daten manuell analysieren ODER:
   - CSV exportieren → analyze_feedback.py anpassen

### Microsoft Forms Struktur

**Sections:**
1. Allgemeine Informationen (Email, Bildanzahl, Bildtypen)
2. Auto-Select Genauigkeit (⭐ Hauptfokus!)
3. Neue Features (Eye Quality, Sharpness, Lighting)
4. Performance (Speed, Crashes)
5. User Experience (Likes, Dislikes, NPS)
6. Bugs & Issues
7. Kaufbereitschaft (€59/Jahr)
8. Gesamtbewertung

**Fragetypen:**
- Multiple Choice (Radio Buttons)
- Checkboxen (Mehrfachauswahl)
- Bewertungsskalen (1-5, 1-10)
- Textfelder (Freitext)
- Zahlen-Eingabe (Accuracy %)

---

## 🎯 OPTION 3: GOOGLE FORMS

### Vorteile
- ✅ Kostenlos & weit verbreitet
- ✅ Automatische Google Sheets Integration
- ✅ Einfach zu teilen

### Setup

1. **Gehe zu:** https://forms.google.com

2. **Erstelle neues Formular:**
   - "Blank Form"
   - Titel: "PhotoCleaner v0.8.2 Beta Feedback"

3. **Fragen übernehmen aus:**
   - `docs/FEEDBACK_QUESTIONS.md`

4. **Link teilen:**
   - "Send" → Link kopieren
   - An Beta-Tester senden

5. **Antworten exportieren:**
   - "Responses" → Google Sheets Icon
   - Download als CSV
   - analyze_feedback.py anpassen

---

## 📊 FEEDBACK ANALYSE

### Automatisierte Analyse

```bash
# Alle JSON-Dateien analysieren
python scripts/analyze_feedback.py feedback_results/

# Ausgabe:
# ✅ Rating Analysis (Trust, Eye Quality, NPS, etc.)
# ✅ Auto-Select Accuracy (Durchschnitt, Distribution)
# ✅ Image Types Tested
# ✅ Performance Feedback
# ✅ Qualitative Text Feedback
# ✅ Purchase Intent
# ✅ Net Promoter Score (NPS)
# ✅ Executive Summary mit Recommendations
```

### Key Metrics

**Auto-Select Genauigkeit:**
- Ziel: >85% Accuracy
- Minimum: >70% für v1.0

**Trust Level:**
- Ziel: >4.0/5
- Minimum: >3.5/5

**Net Promoter Score (NPS):**
- Excellent: >50
- Good: 30-50
- Needs Work: 10-30
- Critical: <10

**Overall Rating:**
- Ziel: >4.5/5
- Minimum: >4.0/5

---

## 🎯 BETA TESTING WORKFLOW

### Phase 1: Vorbereitung (Feb 5)

1. ✅ Feedback-System erstellt
2. 🔵 Beta-Tester rekrutieren (10-20 Personen)
   - Familie & Freunde
   - Power-User aus Social Media
3. 🔵 Testing-Anleitung schreiben
4. 🔵 PhotoCleaner v0.8.2 Build verteilen

### Phase 2: Testing (Feb 6-15)

1. Beta-Tester erhalten:
   - PhotoCleaner_v0.8.2.exe
   - feedback_form.html (oder Microsoft Forms Link)
   - Testing-Anleitung

2. Tester führen durch:
   - Minimum 100 Bilder
   - Verschiedene Bildtypen
   - Auto-Select ausprobieren
   - Bugs dokumentieren

3. Feedback-Deadline: 15. Februar 2026

### Phase 3: Auswertung (Feb 16-20)

1. Alle Feedbacks sammeln
2. `analyze_feedback.py` ausführen
3. Patterns identifizieren:
   - Wo funktioniert Auto-Select gut?
   - Wo versagt es?
   - Welche Bugs sind kritisch?
4. Priorities setzen für Fixes

### Phase 4: Iteration (Feb 21-28)

1. Critical Bugs fixen
2. Algorithm adjustments (falls Accuracy <70%)
3. v0.8.2 oder v0.8.2 Release
4. Optional: 2. Beta-Runde

---

## 📧 BETA-TESTER EMAIL TEMPLATE

```
Betreff: PhotoCleaner v0.8.2 Beta - Feedback gesucht!

Hallo [Name],

ich arbeite gerade an PhotoCleaner v0.8.2 und brauche dein Feedback! 🎉

**Was ist PhotoCleaner?**
Ein Tool zum Sortieren & Auswählen deiner besten Fotos - automatisch!

**Was ist neu in v0.8.2?**
- Verbesserte Gesichtserkennung (Augen offen/geschlossen)
- Intelligentere Auto-Select Algorithmus
- Bessere Schärfe- und Belichtungserkennung

**Was brauche ich von dir?**
1. Lade PhotoCleaner_v0.8.2.exe herunter
2. Teste es mit mindestens 100 deiner Fotos
3. Fülle das Feedback-Formular aus (5-10 Min)

**Download:**
- PhotoCleaner: [Link zu .exe]
- Feedback-Formular: [Link zu HTML oder Microsoft Forms]

**Deadline:** 15. Februar 2026

**Wichtig:**
- Teste verschiedene Bildtypen (Portraits, Landschaften, etc.)
- Sag ehrlich, wo Auto-Select falsch liegt
- Jeder Bug hilft mir, es besser zu machen!

Vielen Dank! 🙏

Chris
```

---

## 🐛 HÄUFIGE FRAGEN

### Q: Wie viele Beta-Tester brauche ich?
**A:** 10-20 ist ideal. Weniger = nicht repräsentativ, mehr = schwer zu managen.

### Q: Was wenn niemand mitmacht?
**A:** 
- Incentive anbieten (z.B. PRO License kostenlos)
- Social Media posten
- Familie & Freunde direkt ansprechen

### Q: HTML vs. Microsoft Forms?
**A:**
- HTML: Mehr Kontrolle, offline, keine Accounts
- Microsoft Forms: Einfacher für User, automatische Sammlung

### Q: Wie lange sollte Testing dauern?
**A:** 1-2 Wochen ist realistisch. Länger = User verlieren Interesse.

### Q: Was wenn Feedback negativ ist?
**A:** PERFEKT! Negatives Feedback ist wertvoller als positives. Es zeigt, wo du verbessern musst.

---

## ✅ NEXT STEPS

1. **Jetzt:**
   - ✅ Feedback-System erstellt
   - 🔵 Entscheide: HTML oder Microsoft Forms?

2. **Diese Woche:**
   - 🔵 10-20 Beta-Tester rekrutieren
   - 🔵 Testing-Anleitung schreiben
   - 🔵 PhotoCleaner v0.8.2 Build erstellen

3. **Nächste 2 Wochen:**
   - 🔵 Beta Testing läuft
   - 🔵 Feedback sammeln

4. **Danach:**
   - 🔵 Feedback analysieren
   - 🔵 Prioritäten setzen
   - 🔵 Fixes implementieren

---

**🎯 Ziel:** Datenbasierte Insights, um v1.0 rock-solid zu machen!
