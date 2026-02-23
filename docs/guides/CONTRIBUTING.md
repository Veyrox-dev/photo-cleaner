# Beitragsrichtlinien

Danke für dein Interesse an PhotoCleaner! 

## Entwicklungsumgebung einrichten

```powershell
# Repository klonen
git clone <repo-url>
cd photo-cleaner

# Virtual Environment
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]

# Tests ausführen
pytest
```

## Code-Stil

- Python ≥ 3.12 Syntax
- Type Hints verwenden
- Docstrings für öffentliche Funktionen
- PEP 8 befolgen (mit black formatieren)

## Pull Requests

1. Feature-Branch erstellen: `git checkout -b feature/mein-feature`
2. Tests hinzufügen für neue Funktionen
3. Commit Messages auf Deutsch oder Englisch
4. Pull Request mit Beschreibung erstellen

## Tests

```powershell
# Alle Tests
pytest

# Mit Coverage
pytest --cov=src --cov-report=html

# Spezifische Tests
pytest tests/test_indexer.py
```

## Berichterstattung von Bugs

Bitte öffne ein Issue mit:
- Beschreibung des Problems
- Schritte zur Reproduktion
- Python-Version und OS
- Relevante Log-Ausgaben

## Feature-Vorschläge

Feature-Vorschläge sind willkommen! Bitte beschreibe:
- Use Case
- Erwartetes Verhalten
- Mögliche Implementierung (optional)
