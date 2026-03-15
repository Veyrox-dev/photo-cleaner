from __future__ import annotations

from pathlib import Path

from photo_cleaner.ui.workflows.selection_workflow_controller import SelectionWorkflowController


class _FileRowStub:
    def __init__(self, path: Path) -> None:
        self.path = path


def test_get_selected_indices_filters_out_of_range() -> None:
    controller = SelectionWorkflowController()

    def _state(_group_id: str):
        return {-1, 0, 2, 99}, -1

    indices = controller.get_selected_indices("g1", 3, _state)
    assert indices == [0, 2]


def test_build_selection_ui_state_two_selected_enables_compare() -> None:
    controller = SelectionWorkflowController()
    t_func = lambda key: key

    state = controller.build_selection_ui_state(2, t_func)

    assert state.compare_enabled is True
    assert state.compare_visible is True
    assert state.compare_text == "compare_side_by_side"
    assert state.action_buttons_visible is True


def test_get_comparison_pair_indices_requires_exactly_two() -> None:
    controller = SelectionWorkflowController()

    def _state(_group_id: str):
        return {0, 1, 2}, -1

    assert controller.get_comparison_pair_indices("g1", 5, _state) is None


def test_collect_valid_existing_paths_only_returns_existing(tmp_path: Path) -> None:
    controller = SelectionWorkflowController()

    existing = tmp_path / "exists.jpg"
    existing.write_text("x", encoding="utf-8")
    missing = tmp_path / "missing.jpg"

    rows = [_FileRowStub(existing), _FileRowStub(missing)]
    paths = controller.collect_valid_existing_paths([0, 1, 999], rows)

    assert paths == [existing]
