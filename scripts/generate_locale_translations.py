#!/usr/bin/env python3
"""Generate FR/ES/NL locale files from existing i18n keys.

Uses machine translation as a bootstrap and preserves placeholders like {count}.
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Dict, List

from deep_translator import GoogleTranslator

from photo_cleaner.i18n import TRANSLATIONS

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "src" / "photo_cleaner" / "i18n_locales"

TARGETS = {
    "fr": "french",
    "es": "spanish",
    "nl": "dutch",
}

PLACEHOLDER_RE = re.compile(r"(\{[^{}]+\}|<[^>]+>|%p%|%\([^)]+\)[a-zA-Z])")


def _protect_text(text: str) -> tuple[str, Dict[str, str]]:
    replacements: Dict[str, str] = {}

    def repl(match: re.Match[str]) -> str:
        token = f"__TOK_{len(replacements)}__"
        replacements[token] = match.group(0)
        return token

    protected = PLACEHOLDER_RE.sub(repl, text)
    return protected, replacements


def _restore_text(text: str, replacements: Dict[str, str]) -> str:
    restored = text
    for token, original in replacements.items():
        restored = restored.replace(token, original)
    return restored


def _base_strings() -> Dict[str, str]:
    de = TRANSLATIONS.get("de", {})
    en = TRANSLATIONS.get("en", {})
    keys = set(de.keys()) | set(en.keys())
    base: Dict[str, str] = {}
    for key in keys:
        base[key] = en.get(key) or de.get(key) or key
    return base


def _translate_values(values: List[str], target_name: str) -> List[str]:
    translator = GoogleTranslator(source="auto", target=target_name)
    results: List[str] = []
    chunk_size = 30
    for i in range(0, len(values), chunk_size):
        chunk = values[i:i + chunk_size]
        translated = translator.translate_batch(chunk)
        if not isinstance(translated, list):
            translated = [translated]
        if len(translated) != len(chunk):
            translated = chunk
        results.extend([t if isinstance(t, str) and t else c for c, t in zip(chunk, translated)])
    return results


def generate() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = _base_strings()

    for lang_code, target_name in TARGETS.items():
        current = dict(TRANSLATIONS.get(lang_code, {}))

        # Translate only entries that still look untranslated (same as base or missing).
        to_translate_keys = [
            key for key, base_value in base.items()
            if key not in current or current.get(key) == base_value
        ]

        protected_values: List[str] = []
        metadata: List[Dict[str, str]] = []
        for key in to_translate_keys:
            source = base[key]
            protected, repl = _protect_text(source)
            protected_values.append(protected)
            metadata.append(repl)

        translated_protected = _translate_values(protected_values, target_name)

        for key, translated_value, repl in zip(to_translate_keys, translated_protected, metadata):
            restored = _restore_text(translated_value, repl)
            current[key] = restored

        # Ensure language labels are always explicit and local.
        if lang_code == "fr":
            current.update({
                "language_de": "Allemand",
                "language_en": "Anglais",
                "language_fr": "Francais",
                "language_es": "Espagnol",
                "language_nl": "Neerlandais",
            })
        elif lang_code == "es":
            current.update({
                "language_de": "Aleman",
                "language_en": "Ingles",
                "language_fr": "Frances",
                "language_es": "Espanol",
                "language_nl": "Neerlandes",
            })
        elif lang_code == "nl":
            current.update({
                "language_de": "Duits",
                "language_en": "Engels",
                "language_fr": "Frans",
                "language_es": "Spaans",
                "language_nl": "Nederlands",
            })

        out_path = OUT_DIR / f"{lang_code}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)
        print(f"Wrote {out_path} with {len(current)} keys")


if __name__ == "__main__":
    generate()
