# 📊 PhotoCleaner Beta Feedback

Dieser Ordner speichert Feedback-Dateien von Beta-Testern für PhotoCleaner v0.8.3+.

## 📁 Struktur

```
feedback/
├── feedback_user1@example.de_1703001234567.json
├── feedback_user2@example.de_1703001256789.json
└── ... weitere Feedback-Dateien
```

## 📤 Wie man Feedback sammelt

### Für den Beta-Tester:
1. Öffne `feedback_form.html` in deinem Browser
2. Fülle das Formular aus
3. Klicke auf **"Feedback absenden"**
4. Eine JSON-Datei wird automatisch heruntergeladen
5. **Speichere diese Datei in diesem Ordner** (`feedback/`)

### Für den Entwickler:
1. Alle heruntergeladenen JSON-Dateien in diesem Ordner speichern
2. Mit `analyze_feedback.py` (in Zukunft) auswerten
3. Trends und häufige Probleme identifizieren

## 📋 JSON-Datei-Format

```json
{
  "timestamp": "2026-02-22T14:30:45.123Z",
  "version": "0.8.3",
  "email": "vater@example.de",
  "image_count": "100-500",
  "image_types": ["portraits", "landscapes"],
  "accuracy": "85",
  "trust": "4",
  "eye_quality": "4",
  "sharpness": "3",
  "lighting": "4",
  "speed": "very_fast",
  "nps": "8",
  "overall": "4",
  "likes": "...",
  "dislikes": "...",
  "bugs": "...",
  "would_buy": "probably",
  "additional": "..."
}
```

## 🔄 Automatische Verarbeitung (TODO v1.0)

In Zukunft könnte ein Script alle JSON-Dateien auswerten und Statistiken generieren:
- Durchschnittliche Bewertungen
- Häufige Bugs
- NPS (Net Promoter Score)
- Feature-Ranking

## 📝 Anleitung für deinen Vater

**So funktioniert's:**
1. Öffne im Photo-Cleaner Ordner die Datei `feedback_form.html` mit deinem Browser (Firefox, Chrome, Edge - egal)
2. Fülle das Formular aus (keine Sorge, dauert ca. 5-10 Min)
3. Klick auf **"Feedback absenden"** unten
4. Es wird eine Datei heruntergeladen z.B. `feedback_vater_1234567890.json`
5. **Speichere diese Datei im `feedback/` Ordner** (neben dieser README.md)

Das ist alles! Dann wird die Datei direkt bei dir im Projekt gespeichert. ✨
