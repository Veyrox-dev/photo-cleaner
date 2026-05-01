"""UI snapshot smoke for dark/light themes.

Renders a lightweight widget set in offscreen mode and writes PNG snapshots.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Use offscreen rendering for CI/headless environments.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QLineEdit, QProgressBar  # noqa: E402
from PySide6.QtGui import QPixmap  # noqa: E402
from photo_cleaner.theme import set_theme, generate_stylesheet  # noqa: E402
from photo_cleaner.ui.gallery.gallery_filter_bar import GalleryFilterBar  # noqa: E402


def _build_demo_widget(theme_name: str) -> QWidget:
    set_theme(theme_name)
    w = QWidget()
    w.setWindowTitle(f"PhotoCleaner Snapshot Smoke - {theme_name}")
    layout = QVBoxLayout(w)
    layout.setContentsMargins(16, 16, 16, 16)
    layout.setSpacing(10)

    title = QLabel(f"Theme Smoke: {theme_name}")
    button = QPushButton("Action")
    input_box = QLineEdit()
    input_box.setPlaceholderText("Search...")
    progress = QProgressBar()
    progress.setRange(0, 100)
    progress.setValue(68)

    filter_bar = GalleryFilterBar()

    layout.addWidget(title)
    layout.addWidget(filter_bar)
    layout.addWidget(input_box)
    layout.addWidget(button)
    layout.addWidget(progress)

    w.setStyleSheet(generate_stylesheet(theme_name))
    w.resize(1000, 280)
    return w


def _save_snapshot(widget: QWidget, target_path: Path) -> None:
    widget.show()
    QApplication.processEvents()
    pix = QPixmap(widget.size())
    widget.render(pix)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if not pix.save(str(target_path), "PNG"):
        raise RuntimeError(f"Failed to save snapshot: {target_path}")


def main() -> int:
    app = QApplication.instance() or QApplication([])
    output_dir = ROOT / "results" / "ui_snapshot_smoke"

    created: list[Path] = []
    for theme_name in ("dark", "light"):
        widget = _build_demo_widget(theme_name)
        out_file = output_dir / f"snapshot_{theme_name}.png"
        _save_snapshot(widget, out_file)
        created.append(out_file)
        widget.close()

    print("UI snapshot smoke OK")
    for path in created:
        print(f"  - {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
