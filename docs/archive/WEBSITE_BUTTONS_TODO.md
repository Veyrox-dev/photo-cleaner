# PhotoCleaner Website - Buttons & Links To-Do Liste

**Status:** alle Elemente identifiziert | **Priorität:** zusammengefasst | **Letzte Aktualisierung:** März 2026

---

## 📋 Übersicht

| Kategorie | Anzahl Elemente | Funktional | Zu implementieren |
|-----------|-----------------|-----------|------------------|
| **Header/Nav** | 7 | 5 | 2 |
| **Hero Section** | 2 | 0 | 2 |
| **Pricing Section** | 2 | 1 | 1 |
| **Contact Section** | 1 | 1 | 0 |
| **CTA Section** | 2 | 0 | 2 |
| **Footer** | 8 | 2 | 6 |
| **GESAMT** | **22** | **9** | **13** |

---

## 🚀 PRIORITÄT 1 - CRITICAL (Download verlinken) - IN UMSETZUNG ✅

**Status:** 5/5 Buttons werden JETZT implementiert!

Diese 5 Buttons sind zentral für die User Journey und müssen ZUERST umgesetzt werden:

| # | Element | Bereich | Status | Aufgabe | Design-Check |
|---|---------|--------|--------|---------|--------------|
| **1** | "Download" Button (Header) | Header/Nav | 🔄 IN PROGRESS | → `https://photocleaner.de/download` | ✓ Groß, prominent, btn-primary |
| **2** | "Jetzt herunterladen" Button | Hero | 🔄 IN PROGRESS | → `https://photocleaner.de/download` | ✓ Groß, Hauptfokus, btn-primary |
| **3** | "Kostenlos herunterladen" Button | Final CTA | 🔄 IN PROGRESS | → `https://photocleaner.de/download` | ✓ Groß, btn-primary |
| **4** | "Download" Link (Footer) | Footer | 🔄 IN PROGRESS | → `https://photocleaner.de/download` | ✓ Klein, Footer-Style |
| **5** | "Download" Button (Pricing Free Plan) | Pricing | 🔄 IN PROGRESS | → `https://photocleaner.de/download` | ✓ Medium, btn-secondary |

---

## 📌 PRIORITÄT 2 - HIGH (Nach Download einrichten)

Diese 5 Elemente sind sekundär wichtig und sollten danach folgen:

| # | Element | Bereich | Status | Aufgabe | Design-Check |
|---|---------|--------|--------|---------|--------------|
| **6** | "Pro aktivieren" Button | Pricing Pro Plan | ✅ IMPLEMENTIERT | → `https://buy.stripe.com/test_7sY28r7yX0xS47a8bP00000` | ✓ Medium, btn-primary, featured card |
| **7** | "Dokumentation" Button | Hero | ❌ nicht funktional | → Link zu Dokumentations-Seite oder PDF | ✓ Transparent white bg, secondary |
| **8** | "Mehr erfahren" Button (Header) | Header/Nav | ✅ funktional (→ #pricing) | ✓ überprüfen ob Link korrekt | ✓ Klein, btn-secondary |
| **9** | "Mehr erfahren" Button (Final CTA) | Final CTA | ❌ nicht funktional | → Link zu Features/Dokumentation | ✓ Medium, btn-secondary |
| **10** | Email Link "support@photocleaner.de" | Contact | ✅ funktional | ✓ überprüfen ob korrekt | ✓ Prominent, mail-to:|

---

## 📑 PRIORITÄT 3 - MEDIUM (Rechtliches & Navigation)

Diese 6 Elemente sollten implementiert werden, sind aber nicht kritisch für die User Journey:

| # | Element | Bereich | Status | Aufgabe | Design-Check |
|---|---------|--------|--------|---------|--------------|
| **11** | "FAQ" Link | Footer & Header | ❌ nicht funktional | → Link zu FAQ-Seite oder Support | ✓ Klein, Footer-Style |
| **12** | "Impressum" Link | Footer | ❌ nicht funktional | → Rechtlich erforderlich, Link zu Impressum | ✓ Klein, Footer-Style |
| **13** | "Datenschutz" Link | Footer | ❌ nicht funktional | → Rechtlich erforderlich, Link zu Datenschutzseite | ✓ Klein, Footer-Style |
| **14** | "Dokumentation" Link | Footer | ❌ nicht funktional | → Link zu Docs (könnte FAQ sein) | ✓ Klein, Footer-Style |
| **15** | "Changelog" Link | Footer | ❌ nicht funktional | → Link zu Changelog/Release Notes | ✓ Klein, Footer-Style |
| **16** | Email Link "info@photocleaner.de" | Footer | ✅ funktional | ✓ überprüfen ob korrekt | ✓ Klein, Footer-Style |

---

## ✅ BEREITS FUNKTIONAL

Diese 7 Elemente sind bereits korrekt verlinkt:

| # | Element | Bereich | Link | Status |
|---|---------|--------|------|--------|
| **A** | "Mehr erfahren" Button | Header | → #pricing | ✅ anchor link |
| **B** | "Features" Link | Navigation | → #features | ✅ anchor link |
| **C** | "Preise" Link | Navigation | → #pricing | ✅ anchor link |
| **D** | "Sicherheit" Link | Navigation | → #security | ✅ anchor link |
| **E** | "Kontakt" Link | Navigation | → #contact | ✅ anchor link |
| **F** | "Features" Link | Footer | → #features | ✅ anchor link |
| **G** | Email Links | Contact + Footer | mailto: | ✅ funktional |

---

## 🎨 DESIGN-CHECKS FÜR ALLE BUTTONS

Checkliste für visuelle Konsistenz:

### Button-Größen
- [ ] `.btn-lg` (Hero, CTA) = `padding: 12px 28px; font-size: 15px` ✓
- [ ] `.btn` (Header) = `padding: 10px 20px; font-size: 14px` ✓
- [ ] Konsistenz bei Hover-Effekten prüfen

### Button-Farben
- [ ] `.btn-primary` = Blue #2563eb mit Hover-Dunkelblau ✓
- [ ] `.btn-secondary` = Blue border, transparent background ✓
- [ ] Transparent white (Dokumentation) = rgba(255,255,255,0.2) background ✓

### Hover-States
- [ ] Primary Buttons: `transform: translateY(-1px)` ✓
- [ ] Secondary Buttons: Background wechselt zu Blau ✓
- [ ] Alle Links: Farbe wechselt zu darker shade ✓

### Responsive Design
- [ ] Desktop (>768px): Alle Buttons sichtbar ✓
- [ ] Tablet (768px): Buttons angepasst ✓
- [ ] Mobile (<480px): Buttons full-width bei Bedarf
  - [ ] Hero Buttons: Check full-width stacking
  - [ ] CTA Buttons: Check full-width stacking
  - [ ] Pricing Buttons: Check size
  - [ ] Header Buttons: Check size reduction

### Mobile-Optimierungen
- [ ] Button-Größe auf 768px: `padding: 8px 16px; font-size: 13px` ✓
- [ ] Button-Größe auf 480px: Check padding/gap
- [ ] Touch-Target mindestens 44px x 44px ✓
- [ ] Spacing bei mehreren Buttons angepasst ✓

---

## 🔗 UMSETZUNGS-REIHENFOLGE

### Phase 1: Critical Path - JETZT IN UMSETZUNG ✅
```
✅ 1. Download URL definiert: https://photocleaner.de/download
   ↓
✅ 2. Alle "Download" Buttons verlinkt (5/5):
   ✓ Header "Download" Button
   ✓ Hero "Jetzt herunterladen" 
   ✓ CTA "Kostenlos herunterladen"
   ✓ Pricing Free Plan "Download"
   ✓ Footer "Download" Link
   ↓
✅ 3. Stripe Test URL implementiert:
   ✓ Pro aktivieren Button → https://buy.stripe.com/test_7sY28r7yX0xS47a8bP00000
```

### Phase 2: Secondary Links (Week 2)
```
1. Dokumentation-Seite erstellen oder linken
2. "Dokumentation" Button implementieren
3. "Mehr erfahren" (CTA) zu Features linken
```

### Phase 3: Rechtliches & Support (Week 3)
```
1. FAQ-Seite erstellen
2. Impressum-Seite erstellen (rechtlich erforderlich)
3. Datenschutz-Seite erstellen (rechtlich erforderlich)
4. Changelog-Seite erstellen
```

### Phase 4: Verifizierung (Week 4)
```
1. Alle Links Tests durchführen (Desktop/Tablet/Mobile)
2. Hover-States überprüfen
3. Responsive Behavior überprüfen
4. Email-Links testen
5. Externe Links auf Zuladezeit prüfen
```

---

## 📊 BUTTON-TYPEN & IHRE ROLLEN

### Primary Buttons (Blau - call-to-action)
- **Zweck:** Main conversion goal (Download, Pro aktivieren)
- **Farbe:** #2563eb
- **Größe:** Variabel (btn oder btn-lg)
- **Hover:** Dunkler + Lift-Effekt
- **Elemente:** 4
  - Down Button Header
  - Jetzt herunterladen (Hero)
  - Pro aktivieren (Pricing)
  - Kostenlos herunterladen (CTA)

### Secondary Buttons (Blue Border - secondary action)
- **Zweck:** Sekundäre actions (mehr Info, Download alternativer)
- **Farbe:** Border blau, transparent background
- **Hover:** Background wird blau, Text weiß
- **Größe:** Variabel
- **Elemente:** 4
  - Mehr erfahren (Header)
  - Download (Pricing Free)
  - Dokumentation (Hero - special white style)
  - Mehr erfahren (Final CTA)

### Links (Text-basiert)
- **Zweck:** Navigation zwischen Seiten
- **Farbe:** #2563eb → dunkelblau on hover
- **Größe:** 14px
- **Elemente:** 14
  - Nav-Links (5)
  - Footer-Links (9)

---

## ✨ BESONDERE DESIGN-ELEMENTE

### 1. Dokumentation Button (Hero) - CUSTOM STYLING
```css
/* White transparent background with white border */
background: rgba(255, 255, 255, 0.2);
border: 1.5px solid white;
color: white;
font-weight: 600;
```
**Status:** ✅ Implementiert
**Check:** Funktioniert auf Dark Background ✓

### 2. Pricing Card Featured Badge
Die "Pro" Karte hat:
- `.pricing-badge` (Empfohlen - oben)
- Dicker Border (2px statt 1.5px)
- Stärkerer Shadow
**Status:** ✅ CSS vorhanden
**Check:** Visuell prominent ✓

### 3. Button Groups (Flex Layout)
- `.hero-buttons` = gap: 16px, flex-wrap
- `.cta-buttons` = gap: 16px, flex-wrap
**Mobile:** `flex-direction: column` bei <640px
**Status:** ✅ Responsive
**Check:** Spacing auf Mobile überprüfen

---

## 🔍 WEITERE DESIGN-ASPEKTE

### Button Spacing
- [ ] Gap zwischen Buttons: 16px (--spacing-md) ✓
- [ ] Gap bei mobile: Gleich (flex-direction: column)
- [ ] Padding inside buttons: Konsistent ✓

### Button Accessibility
- [ ] Alle Buttons haben `cursor: pointer` ✓
- [ ] Alle Links haben `text-decoration: none` ✓
- [ ] Kontrast White-on-Blue: ✓ WCAG AAA
- [ ] Focus-States: ⚠️ Könnten hinzugefügt werden
  ```css
  .btn:focus {
      outline: 2px solid var(--primary);
      outline-offset: 2px;
  }
  ```

### Footer Link Styling
- Komplettes Styling vorhanden ✓
- Hover → weiß ✓
- Font: 14px ✓
- Color: rgba(255, 255, 255, 0.7) → white on hover ✓

---

## 📱 RESPONSIVE BREAKPOINTS CHECKLIST

### Desktop (>768px)
- [ ] Alle Nav-Links sichtbar
- [ ] Header mit Buttons
- [ ] Hero Buttons nebeneinander
- [ ] Pricing Grid: 2 Spalten
- [ ] Footer Grid: 3 Spalten

### Tablet (768px)
- [ ] Nav-Links ausblenden (✓ display: none)
- [ ] Hero Buttons: Check size
- [ ] Pricing Grid: auto-fit
- [ ] Footer Grid: 1 Spalte

### Mobile (480px)
- [ ] Button Size: 8px 16px (✓ implementiert)
- [ ] Button Full-Width: bei Bedarf
- [ ] Spacing: reduziert
- [ ] Header: kompakt (56px vs 64px)

---

## 🎯 ZUSAMMENFASSUNG

**Arbeitsaufwand:**
- ✅ Design & CSS: 100% Done
- 🔄 Links & URLs: ~60% Done (15/22 implementiert + 5 Critical in Umsetzung)
- ✅ Stripe-Integration: Test URL implementiert

**Nächste Schritte:**
1. **Definitionen klären:**
   - Wo liegt der Download-Installer?
   - Stripe/Lizenz-System: Welche Plattform?
   - Wo liegen Docs?

2. **URLs sammeln:**
   - `https://photocleaner.de/download` (oder wo?)
   - `https://photocleaner.de/docs`
   - `https://photocleaner.de/faq`
   - `https://photocleaner.de/impressum`
   - `https://photocleaner.de/datenschutz`
   - `https://photocleaner.de/changelog`

3. **In HTML einsetzen** (sobald URLs definiert)

4. **Testing durchführen:**
   - Links funktionieren
   - Responsive Design OK
   - Hover-States OK
   - Lade-Geschwindigkeit OK

---

**Letzte Änderung:** März 3, 2026
**Verantwortlich:** Design & Development Team
