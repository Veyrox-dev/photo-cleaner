from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence


@dataclass(frozen=True)
class SelectionUiState:
    count_text: str
    compare_enabled: bool
    compare_text: str
    compare_visible: bool
    action_buttons_visible: bool


class SelectionWorkflowController:
    """Controller for selection-state logic used by the modern UI."""

    def get_selected_indices(
        self,
        current_group: str | None,
        files_in_group_count: int,
        get_group_selection_state: Callable[[str], tuple[set[int], int]],
    ) -> list[int]:
        """Return bounded, sorted indices for the current group."""
        if not current_group:
            return []
        selected_indices, _ = get_group_selection_state(current_group)
        return [i for i in sorted(selected_indices) if 0 <= i < files_in_group_count]

    def build_selection_ui_state(self, selected_count: int, t_func: Callable[[str], str]) -> SelectionUiState:
        """Build a UI state snapshot from selected item count."""
        if selected_count == 0:
            return SelectionUiState(
                count_text=t_func("selection_none_bold"),
                compare_enabled=False,
                compare_text=t_func("compare_select_two"),
                compare_visible=False,
                action_buttons_visible=False,
            )

        if selected_count == 1:
            return SelectionUiState(
                count_text=t_func("selection_one_image"),
                compare_enabled=False,
                compare_text=t_func("compare_need_two"),
                compare_visible=False,
                action_buttons_visible=True,
            )

        if selected_count == 2:
            return SelectionUiState(
                count_text=t_func("selection_two_images"),
                compare_enabled=True,
                compare_text=t_func("compare_side_by_side"),
                compare_visible=True,
                action_buttons_visible=True,
            )

        return SelectionUiState(
            count_text=t_func("selection_n_images").format(count=selected_count),
            compare_enabled=False,
            compare_text=t_func("compare_select_exactly_two"),
            compare_visible=False,
            action_buttons_visible=True,
        )

    def get_comparison_pair_indices(
        self,
        current_group: str | None,
        files_in_group_count: int,
        get_group_selection_state: Callable[[str], tuple[set[int], int]],
    ) -> tuple[int, int] | None:
        """Return two valid indices for comparison, else None."""
        indices = self.get_selected_indices(current_group, files_in_group_count, get_group_selection_state)
        if len(indices) != 2:
            return None
        return indices[0], indices[1]

    def collect_valid_existing_paths(self, indices: Sequence[int], files_in_group: Sequence) -> list[Path]:
        """Collect existing file paths from selected indices."""
        paths: list[Path] = []
        for idx in indices:
            if idx < 0 or idx >= len(files_in_group):
                continue
            file_path = getattr(files_in_group[idx], "path", None)
            if isinstance(file_path, Path) and file_path.exists():
                paths.append(file_path)
        return paths
