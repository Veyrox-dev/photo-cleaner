"""Pre-release theme audit for PhotoCleaner.

Checks:
- Dark/Light theme key parity
- Hex color format validity
- Minimum contrast for key text/background pairs
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from photo_cleaner.theme import THEMES  # noqa: E402

HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _hex_to_rgb(value: str) -> tuple[float, float, float]:
    value = value.lstrip("#")
    return (int(value[0:2], 16) / 255.0, int(value[2:4], 16) / 255.0, int(value[4:6], 16) / 255.0)


def _linearize(c: float) -> float:
    if c <= 0.03928:
        return c / 12.92
    return ((c + 0.055) / 1.055) ** 2.4


def _luminance(hex_color: str) -> float:
    r, g, b = _hex_to_rgb(hex_color)
    return 0.2126 * _linearize(r) + 0.7152 * _linearize(g) + 0.0722 * _linearize(b)


def _contrast_ratio(a: str, b: str) -> float:
    la = _luminance(a)
    lb = _luminance(b)
    light = max(la, lb)
    dark = min(la, lb)
    return (light + 0.05) / (dark + 0.05)


def main() -> int:
    failures: list[str] = []

    dark_keys = set(THEMES["dark"].keys())
    light_keys = set(THEMES["light"].keys())

    if dark_keys != light_keys:
        missing_in_light = sorted(dark_keys - light_keys)
        missing_in_dark = sorted(light_keys - dark_keys)
        if missing_in_light:
            failures.append(f"Missing keys in light theme: {missing_in_light}")
        if missing_in_dark:
            failures.append(f"Missing keys in dark theme: {missing_in_dark}")

    for theme_name, colors in THEMES.items():
        for key, value in colors.items():
            if not HEX_RE.match(value):
                failures.append(f"{theme_name}.{key} has invalid hex color: {value}")

    # Key readability checks (WCAG-ish thresholds for UI text)
    checks = [
        ("window_text", "window", 4.5),
        ("text", "base", 4.5),
        ("button_text", "button", 3.0),
        ("input_text", "input_bg", 4.5),
        ("highlighted_text", "highlight", 3.0),
    ]

    for theme_name, colors in THEMES.items():
        for fg, bg, min_ratio in checks:
            ratio = _contrast_ratio(colors[fg], colors[bg])
            if ratio < min_ratio:
                failures.append(
                    f"{theme_name}: contrast {fg}/{bg}={ratio:.2f} below {min_ratio:.2f}"
                )

    if failures:
        print("Theme audit FAILED")
        for item in failures:
            print(f"  - {item}")
        return 1

    print("Theme audit OK")
    print(f"  - Theme keys checked: {len(dark_keys)}")
    print("  - Dark/Light contrast checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
