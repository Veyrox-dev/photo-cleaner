#!/usr/bin/env python3
"""Synchronize FR/ES/NL/IT locale files from EN base keys.

Features:
- Audits missing/extra keys vs EN base.
- Fills missing keys and optionally refreshes untranslated values.
- Supports DeepL (API key) with Google fallback.
- Preserves placeholders like {count}, HTML tags and %-tokens.

Usage examples:
    python scripts/generate_locale_translations.py --audit-only
    python scripts/generate_locale_translations.py --provider deepl
    python scripts/generate_locale_translations.py --provider google --rewrite-equal

DeepL setup:
    set DEEPL_API_KEY=...  (Windows)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

import requests
from deep_translator import GoogleTranslator

ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from photo_cleaner.i18n import TRANSLATIONS  # noqa: E402

OUT_DIR = ROOT / "src" / "photo_cleaner" / "i18n_locales"

TARGETS = {
    "fr": {"google": "french", "deepl": "FR"},
    "es": {"google": "spanish", "deepl": "ES"},
    "nl": {"google": "dutch", "deepl": "NL"},
    "it": {"google": "italian", "deepl": "IT"},
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
    en = TRANSLATIONS.get("en", {})
    return dict(en)


def _load_locale_file(lang_code: str) -> Dict[str, str]:
    path = OUT_DIR / f"{lang_code}.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        loaded = json.load(f)
    return {str(k): str(v) for k, v in loaded.items() if isinstance(k, str)}


def _translate_google(values: List[str], target_name: str) -> List[str]:
    translator = GoogleTranslator(source="auto", target=target_name)
    results: List[str] = []
    chunk_size = 30
    for i in range(0, len(values), chunk_size):
        chunk = values[i : i + chunk_size]
        translated = translator.translate_batch(chunk)
        if not isinstance(translated, list):
            translated = [translated]
        if len(translated) != len(chunk):
            translated = chunk
        results.extend([t if isinstance(t, str) and t else c for c, t in zip(chunk, translated)])
    return results


def _translate_deepl(values: List[str], target_code: str, api_key: str) -> List[str]:
    if not values:
        return []

    url = os.environ.get("DEEPL_API_URL", "https://api-free.deepl.com/v2/translate")
    headers = {"Authorization": f"DeepL-Auth-Key {api_key}"}
    out: List[str] = []
    chunk_size = 50

    for i in range(0, len(values), chunk_size):
        chunk = values[i : i + chunk_size]
        data = {
            "target_lang": target_code,
            "source_lang": "EN",
            "preserve_formatting": "1",
            "tag_handling": "html",
        }
        payload = [("text", txt) for txt in chunk]
        resp = requests.post(url, headers=headers, data=[*data.items(), *payload], timeout=30)
        resp.raise_for_status()
        body = resp.json()
        translated = [item.get("text", "") for item in body.get("translations", [])]
        if len(translated) != len(chunk):
            raise RuntimeError("DeepL response size mismatch")
        out.extend([t if t else c for c, t in zip(chunk, translated)])

    return out


def _translate_values(values: List[str], lang_code: str, provider: str) -> List[str]:
    if provider == "deepl":
        api_key = os.environ.get("DEEPL_API_KEY", "").strip()
        if not api_key:
            raise RuntimeError("DEEPL_API_KEY not set")
        target_code = TARGETS[lang_code]["deepl"]
        return _translate_deepl(values, target_code, api_key)

    target_name = TARGETS[lang_code]["google"]
    return _translate_google(values, target_name)


def _translate_values_safe(values: List[str], lang_code: str, provider: str) -> List[str]:
    """Translate values with fallback to original text if provider is unavailable."""
    if not values:
        return []
    try:
        return _translate_values(values, lang_code, provider)
    except Exception as exc:
        print(f"{lang_code}: provider '{provider}' failed ({exc}); falling back to EN source for this batch")
        return list(values)


def _ensure_language_labels(lang_code: str, current: Dict[str, str]) -> None:
    if lang_code == "fr":
        current.update(
            {
                "language_de": "Allemand",
                "language_en": "Anglais",
                "language_fr": "Francais",
                "language_es": "Espagnol",
                "language_nl": "Neerlandais",
            }
        )
    elif lang_code == "es":
        current.update(
            {
                "language_de": "Aleman",
                "language_en": "Ingles",
                "language_fr": "Frances",
                "language_es": "Espanol",
                "language_nl": "Neerlandes",
            }
        )
    elif lang_code == "nl":
        current.update(
            {
                "language_de": "Duits",
                "language_en": "Engels",
                "language_fr": "Frans",
                "language_es": "Spaans",
                "language_nl": "Nederlands",
            }
        )
    elif lang_code == "it":
        current.update(
            {
                "language_de": "Tedesco",
                "language_en": "Inglese",
                "language_fr": "Francese",
                "language_es": "Spagnolo",
                "language_nl": "Olandese",
                "language_it": "Italiano",
            }
        )


def _audit(base: Dict[str, str], locale_map: Dict[str, Dict[str, str]]) -> None:
    base_keys = set(base.keys())
    for lang_code, current in locale_map.items():
        current_keys = set(current.keys())
        missing = sorted(base_keys - current_keys)
        extra = sorted(current_keys - base_keys)
        print(f"{lang_code}: missing={len(missing)} extra={len(extra)}")
        if missing:
            print(f"  missing sample: {missing[:10]}")
        if extra:
            print(f"  extra sample: {extra[:10]}")


def generate(provider: str, audit_only: bool, rewrite_equal: bool, prune_extra: bool) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = _base_strings()
    locale_map = {lang: _load_locale_file(lang) for lang in TARGETS}

    _audit(base, locale_map)
    if audit_only:
        return

    base_keys = set(base.keys())

    for lang_code, current in locale_map.items():
        removed_extra = 0
        if prune_extra:
            extra_keys = [k for k in current.keys() if k not in base_keys]
            removed_extra = len(extra_keys)
            for key in extra_keys:
                current.pop(key, None)

        to_translate_keys = [
            key
            for key, base_value in base.items()
            if key not in current or (rewrite_equal and current.get(key) == base_value)
        ]

        if not to_translate_keys:
            _ensure_language_labels(lang_code, current)
            out_path = OUT_DIR / f"{lang_code}.json"
            with out_path.open("w", encoding="utf-8") as f:
                json.dump(current, f, ensure_ascii=False, indent=2)
            prune_info = f", pruned {removed_extra} extra" if prune_extra else ""
            print(f"{lang_code}: up to date ({len(current)} keys{prune_info})")
            continue

        protected_values: List[str] = []
        metadata: List[Dict[str, str]] = []
        for key in to_translate_keys:
            source = base[key]
            protected, repl = _protect_text(source)
            protected_values.append(protected)
            metadata.append(repl)

        translated_protected = _translate_values_safe(protected_values, lang_code, provider)

        for key, translated_value, repl in zip(to_translate_keys, translated_protected, metadata):
            current[key] = _restore_text(translated_value, repl)

        _ensure_language_labels(lang_code, current)

        out_path = OUT_DIR / f"{lang_code}.json"
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(current, f, ensure_ascii=False, indent=2)

        prune_info = f", pruned {removed_extra} extra" if prune_extra else ""
        print(
            f"{lang_code}: wrote {out_path.name} ({len(to_translate_keys)} translated, total {len(current)}{prune_info})"
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync locale JSON files from EN i18n keys")
    parser.add_argument(
        "--provider",
        choices=("deepl", "google"),
        default="google",
        help="translation backend (default: google)",
    )
    parser.add_argument(
        "--audit-only",
        action="store_true",
        help="only compare keys, do not modify locale files",
    )
    parser.add_argument(
        "--rewrite-equal",
        action="store_true",
        help="also retranslate entries that are still identical to EN source",
    )
    parser.add_argument(
        "--prune-extra",
        action="store_true",
        help="remove locale keys that are not present in EN base",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    generate(
        provider=args.provider,
        audit_only=args.audit_only,
        rewrite_equal=args.rewrite_equal,
        prune_extra=args.prune_extra,
    )
