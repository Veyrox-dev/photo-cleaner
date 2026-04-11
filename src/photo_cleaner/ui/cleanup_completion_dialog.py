from __future__ import annotations

import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QPointF, Qt, QTimer, QUrl
from PySide6.QtGui import QColor, QDesktopServices, QPainter, QPen
from PySide6.QtWidgets import QDialog, QFrame, QHBoxLayout, QLabel, QPushButton, QProgressBar, QVBoxLayout, QWidget

from photo_cleaner.theme import get_theme_colors
from photo_cleaner.ui.color_constants import get_semantic_colors


def _format_bytes(num_bytes: int) -> str:
    size = max(0, int(num_bytes or 0))
    units = ("B", "KB", "MB", "GB", "TB")
    value = float(size)
    unit = units[0]
    for unit in units:
        if value < 1024.0 or unit == units[-1]:
            break
        value /= 1024.0
    if unit == "B":
        return f"{int(value)} {unit}"
    return f"{value:.1f} {unit}"


def _format_mb(num_bytes: int) -> str:
    value = max(0.0, float(num_bytes) / (1024.0 * 1024.0))
    if value >= 100:
        return f"{value:,.0f}".replace(",", ".")
    return f"{value:,.1f}".replace(",", "X").replace(".", ",").replace("X", ".")


@dataclass
class _Particle:
    x: float
    y: float
    vx: float
    vy: float
    size: float
    color: QColor
    life: float
    max_life: float
    rotation: float
    rotation_speed: float


class _CelebrationCanvas(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._particles: list[_Particle] = []
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._spawn_until = 0.0

    def start(self, intensity: int) -> None:
        self._particles.clear()
        self._spawn_until = time.monotonic() + min(1.6, 0.7 + (intensity / (1024 * 1024 * 600)))
        if not self._timer.isActive():
            self._timer.start(16)

    def _spawn_particles(self, count: int) -> None:
        width = max(1, self.width())
        height = max(1, self.height())
        palette = [
            QColor("#1D9E75"),
            QColor("#5DCAA5"),
            QColor("#9FE1CB"),
            QColor("#1F6F8B"),
            QColor("#E7B646"),
        ]
        origin_y = max(36.0, height * 0.28)
        for _ in range(count):
            self._particles.append(
                _Particle(
                    x=(width * 0.5) + random.uniform(-width * 0.18, width * 0.18),
                    y=origin_y + random.uniform(-10.0, 12.0),
                    vx=random.uniform(-2.8, 2.8),
                    vy=random.uniform(-5.2, -2.4),
                    size=random.uniform(4.0, 8.0),
                    color=random.choice(palette),
                    life=0.0,
                    max_life=random.uniform(34.0, 60.0),
                    rotation=random.uniform(0.0, 360.0),
                    rotation_speed=random.uniform(-10.0, 10.0),
                )
            )

    def _tick(self) -> None:
        now = time.monotonic()
        if now < self._spawn_until:
            self._spawn_particles(random.randint(2, 4))

        next_particles: list[_Particle] = []
        gravity = 0.15
        for particle in self._particles:
            particle.x += particle.vx
            particle.y += particle.vy
            particle.vy += gravity
            particle.life += 1.0
            particle.rotation += particle.rotation_speed
            if particle.life < particle.max_life and particle.y < (self.height() + 40):
                next_particles.append(particle)
        self._particles = next_particles
        self.update()
        if not self._particles and now >= self._spawn_until:
            self._timer.stop()

    def paintEvent(self, event) -> None:  # type: ignore[override]
        if not self._particles:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        for particle in self._particles:
            alpha = max(0.0, 1.0 - (particle.life / particle.max_life))
            color = QColor(particle.color)
            color.setAlphaF(alpha)
            painter.save()
            painter.translate(QPointF(particle.x, particle.y))
            painter.rotate(particle.rotation)
            painter.setBrush(color)
            painter.drawRoundedRect(
                int(-particle.size / 2),
                int(-particle.size / 2),
                int(particle.size),
                int(particle.size * 1.4),
                2,
                2,
            )
            painter.restore()


class CleanupCompletionDialog(QDialog):
    def __init__(
        self,
        *,
        title: str,
        cleaned_bytes: int,
        removed_count: int,
        exported_count: int = 0,
        skipped_count: int = 0,
        archive_path: Optional[Path] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(520)
        self.cleaned_bytes = max(0, int(cleaned_bytes or 0))
        self.removed_count = max(0, int(removed_count or 0))
        self.exported_count = max(0, int(exported_count or 0))
        self.skipped_count = max(0, int(skipped_count or 0))
        self.archive_path = archive_path
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._animation_started_at = 0.0
        self._animation_duration = 1.6

        self._build_ui()

    def _build_ui(self) -> None:
        theme_colors = get_theme_colors()
        semantic_colors = get_semantic_colors()
        self.setStyleSheet(
            f"QDialog {{ background: {theme_colors['base']}; }}"
            f"QLabel {{ color: {theme_colors['text']}; }}"
            f"QFrame#card {{ background: {theme_colors['alternate_base']}; border: 1px solid {theme_colors['border']}; border-radius: 18px; }}"
            f"QFrame#statCard {{ background: {theme_colors['base']}; border: 1px solid {theme_colors['border']}; border-radius: 14px; }}"
            f"QPushButton {{ border-radius: 12px; padding: 10px 18px; border: 1px solid {theme_colors['border']}; background: {theme_colors['alternate_base']}; color: {theme_colors['text']}; font-weight: 600; }}"
            f"QPushButton:hover {{ border-color: {semantic_colors['success']}; }}"
            f"QPushButton#primaryButton {{ background: {semantic_colors['success']}; color: white; border-color: {semantic_colors['success']}; }}"
        )

        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)

        card = QFrame(self)
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 22, 22, 18)
        card_layout.setSpacing(14)
        root.addWidget(card)

        self._canvas = _CelebrationCanvas(card)
        self._canvas.lower()

        eyebrow = QLabel("PhotoCleaner - Bereinigung abgeschlossen", card)
        eyebrow.setStyleSheet(f"font-size: 12px; letter-spacing: 1.6px; text-transform: uppercase; color: {theme_colors['disabled_text']};")
        card_layout.addWidget(eyebrow, alignment=Qt.AlignHCenter)

        headline = QLabel("Du hast Speicher freigemacht", card)
        headline.setStyleSheet("font-size: 24px; font-weight: 700;")
        card_layout.addWidget(headline, alignment=Qt.AlignHCenter)

        counter_row = QHBoxLayout()
        counter_row.setSpacing(10)
        counter_row.setAlignment(Qt.AlignHCenter)
        self.counter_label = QLabel("0", card)
        self.counter_label.setStyleSheet("font-size: 68px; font-weight: 700; line-height: 1; color: #1D9E75;")
        counter_row.addWidget(self.counter_label)
        unit_label = QLabel("MB", card)
        unit_label.setStyleSheet(f"font-size: 28px; font-weight: 600; color: {theme_colors['disabled_text']};")
        counter_row.addWidget(unit_label, alignment=Qt.AlignBottom)
        card_layout.addLayout(counter_row)

        self.summary_label = QLabel("0 MB bereinigt", card)
        self.summary_label.setStyleSheet(f"font-size: 13px; color: {theme_colors['disabled_text']};")
        card_layout.addWidget(self.summary_label, alignment=Qt.AlignHCenter)

        self.progress_bar = QProgressBar(card)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setRange(0, 1000)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedHeight(12)
        self.progress_bar.setStyleSheet(
            f"QProgressBar {{ background: {theme_colors['base']}; border: 1px solid {theme_colors['border']}; border-radius: 6px; }}"
            f"QProgressBar::chunk {{ background: {semantic_colors['success']}; border-radius: 6px; }}"
        )
        card_layout.addWidget(self.progress_bar)

        stats_row = QHBoxLayout()
        stats_row.setSpacing(10)
        stats_row.addWidget(self._build_stat_card("Dateien bereinigt", str(self.removed_count)))
        stats_row.addWidget(self._build_stat_card("Exportiert", str(self.exported_count)))
        stats_row.addWidget(self._build_stat_card("Gesamt frei", _format_bytes(self.cleaned_bytes)))
        if self.skipped_count:
            stats_row.addWidget(self._build_stat_card("Uebersprungen", str(self.skipped_count)))
        card_layout.addLayout(stats_row)

        note = QLabel(
            "Die Dateien wurden aus dem aktiven Review entfernt. Die Originaldateien bleiben physisch erhalten.",
            card,
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"font-size: 12px; color: {theme_colors['disabled_text']};")
        card_layout.addWidget(note)

        button_row = QHBoxLayout()
        button_row.setSpacing(10)
        if self.archive_path is not None:
            open_button = QPushButton("Exportordner oeffnen", card)
            open_button.clicked.connect(self._open_archive_folder)
            button_row.addWidget(open_button)
        button_row.addStretch(1)
        close_button = QPushButton("Fertig", card)
        close_button.setObjectName("primaryButton")
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        card_layout.addLayout(button_row)

    def _build_stat_card(self, label: str, value: str) -> QFrame:
        theme_colors = get_theme_colors()
        frame = QFrame(self)
        frame.setObjectName("statCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(2)
        value_label = QLabel(value, frame)
        value_label.setAlignment(Qt.AlignCenter)
        value_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        layout.addWidget(value_label)
        text_label = QLabel(label, frame)
        text_label.setAlignment(Qt.AlignCenter)
        text_label.setStyleSheet(f"font-size: 11px; color: {theme_colors['disabled_text']};")
        layout.addWidget(text_label)
        return frame

    def resizeEvent(self, event) -> None:  # type: ignore[override]
        super().resizeEvent(event)
        if hasattr(self, "_canvas"):
            self._canvas.setGeometry(self.rect())

    def showEvent(self, event) -> None:  # type: ignore[override]
        super().showEvent(event)
        self._animation_started_at = time.monotonic()
        self._animation_timer.start(16)
        self._canvas.start(self.cleaned_bytes)

    def _advance_animation(self) -> None:
        elapsed = time.monotonic() - self._animation_started_at
        progress = min(1.0, elapsed / self._animation_duration)
        eased = 1.0 - pow(1.0 - progress, 3)
        current_bytes = int(self.cleaned_bytes * eased)
        self.counter_label.setText(_format_mb(current_bytes))
        self.summary_label.setText(f"Du hast aktuell {_format_bytes(current_bytes)} eingespart")
        self.progress_bar.setValue(int(eased * 1000))
        if progress >= 1.0:
            self._animation_timer.stop()

    def _open_archive_folder(self) -> None:
        if self.archive_path is None:
            return
        target = self.archive_path.parent if self.archive_path.is_file() else self.archive_path
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(target)))