from __future__ import annotations

from typing import List

from PySide6.QtWidgets import QFrame, QGridLayout, QScrollArea, QVBoxLayout, QWidget


class VirtualScrollContainer(QWidget):
    """Virtual scrolling container for large image grids.

    Only renders visible items to improve performance.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        self.items: List[QWidget] = []
        self.visible_items: dict[int, QWidget] = {}
        self.item_height = 310
        self.items_per_row = 5

        self._build_ui()

    def _build_ui(self):
        """Build virtual scroll UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.verticalScrollBar().valueChanged.connect(self._on_scroll)

        self.container = QWidget()
        self.grid_layout = QGridLayout(self.container)
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(8, 8, 8, 8)

        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def set_items(self, items: List[QWidget]):
        """Set items for virtual scrolling."""
        self.items = items

        total_rows = (len(items) + self.items_per_row - 1) // self.items_per_row
        total_height = total_rows * self.item_height
        self.container.setMinimumHeight(total_height)

        self._render_visible_items()

    def _on_scroll(self):
        """Handle scroll event."""
        self._render_visible_items()

    def _render_visible_items(self):
        """Render only visible items."""
        if not self.items:
            return

        scroll_pos = self.scroll.verticalScrollBar().value()
        viewport_height = self.scroll.viewport().height()

        start_row = max(0, scroll_pos // self.item_height - 1)
        end_row = min(
            (len(self.items) + self.items_per_row - 1) // self.items_per_row,
            (scroll_pos + viewport_height) // self.item_height + 2,
        )

        start_idx = start_row * self.items_per_row
        end_idx = min(len(self.items), end_row * self.items_per_row)

        for idx in list(self.visible_items.keys()):
            if idx < start_idx or idx >= end_idx:
                card = self.visible_items.pop(idx)
                self.grid_layout.removeWidget(card)
                card.hide()

        for idx in range(start_idx, end_idx):
            if idx not in self.visible_items and idx < len(self.items):
                card = self.items[idx]
                row = idx // self.items_per_row
                col = idx % self.items_per_row
                self.grid_layout.addWidget(card, row, col)
                card.show()
                self.visible_items[idx] = card

    def get_selected_indices(self) -> List[int]:
        """Get indices of all selected items."""
        selected: List[int] = []
        for idx, card in enumerate(self.items):
            is_selected = getattr(card, "is_selected", None)
            if callable(is_selected) and is_selected():
                selected.append(idx)
        return selected
