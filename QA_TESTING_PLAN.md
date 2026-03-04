# 📋 Phase 2 & 3 - QA Testing & Validation Plan

**Status:** Alle Secondary & Rechtliche Links - IMPLEMENTIERT & READY FOR TESTING ✅
**Zeitstempel:** März 3, 2026
**Priorität:** QA Validation vor nächster Feature-Phase

---

## 📊 PHASE 2 & 3 IMPLEMENTATION STATUS

### Phase 2: Secondary Links - KOMPLETT IMPLEMENTIERT ✅

| # | Element | Link | Status | Typ | Tested |
|---|---------|------|--------|-----|--------|
| **A** | Hero "Dokumentation" Button | `https://photocleaner.de/docs` | ✅ LIVE | External | 🔄 Pending |
| **B** | CTA "Mehr erfahren" Button | `#features` | ✅ LIVE | Anchor | 🔄 Pending |
| **C** | Contact Email | `mailto:info@photocleaner.de` | ✅ LIVE | mailto | 🔄 Pending |

### Phase 3: Rechtliches & Support - KOMPLETT IMPLEMENTIERT ✅

| # | Element | Link | Status | Typ | Tested |
|---|---------|------|--------|-----|--------|
| **D** | Footer "FAQ" Link | `https://photocleaner.de/faq` | ✅ LIVE | External | 🔄 Pending |
| **E** | Footer "Impressum" Link | `https://photocleaner.de/impressum` | ✅ LIVE | External | 🔄 Pending |
| **F** | Footer "Datenschutz" Link | `https://photocleaner.de/datenschutz` | ✅ LIVE | External | 🔄 Pending |
| **G** | Footer "Dokumentation" Link | `https://photocleaner.de/docs` | ✅ LIVE | External | 🔄 Pending |
| **H** | Footer "Changelog" Link | `https://photocleaner.de/changelog` | ✅ LIVE | External | 🔄 Pending |

---

## 🎯 GESAMTSTATUS - ALL BUTTONS & LINKS

| Phase | Bereich | Buttons | Status | Priority |
|-------|---------|---------|--------|----------|
| **1** | Critical Download | 5 | ✅ 100% LIVE | 🔴 CRITICAL |
| **1** | Stripe Pro | 1 | ✅ LIVE | 🔴 CRITICAL |
| **2** | Secondary Links | 3 | ✅ LIVE | 🟠 HIGH |
| **3** | Rechtliches | 5 | ✅ LIVE | 🟡 MEDIUM |
| **TOTAL** | **22 Elements** | **14** | **✅ 64% LIVE** | |

---

## ✅ DETAILLIERTE QA CHECKLIST

### SECTION 1: PHASE 1 CRITICAL BUTTONS - VALIDIERUNG

#### 1.1 Header "Download" Button
- **Element:** `.nav-cta` → `.btn.btn-primary.btn-lg`
- **Link:** `https://photocleaner.de/download`
- **Visual Style:** Blau, Groß, Prominent

**Desktop Testing (>768px):**
- [ ] Button sichtbar im Header neben "Mehr erfahren"
- [ ] Link Ziel korrekt
- [ ] Hover-Effekt: Dunkler Blau + Lift Effekt
- [ ] Cursor ändert zu Pointer
- [ ] Kein Text-Decoration sichtbar

**Tablet Testing (768px):**
- [ ] Button verkleinert (padding: 8px 16px)
- [ ] Positioning OK
- [ ] Hover-Effekt funktioniert

**Mobile Testing (480px):**
- [ ] Button verkleinert
- [ ] Kein Text-Overflow
- [ ] Touch-Target >44x44px
- [ ] Spacing OK

**Responsive Media Query Check:**
- [ ] `@media (max-width: 768px)` → `.btn { padding: 8px 16px; font-size: 13px; }` ✓
- [ ] Keine zusätzliche Mobile-Anpassung nötig

---

#### 1.2 Hero "Jetzt herunterladen" Button
- **Element:** `.hero-buttons` → first `.btn.btn-primary.btn-lg`
- **Link:** `https://photocleaner.de/download`
- **Background:** Blue Gradient (#2563eb → #1e40af)
- **Text Color:** White

**Desktop Testing (>768px):**
- [ ] Button prominent im Hero sichtbar
- [ ] Neben "Dokumentation" Button (gap: 16px)
- [ ] Text "Jetzt herunterladen" klar lesbar (weiß auf blau)
- [ ] Hover-Effekt sichtbar (dunkelblau + lift)
- [ ] Link navigiert zu Download

**Tablet Testing (768px):**
- [ ] Buttons nebeneinander oder stacked?
- [ ] Größe angepasst?
- [ ] Spacing angepasst?

**Mobile Testing (<640px):**
- [ ] Buttons stacked vertikal (flex-direction: column)
- [ ] Full-width Verhalten prüfen
- [ ] Spacing zwischen Buttons prüfen

**HTML Structure Check:**
```html
<button> → <a href>? ✓ Link-Element verwenden
Ist es "Jetzt herunterladen"? ✓
Style: btn btn-primary btn-lg? ✓
```

---

#### 1.3 Hero "Dokumentation" Button (Custom White Style)
- **Element:** `.hero-buttons` → second `.btn.btn-lg` (custom style)
- **Link:** `https://photocleaner.de/docs`
- **Background:** `rgba(255, 255, 255, 0.2)` (transparent white)
- **Border:** `1.5px solid white`
- **Text Color:** White, font-weight: 600

**Desktop Testing (>768px):**
- [ ] Button sichtbar neben Hauptbutton
- [ ] Transparent white Background sichtbar
- [ ] White border deutlich sichtbar
- [ ] Text "Dokumentation" weiß auf transparent
- [ ] Hover-Effekt funktoniert (was passiert? → sollte kontrast erhöhen)
- [ ] Link navigiert zu Docs

**Color Contrast Check:**
- [ ] White text on rgba(255,255,255,0.2) background?
- [ ] Hover-State für besseren Kontrast?
- [ ] WCAG AA minimum 4.5:1 erfüllt?

**Tablet/Mobile Testing:**
- [ ] Button stacked mit Hauptbutton
- [ ] Größe angepasst
- [ ] Custom Style bleibt sichtbar
- [ ] Spacing korrekt

---

#### 1.4 Pricing Free "Download" Button
- **Element:** `.pricing-card` (nicht featured) → `.btn.btn-secondary.btn-lg`
- **Link:** `https://photocleaner.de/download` (NICHT #contact!)
- **Style:** Blue border, transparent background

**Desktop Testing (>768px):**
- [ ] Button in Free Pricing Card sichtbar
- [ ] Blue Border sichtbar
- [ ] Transparent Background
- [ ] Text "Download" blau (#2563eb)
- [ ] Hover: Background blau, Text weiß
- [ ] Link korrekt zu Download

**Visual Alignment:**
- [ ] Button Position in Card korrekt?
- [ ] Größe konsistent mit anderen Buttons?
- [ ] Padding um Button OK?

**Tablet/Mobile Testing:**
- [ ] Pricing Grid Verhalten überprüfen
- [ ] Button-Größe angepasst
- [ ] Full-width Behavior auf Mobile?

**Critical Check:**
- [ ] War auf `#contact`? → FIXED zu `https://photocleaner.de/download` ✓

---

#### 1.5 Pricing Pro "Pro aktivieren" Button (Stripe Test Link)
- **Element:** `.pricing-card.featured` → `.btn.btn-primary.btn-lg`
- **Link:** `https://buy.stripe.com/test_7sY28r7yX0xS47a8bP00000`
- **Target:** `target="_blank"` (neuer Tab)
- **Security:** `rel="noopener"`
- **Style:** Blue solid, weiß Text

**Desktop Testing (>768px):**
- [ ] Button prominent in Pro Card sichtbar
- [ ] Blau solid background
- [ ] Text "Pro aktivieren" weiß
- [ ] Hover-Effekt: dunkler blau + lift
- [ ] Klick → Stripe Test URL öffnet in NEUEM TAB
- [ ] Keine Sicherheitswarnungen

**Stripe Link Validation:**
- [ ] URL `https://buy.stripe.com/test_7sY28r7yX0xS47a8bP00000` erreichbar? (externe Validierung)
- [ ] Test Mode aktiv?
- [ ] Stripe Test Karten funktionieren? (optional: Test-Payment durchführen)

**Security Checks:**
- [ ] `target="_blank"` implementiert? ✓
- [ ] `rel="noopener"` implementiert? ✓
- [ ] Keine referrer info gesendet?

**Featured Card Styling:**
- [ ] Border 2px statt 1.5px? ✓
- [ ] Shadow größer (--shadow-lg)? ✓
- [ ] Badge "Empfohlen" sichtbar? ✓

**Tablet/Mobile Testing:**
- [ ] Card Layout angepasst?
- [ ] Button-Größe OK?
- [ ] Border auf Mobile angepasst (1.5px statt 2px)?

---

#### 1.6 Final CTA "Kostenlos herunterladen" Button
- **Element:** `.section-dark` → `.cta-buttons` → first `.btn.btn-primary.btn-lg`
- **Link:** `https://photocleaner.de/download`
- **Background:** Blue (#2563eb)

**Desktop Testing (>768px):**
- [ ] Button prominent auf Dark Section (#0f172a background)
- [ ] Text weiß klar lesbar
- [ ] Hover-Effekt sichtbar (dunkelblau + lift)
- [ ] Link zu Download

**Color Contrast:**
- [ ] White on #2563eb = Good Contrast ✓
- [ ] WCAG AAA erfüllt?

**Tablet/Mobile Testing:**
- [ ] Button stacked mit "Mehr erfahren"
- [ ] Full-width auf Mobile?
- [ ] Größe angepasst
- [ ] Spacing OK

---

### SECTION 2: PHASE 2 SECONDARY LINKS - VALIDIERUNG

#### 2.1 Hero "Dokumentation" Button
**Bereits validiert in 1.3**

#### 2.2 CTA "Mehr erfahren" Button (Anchor zu #features)
- **Element:** `.section-dark` → `.cta-buttons` → second `.btn.btn-secondary.btn-lg`
- **Link:** `#features` (Anchor Link)
- **Style:** Border blau, transparent, text blau

**Desktop Testing (>768px):**
- [ ] Button neben CTA Button sichtbar
- [ ] Blue Border sichtbar auf Dark Background
- [ ] Text blau sichtbar
- [ ] Hover: Background blau, Text weiß
- [ ] Klick → Scrollt zu #features Section
- [ ] Scroll-Behavior: smooth? (html { scroll-behavior: smooth; } ✓)

**Accessibility Check:**
- [ ] Anchor Link funktioniert auf allen Browsern?
- [ ] Focus-State beim Scrollen sichtbar?

**Tablet/Mobile Testing:**
- [ ] Button stacked
- [ ] Anchor Link funktioniert auf Mobile?
- [ ] Smooth Scroll auf Mobile OK?

---

#### 2.3 Contact Email
- **Element:** `#contact` Section → `.contact-box` → `<a href="mailto:...">`
- **Link:** `mailto:info@photocleaner.de`
- **Visual:** Text-Link, blau, Hover dunkler

**Desktop Testing:**
- [ ] Email Link sichtbar in Contact Box
- [ ] Farbe blau (#2563eb)
- [ ] Hover: dunkelblau
- [ ] Klick → Standard Mail-Client öffnet

**Email Client Test:**
- [ ] Outlook/Thunderbird/Apple Mail startet?
- [ ] To-Adresse korrekt eingetragen?
- [ ] Keine Fehler beim Mailto-Link?

**Mobile Testing:**
- [ ] Tappbar (>44x44px)?
- [ ] Mail-App öffnet statt Web-Mailer?
- [ ] Link sichtbar und prominent?

---

### SECTION 3: PHASE 3 RECHTLICHES - VALIDIERUNG

#### 3.1 Footer "FAQ" Link
- **Element:** `.footer-section` (Navigation) → `<a href="...">FAQ</a>`
- **Link:** `https://photocleaner.de/faq`
- **Style:** Footer Link (14px, rgba(255,255,255,0.7), hover weiß)

**Desktop Testing:**
- [ ] Link sichtbar in Footer unter "Navigation"
- [ ] Farbe: Grau-Weiß (rgba(255,255,255,0.7))
- [ ] Hover: Weiß
- [ ] Link funktioniert

**Footer Styling Check:**
```css
.footer-section a {
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  transition: var(--transition);
}
.footer-section a:hover {
  color: white;
}
```
- [ ] Styling korrekt angewendet?
- [ ] Hover-Transition smooth?

**Mobile Testing:**
- [ ] Link tappbar?
- [ ] Spacing OK zwischen Links?
- [ ] Footer Grid auf 1 Spalte?

---

#### 3.2 Footer "Impressum" Link
- **Element:** `.footer-section` (Rechtliches) → `<a href="...">Impressum</a>`
- **Link:** `https://photocleaner.de/impressum`
- **Rechtliches:** ERFORDERLICH in Deutschland

**Desktop Testing:**
- [ ] Link sichtbar unter "Rechtliches"
- [ ] Styling konsistent mit anderen Footer Links
- [ ] Hover funktioniert
- [ ] Link funktioniert

**Rechtliche Prüfung:**
- [ ] Impressum Seite existiert? (TBD)
- [ ] Enthält alle erforderlichen Infos:
  - [ ] Name & Adresse des Unternehmens
  - [ ] Kontakt (Email, Telefon ggf.)
  - [ ] Vertretungsberechtigte Person
  - [ ] Registrierungsdetails (HRB, USt-ID etc.)
  - [ ] Haftungsausschluss

---

#### 3.3 Footer "Datenschutz" Link
- **Element:** `.footer-section` (Rechtliches) → `<a href="...">Datenschutz</a>`
- **Link:** `https://photocleaner.de/datenschutz`
- **Rechtliches:** ERFORDERLICH (GDPR/DSGVO)

**Desktop Testing:**
- [ ] Link sichtbar unter "Rechtliches"
- [ ] Styling OK
- [ ] Hover funktioniert
- [ ] Link funktioniert

**GDPR/DSGVO Compliance Prüfung:**
- [ ] Datenschutzerklärung existiert? (TBD)
- [ ] Enthält folgende Punkte:
  - [ ] Verantwortlicher (Data Controller)
  - [ ] Verarbeitete Daten (Login-Daten, Email, IP)
  - [ ] Zweck der Verarbeitung
  - [ ] Berechtigungsgrundlage (Consent, Contract, etc.)
  - [ ] Speicherdauer
  - [ ] Betroffenenrechte (Zugriff, Löschung, Portabilität, etc.)
  - [ ] Drittländer-Transfers (falls relevant)
  - [ ] Cookie-Richtlinie (falls Cookies verwendet)
  - [ ] Kontakt zu DPA/Datenschutzbeauftragtem

---

#### 3.4 Footer "Dokumentation" Link
- **Element:** `.footer-section` (Kontakt) → `<a href="...">Dokumentation</a>`
- **Link:** `https://photocleaner.de/docs`

**Desktop Testing:**
- [ ] Link sichtbar unter "Kontakt"
- [ ] Styling konsistent
- [ ] Hover OK
- [ ] Link funktioniert

**Consistency Check:**
- [ ] Gleiche URL wie Hero "Dokumentation" Button (`/docs`)? ✓
- [ ] Beide verlinken auf gleiche Seite? ✓

---

#### 3.5 Footer "Changelog" Link
- **Element:** `.footer-section` (Kontakt) → `<a href="...">Changelog</a>`
- **Link:** `https://photocleaner.de/changelog`

**Desktop Testing:**
- [ ] Link sichtbar unter "Kontakt"
- [ ] Styling OK
- [ ] Hover funktioniert
- [ ] Link funktioniert

**Changelog Content Check:**
- [ ] Changelog Seite existiert? (TBD)
- [ ] Dokumentiert Version History:
  - [ ] Version Nummern (v1.0, v1.1, etc.)
  - [ ] Release Dates
  - [ ] Features (neue Funktionen)
  - [ ] Bug Fixes (behobene Fehler)
  - [ ] Breaking Changes
  - [ ] Download Links für alte Versionen (optional)

---

## 🎨 DESIGN VALIDATION CHECKLIST

### Button-Größen Konsistenz

#### Desktop (>768px)
```css
.btn-lg {
  padding: 12px 28px;
  font-size: 15px;
}
```

**Points zu überprüfen:**
- [ ] Alle Download Buttons uniform?
- [ ] Stripe Button gleiche Größe?
- [ ] CTA Buttons gleich groß?
- [ ] Footer Links kleinere Font (14px)?

#### Tablet (768px Media Query)
```css
.btn {
  padding: 8px 16px;
  font-size: 13px;
}
```

- [ ] Header Buttons verkleinert?
- [ ] Hero Buttons verkleinert?
- [ ] Pricing Buttons verkleinert?

#### Mobile (<640px)
**Beobacht:**
- [ ] Sind Buttons `.btn-lg` noch full-width?
- [ ] Flexbox `flex-direction: column` bei Mehreren?
- [ ] Padding noch angemessen?
- [ ] Touch-Target >44x44px überall?

---

### Button-Farben Konsistenz

#### Primary Buttons (#2563eb - Blue)
- [ ] Header Download
- [ ] Hero "Jetzt herunterladen"
- [ ] Pricing Pro
- [ ] CTA "Kostenlos herunterladen"
- **Hover:** #1e40af (Dunkelblau) ✓

#### Secondary Buttons (Blue Border)
- [ ] Header "Mehr erfahren"
- [ ] Pricing Free "Download"
- [ ] CTA "Mehr erfahren"
- **Hover:** Blau background, weiß Text ✓

#### Special (White Transparent)
- [ ] Hero "Dokumentation"
- **Background:** rgba(255,255,255,0.2) ✓
- **Border:** 1.5px white ✓
- **Hover:** ? (zu überprüfen)

#### Links (Text)
- [ ] Nav Links: #0f172a (dark) → #2563eb (hover)
- [ ] Footer Links: rgba(255,255,255,0.7) → white (hover)
- [ ] All smooth transition (0.2s)

---

### Hover-Effects Validation

**Primary Buttons:**
```css
.btn-primary:hover {
  background: var(--primary-dark);
  transform: translateY(-1px);
}
```
- [ ] Farbe ändert sich zu #1e40af?
- [ ] Lift-Effekt sichtbar (translateY -1px)?
- [ ] Transition smooth (0.2s)?
- [ ] Cursor zeigt Pointer?

**Secondary Buttons:**
```css
.btn-secondary:hover {
  background: var(--primary);
  color: white;
}
```
- [ ] Background wechselt zu Blau?
- [ ] Text wird weiß?
- [ ] Transition smooth?

**Links:**
```css
a:hover {
  color: var(--primary-dark);
}
```
- [ ] Text-Farbe dunkelblau?
- [ ] Smooth transition?

---

### Spacing & Alignment Prüfung

#### Button Groups
**Hero Buttons:**
```css
.hero-buttons {
  display: flex;
  gap: var(--spacing-md);  /* 16px */
  justify-content: center;
  flex-wrap: wrap;
}
```
- [ ] Gap zwischen Buttons 16px?
- [ ] Centered? ✓
- [ ] Wrapping auf Mobile?

**CTA Buttons:**
```css
.cta-buttons {
  display: flex;
  gap: var(--spacing-md);  /* 16px */
  justify-content: center;
  flex-wrap: wrap;
}
```
- [ ] Gap 16px?
- [ ] Centered?
- [ ] Mobile stacking?

#### Footer Grid
```css
.footer-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--spacing-3xl);  /* 64px */
  margin-bottom: var(--spacing-2xl);  /* 48px */
}
```
- [ ] 3 Spalten am Desktop?
- [ ] Gap 64px (großzügig)?
- [ ] Mobile: 1 Spalte?

---

## 📱 RESPONSIVE DESIGN TESTS

### Desktop (>768px)
**Browser:** Chrome, Firefox, Safari (wenn möglich)
**Viewport:** 1920x1080, 1366x768, 1024x768

Checklist:
- [ ] Header: Alle Nav Links sichtbar
- [ ] Hero: Beide Buttons nebeneinander
- [ ] Pricing: 2 Spalten
- [ ] CTA: Beide Buttons nebeneinander
- [ ] Footer: 3 Spalten
- [ ] Alle Links anklickbar
- [ ] Alle Hover-Effekte sichtbar

### Tablet (768px)
**Browser:** Chrome DevTools Tablet Mode
**Viewport:** 768x1024 (iPad)

Checklist:
- [ ] Header: Nav Links ausgeblendet ✓
- [ ] Hero: Buttons nebeneinander oder stacked?
- [ ] Pricing: Auto-fit (2 oder 1 Spalte?)
- [ ] CTA: Check Layout
- [ ] Footer: 1 Spalte?
- [ ] Touch-Targets >44x44px?

### Mobile (≤480px)
**Browser:** Chrome DevTools Mobile Mode
**Viewport:** 375x667 (iPhone), 360x640 (Android)

Checklist:
- [ ] Header: Kompakt (56px height)
- [ ] Hero: Buttons full-width stacked
- [ ] Pricing: 1 Spalte
- [ ] CTA: Buttons full-width stacked
- [ ] Footer: 1 Spalte
- [ ] Kein Horizontal Scrolling
- [ ] Text lesbar
- [ ] Alle Links tappbar (>44x44px)

---

## 🔍 CROSS-BROWSER TESTING

| Browser | Desktop | Tablet | Mobile | Status |
|---------|---------|--------|--------|--------|
| **Chrome** | [ ] | [ ] | [ ] | 🔄 Pending |
| **Firefox** | [ ] | [ ] | [ ] | 🔄 Pending |
| **Safari** | [ ] | [ ] | [ ] | 🔄 Pending |
| **Edge** | [ ] | [ ] | [ ] | 🔄 Pending |

**Points zu testen pro Browser:**
- [ ] Links sind anklickbar
- [ ] Hover-Effekte sichtbar
- [ ] Farben korrekt
- [ ] Layout responsive
- [ ] Keine Rendering-Fehler

---

## ✅ QA SIGN-OFF CHECKLIST

### Funktionalität (100% Passing)
- [ ] Alle 14 implementierten Links funktionieren
- [ ] Keine 404 Fehler (externe Links zu echten URLs testen)
- [ ] Keine JavaScript Fehler (DevTools Console)
- [ ] Email Links öffnen Mail-Client

### Design Konsistenz (100% Passing)
- [ ] Button-Größen einheitlich
- [ ] Farben konsistent
- [ ] Hover-Effekte alle sichtbar
- [ ] Spacing korrekt

### Responsive Design (100% Passing)
- [ ] Desktop OK
- [ ] Tablet OK
- [ ] Mobile OK
- [ ] Kein Horizontal Scrolling

### Accessibility (100% Passing)
- [ ] Color Contrast WCAG AAA
- [ ] Touch-Targets >44x44px
- [ ] Focus States sichtbar (optional: implementieren)
- [ ] Semantic HTML (<a>, <button>)

### Performance (100% Passing)
- [ ] Load Time akzeptabel
- [ ] Keine Render-Blocking Resources
- [ ] Images optimiert

---

## 📝 ISSUES TRACKER

**Gefundene Probleme während QA:**

| Issue | Severity | Komponente | Lösung | Status |
|-------|----------|-----------|--------|--------|
| EXAMPLE: Hover-Effekt nicht sichtbar | Medium | Hero "Dokumentation" | CSS überprüfen | 🔄 Open |

---

## 📋 NEXT STEPS NACH QA APPROVAL

### 1. QA Testing durchführen (Diese Checklist)
- [ ] Alle Tests durchführen
- [ ] Alle Fehler dokumentieren
- [ ] Fehler beheben

### 2. Phase 4 - Seiten-Erstellung
Nach erfolgreicher QA:
- [ ] FAQ Seite erstellen
- [ ] Impressum Seite erstellen
- [ ] Datenschutz Seite erstellen
- [ ] Changelog Seite erstellen
- [ ] Dokumentation Seite erstellen

### 3. Integration Testing
- [ ] Alle Links verweisen auf echte Seiten
- [ ] Keine Broken Links
- [ ] Navigation konsistent

### 4. Final Launch
- [ ] Website Review
- [ ] SEO Check
- [ ] Analytics Setup
- [ ] Go Live

---

**Status Summary:**
```
✅ Critical Buttons: 5/5 LIVE
✅ Secondary Links: 3/3 LIVE
✅ Rechtliches: 5/5 LIVE
🔄 QA Testing: PENDING
⏳ Seiten-Erstellung: TBD
```

**Verantwortlich:** Design & QA Team
**Deadline:** Nach vollständiger QA Validierung
