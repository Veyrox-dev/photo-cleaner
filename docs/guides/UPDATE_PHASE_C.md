# Update-Logik Phase C – Entscheidungsvorlage

**Stand:** 10. April 2026  
**Status:** Entschieden → MSI-only für v1.0; MSIX/AppInstaller als Post-Launch-Option  
**Abhängigkeit:** Phase A ✅ (Manifest-Check + Download-Link produktiv seit 2026-04-10)  
**Dokument:** Entscheidungsvorlage – keine Implementierung in v1.0 erforderlich

---

## Kontext

Phase A liefert einen einfachen Hinweis-Dialog mit Download-Link.  
Phase B (spezifiziert in `docs/guides/UPDATE_PHASE_B.md`) fügt In-App-Download + optionalen MSI-Start hinzu.  
Phase C bewertet, ob ein **Delta-Update-Kanal** via MSIX/AppInstaller sinnvoll und notwendig ist.

---

## Optionen im Vergleich

| Kriterium | MSI-only (Phase A + B) | MSI + MSIX/AppInstaller |
|---|---|---|
| **Komplexität** | Gering – vorhandene WiX/MSI-Pipeline nutzen | Hoch – zweites Paketformat, Signing, Store-Prozesse |
| **Update-Größe** | Vollinstaller je Release (~50–150 MB) | Delta-Patches möglich (kleinere Downloads) |
| **Stille Installation** | Nur mit Elevationsrechten | AppInstaller erledigt das systemseitig |
| **Code-Signing** | EV-Zertifikat + Timestamp reicht | Identisch; zusätzlich MSIX-Publisher-ID |
| **Rollback** | MSI MajorUpgrade überschreibt – kein Auto-Rollback | AppInstaller bietet kein echtes Rollback |
| **Nutzerbasis** | Direktdownload / EXE-Nutzer → MSI ist idiomatisch | Microsoft-Store-Nutzer: derzeit keine Zielgruppe |
| **Aufwand bis Launch** | Null (bereits vorhanden) | 3–5 Entwicklertage + Store-Zertifizierungsdurchlauf |
| **Risiko** | Minimal | Mittelhoch (neue Pipeline, Signing-Abhängigkeit) |

---

## Entscheidung für v1.0

**→ MSI-only.**

Begründung:
- Phase A (Hinweis + Link) ist produktiv. Phase B (In-App-Download) ist spezifiziert und als v1.1-Upgrade anschlussfähig.
- MSIX/AppInstaller bietet keinen messbaren Vorteil für die aktuelle Nutzerbasis (Direktdownload / EV-MSI).
- Der Delta-Update-Vorteil wird erst bei hoher Release-Frequenz relevant; für v1.0 sind Releases selten.
- Kein zusätzlicher Aufwand vor Launch notwendig.

---

## Post-Launch-Bewertungskriterien (wann MSIX sinnvoll wird)

MSIX/AppInstaller lohnt sich neu zu bewerten, sobald **mindestens zwei** dieser Punkte zutreffen:

1. Release-Zyklus kürzer als 8 Wochen (Delta-Größe relevant).
2. Nutzerbeschwerden über langsamen/großen Download häufen sich.
3. Code-Signing-Zertifikat bereits vorhanden und amortisiert.
4. Microsoft-Store-Distribution wird ein strategisches Ziel.
5. Phase B (In-App-Download) ist produktiv und die nächste natürliche Ausbaustufe ist stille Installation.

---

## Empfohlene Reihenfolge nach Launch

```
v1.0  →  Phase A (Hinweis + Link)  ✅ produktiv
v1.1  →  Phase B (In-App-Download + optional MSI-Start)  📄 spezifiziert
v1.2+ →  Phase C erneut bewerten (MSIX ggf. wenn Kriterien oben erfüllt)
```

---

## Offene Abhängigkeiten

| Punkt | Status |
|---|---|
| EV-Code-Signing-Zertifikat | ▶ geplant (Publisher-Vertrauen für MSI) |
| WiX v4 MSI-Pipeline | ✅ fertig (`scripts/build_msi.ps1`) |
| Website-Manifest `/updates/latest.json` | ✅ produktiv |
| Phase B Implementierung | 📄 spezifiziert, nicht implementiert |
