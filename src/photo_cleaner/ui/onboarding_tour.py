from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional

from PySide6.QtCore import QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


@dataclass(frozen=True)
class OnboardingStep:
    title: str
    body: str
    target: QWidget


class OnboardingTourDialog(QDialog):
    """Modal guided tour with dimmed overlay and highlighted target widget."""

    def __init__(
        self,
        parent: QWidget,
        steps: List[OnboardingStep],
        *,
        dont_show_label: str,
        skip_label: str,
        next_label: str,
        prev_label: str,
        finish_label: str,
        interactive_toggle_label: str,
        interactive_hint_label: str,
    ) -> None:
        super().__init__(parent)
        self._steps = steps
        self._step_index = 0
        self._dont_show_again = False
        self._highlight_rect = QRect()
        self._interactive_hint_label_text = interactive_hint_label

        self.setModal(True)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setObjectName("onboarding_tour_overlay")
        self.setFocusPolicy(Qt.StrongFocus)

        self._card = QFrame(self)
        self._card.setObjectName("onboarding_tour_card")
        self._card.setStyleSheet(
            "QFrame#onboarding_tour_card {"
            "background: #fbfcff;"
            "border: 1px solid #9bb8f5;"
            "border-radius: 14px;"
            "}"
            "QLabel#onboarding_tour_step_counter { font-size: 11px; font-weight: 700; color: #2f6fde; }"
            "QLabel#onboarding_tour_title { font-size: 18px; font-weight: 700; color: #151a2d; }"
            "QLabel#onboarding_tour_body { font-size: 13px; color: #2b3144; line-height: 1.35; }"
            "QCheckBox { color: #1a1f36; }"
            "QPushButton {"
            "background: #2f6fde; color: white; border: none; border-radius: 8px;"
            "padding: 6px 12px; min-width: 90px;"
            "}"
            "QPushButton:hover { background: #275ec1; }"
            "QPushButton:disabled { background: #9ab2e8; }"
            "QPushButton#onboarding_secondary { background: #e6ecfb; color: #173d93; }"
            "QPushButton#onboarding_secondary:hover { background: #d9e3fb; }"
        )

        card_layout = QVBoxLayout(self._card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(10)

        self._step_counter_label = QLabel()
        self._step_counter_label.setObjectName("onboarding_tour_step_counter")
        self._step_counter_label.setAlignment(Qt.AlignLeft)
        card_layout.addWidget(self._step_counter_label)

        self._title_label = QLabel()
        self._title_label.setObjectName("onboarding_tour_title")
        card_layout.addWidget(self._title_label)

        self._body_label = QLabel()
        self._body_label.setObjectName("onboarding_tour_body")
        self._body_label.setWordWrap(True)
        self._body_label.setTextFormat(Qt.PlainText)
        card_layout.addWidget(self._body_label)

        self._interactive_mode_checkbox = QCheckBox(interactive_toggle_label)
        self._interactive_mode_checkbox.toggled.connect(self._on_interactive_mode_toggled)
        card_layout.addWidget(self._interactive_mode_checkbox)

        self._interactive_hint_label = QLabel(interactive_hint_label)
        self._interactive_hint_label.setWordWrap(True)
        self._interactive_hint_label.setStyleSheet("color: #173d93; font-size: 11px;")
        self._interactive_hint_label.hide()
        card_layout.addWidget(self._interactive_hint_label)

        self._dont_show_checkbox = QCheckBox(dont_show_label)
        card_layout.addWidget(self._dont_show_checkbox)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)

        self._skip_btn = QPushButton(skip_label)
        self._skip_btn.setObjectName("onboarding_secondary")
        self._skip_btn.clicked.connect(self._on_skip)
        button_row.addWidget(self._skip_btn)

        button_row.addStretch(1)

        self._prev_btn = QPushButton(prev_label)
        self._prev_btn.setObjectName("onboarding_secondary")
        self._prev_btn.clicked.connect(self._on_prev)
        button_row.addWidget(self._prev_btn)

        self._next_btn = QPushButton(next_label)
        self._finish_label = finish_label
        self._next_label = next_label
        self._next_btn.clicked.connect(self._on_next)
        button_row.addWidget(self._next_btn)

        card_layout.addLayout(button_row)

    @property
    def dont_show_again(self) -> bool:
        return self._dont_show_again

    def exec(self) -> int:  # noqa: A003
        self._sync_geometry()
        self._apply_step(0)
        return super().exec()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._reposition_card()

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)

        painter.fillRect(self.rect(), QColor(10, 12, 20, 170))

        if self._highlight_rect.isValid():
            glow_pen = QPen(QColor(255, 255, 255, 220), 3)
            painter.setPen(glow_pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(self._highlight_rect, 10, 10)

            accent_pen = QPen(QColor(47, 111, 222, 255), 3)
            painter.setPen(accent_pen)
            painter.drawRoundedRect(self._highlight_rect.adjusted(2, 2, -2, -2), 10, 10)
            self._draw_callout_arrow(painter)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if self._card.geometry().contains(event.pos()):
            super().mousePressEvent(event)
            return

        if self._interactive_mode_checkbox.isChecked() and self._highlight_rect.contains(event.pos()):
            self._advance_step_from_click()
            event.accept()
            return

        super().mousePressEvent(event)

    def _sync_geometry(self) -> None:
        parent = self.parentWidget()
        if not parent:
            return
        self.setGeometry(parent.rect())

    def _on_prev(self) -> None:
        if self._step_index > 0:
            self._apply_step(self._step_index - 1)

    def _on_next(self) -> None:
        if self._step_index >= len(self._steps) - 1:
            self._dont_show_again = self._dont_show_checkbox.isChecked()
            self.accept()
            return
        self._apply_step(self._step_index + 1)

    def _on_skip(self) -> None:
        self._dont_show_again = self._dont_show_checkbox.isChecked()
        self.reject()

    def _on_interactive_mode_toggled(self, enabled: bool) -> None:
        self._interactive_hint_label.setVisible(enabled)
        if enabled:
            self._interactive_hint_label.setText(self._interactive_hint_label_text)

    def _advance_step_from_click(self) -> None:
        if self._step_index >= len(self._steps) - 1:
            self._dont_show_again = self._dont_show_checkbox.isChecked()
            self.accept()
            return
        self._apply_step(self._step_index + 1)

    def _target_rect_for_step(self, step: OnboardingStep) -> QRect:
        widget = step.target
        if not widget or not widget.isVisible():
            return QRect()

        top_left = self.mapFromGlobal(widget.mapToGlobal(QPoint(0, 0)))
        rect = QRect(top_left, widget.size())
        return rect.adjusted(-6, -6, 6, 6)

    def _reposition_card(self) -> None:
        card_w = 500
        card_h = min(300, max(220, self._card.sizeHint().height()))
        self._card.resize(card_w, card_h)

        if not self._highlight_rect.isValid():
            x = max(20, (self.width() - card_w) // 2)
            y = max(20, self.height() - card_h - 24)
            self._card.move(x, y)
            return

        gap = 18
        right_x = self._highlight_rect.right() + gap
        left_x = self._highlight_rect.left() - card_w - gap
        y = self._highlight_rect.top()

        if right_x + card_w <= self.width() - 20:
            x = right_x
        elif left_x >= 20:
            x = left_x
        else:
            x = max(20, min(self.width() - card_w - 20, self._highlight_rect.center().x() - card_w // 2))
            y = self._highlight_rect.bottom() + gap

        y = max(20, min(self.height() - card_h - 20, y))
        self._card.move(x, y)

    @staticmethod
    def _point_on_rect_edge_towards(rect: QRect, target: QPointF) -> QPointF:
        cx = rect.center().x()
        cy = rect.center().y()
        dx = target.x() - cx
        dy = target.y() - cy

        if dx == 0 and dy == 0:
            return QPointF(cx, cy)

        half_w = max(1.0, rect.width() / 2.0)
        half_h = max(1.0, rect.height() / 2.0)

        scale_x = half_w / abs(dx) if dx else float("inf")
        scale_y = half_h / abs(dy) if dy else float("inf")
        scale = min(scale_x, scale_y)
        return QPointF(cx + dx * scale, cy + dy * scale)

    def _draw_callout_arrow(self, painter: QPainter) -> None:
        card_rect = self._card.geometry()
        if not card_rect.isValid() or not self._highlight_rect.isValid():
            return

        highlight_center = QPointF(self._highlight_rect.center())
        card_center = QPointF(card_rect.center())

        start = self._point_on_rect_edge_towards(card_rect, highlight_center)
        end = self._point_on_rect_edge_towards(self._highlight_rect, card_center)

        line_pen = QPen(QColor(255, 255, 255, 240), 2)
        painter.setPen(line_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawLine(start, end)

        angle = math.atan2(end.y() - start.y(), end.x() - start.x())
        arrow_size = 10.0
        wing = 5.5

        p1 = QPointF(
            end.x() - arrow_size * math.cos(angle) + wing * math.sin(angle),
            end.y() - arrow_size * math.sin(angle) - wing * math.cos(angle),
        )
        p2 = QPointF(
            end.x() - arrow_size * math.cos(angle) - wing * math.sin(angle),
            end.y() - arrow_size * math.sin(angle) + wing * math.cos(angle),
        )

        painter.setBrush(QColor(255, 255, 255, 240))
        painter.setPen(Qt.NoPen)
        painter.drawPolygon(QPolygonF([end, p1, p2]))

    def _apply_step(self, index: int) -> None:
        self._step_index = index
        step = self._steps[index]
        self._step_counter_label.setText(f"Schritt {index + 1} / {len(self._steps)}")

        self._title_label.setText(step.title)
        self._body_label.setText(step.body)

        self._highlight_rect = self._target_rect_for_step(step)
        self._prev_btn.setEnabled(index > 0)

        is_last = index == len(self._steps) - 1
        self._next_btn.setText(self._finish_label if is_last else self._next_label)

        self._reposition_card()
        self.update()
