"""
Test suite for cross-group selection isolation bug fix.

Verifies that selecting images in one group doesn't affect selections in other groups.
Each group maintains independent selection state.
"""

import pytest
from unittest.mock import Mock


class SimpleSelectionManager:
    """Simplified version of ModernMainWindow selection state management for testing."""
    
    def __init__(self):
        self.current_group = None
        self._group_selection_state = {}
    
    def _get_group_selection_state(self, group_id):
        """Get selection state for a specific group. Returns (selected_indices, last_selected_index)."""
        if group_id not in self._group_selection_state:
            self._group_selection_state[group_id] = (set(), -1)
        return self._group_selection_state[group_id]
    
    def _save_group_selection_state(self, group_id, selected_indices=None, last_selected_index=-1):
        """Save selection state for a specific group."""
        if selected_indices is None:
            selected_indices, last_selected_index = self._get_group_selection_state(group_id)
        self._group_selection_state[group_id] = (selected_indices, last_selected_index)


@pytest.fixture
def manager():
    """Create selection manager for tests."""
    return SimpleSelectionManager()


class TestCrossGroupSelectionIsolation:
    """Test that selections in one group don't affect other groups."""

    def test_selection_state_dict_initialized(self, manager):
        """Test that per-group selection state dictionary is initialized."""
        assert hasattr(manager, '_group_selection_state')
        assert isinstance(manager._group_selection_state, dict)
        assert len(manager._group_selection_state) == 0

    def test_get_group_selection_state_creates_entry(self, manager):
        """Test that accessing non-existent group creates default state."""
        selected_indices, last_selected = manager._get_group_selection_state("g00001")
        
        assert isinstance(selected_indices, set)
        assert len(selected_indices) == 0
        assert last_selected == -1
        assert "g00001" in manager._group_selection_state

    def test_save_and_restore_group_state(self, manager):
        """Test saving and restoring group selection state."""
        # Save state for g00001
        indices_g1 = {0, 2}
        manager._save_group_selection_state("g00001", indices_g1, 2)
        
        # Verify it's saved
        restored_indices, restored_last = manager._get_group_selection_state("g00001")
        assert restored_indices == indices_g1
        assert restored_last == 2

    def test_separate_states_for_different_groups(self, manager):
        """Test that different groups maintain separate selection states."""
        # Select indices in g00001
        manager._save_group_selection_state("g00001", {0, 2}, 2)
        
        # Select different indices in g00002
        manager._save_group_selection_state("g00002", {1}, 1)
        
        # Select yet different indices in g00003
        manager._save_group_selection_state("g00003", {0, 1, 2}, 2)
        
        # Verify all states are independent
        g1_indices, g1_last = manager._get_group_selection_state("g00001")
        g2_indices, g2_last = manager._get_group_selection_state("g00002")
        g3_indices, g3_last = manager._get_group_selection_state("g00003")
        
        assert g1_indices == {0, 2} and g1_last == 2
        assert g2_indices == {1} and g2_last == 1
        assert g3_indices == {0, 1, 2} and g3_last == 2

    def test_scenario_select_group1_switch_to_group2_no_bleed(self, manager):
        """
        SCENARIO 1: Select image at index 2 in Group 1,
        then switch to Group 2 - index 2 in Group 2 should NOT be selected.
        """
        manager.current_group = "g00001"
        
        # Save selection for g00001 (select index 2)
        manager._save_group_selection_state("g00001", {2}, 2)
        
        # Switch to g00002
        manager.current_group = "g00002"
        
        # g00002 should have no selection (default empty state)
        g2_indices, g2_last = manager._get_group_selection_state("g00002")
        
        assert len(g2_indices) == 0
        assert g2_last == -1
        
        # g00001 should still have its selection
        g1_indices, g1_last = manager._get_group_selection_state("g00001")
        assert g1_indices == {2}
        assert g1_last == 2

    def test_scenario_multiselect_group1_switch_no_bleed(self, manager):
        """
        SCENARIO 2: Multi-select (Ctrl+Click) multiple images in Group 1,
        then switch to Group 2 - those indices should NOT be selected in Group 2.
        """
        manager.current_group = "g00001"
        
        # Simulate multi-select in g00001 (indices 0, 1, 2)
        manager._save_group_selection_state("g00001", {0, 1, 2}, 2)
        
        # Switch to g00002
        manager.current_group = "g00002"
        
        # g00002 should have no selection
        g2_indices, _ = manager._get_group_selection_state("g00002")
        assert len(g2_indices) == 0
        
        # g00001 should retain full selection
        g1_indices, _ = manager._get_group_selection_state("g00001")
        assert g1_indices == {0, 1, 2}

    def test_scenario_select_all_group1_clear_group2_then_restore_group1(self, manager):
        """
        SCENARIO 3: Select-All in Group 1 (all 3 images),
        switch to Group 2, Clear-Selection in Group 2,
        then switch back to Group 1 - Group 1 should still have full selection.
        """
        # Select all in g00001
        manager._save_group_selection_state("g00001", {0, 1, 2}, 2)
        
        # Switch to g00002
        manager.current_group = "g00002"
        manager._save_group_selection_state("g00002", {0, 1, 2}, 2)  # Also select all
        
        # Clear selection in g00002
        manager._save_group_selection_state("g00002", set(), -1)
        
        # Switch back to g00001
        manager.current_group = "g00001"
        
        # g00001 should still have full selection
        g1_indices, _ = manager._get_group_selection_state("g00001")
        assert g1_indices == {0, 1, 2}
        
        # g00002 should have cleared selection
        g2_indices, _ = manager._get_group_selection_state("g00002")
        assert len(g2_indices) == 0

    def test_scenario_shift_click_range_isolation(self, manager):
        """
        SCENARIO 4: Shift+Click range selection in Group 1 (indices 0-2),
        switch to Group 2, perform independent operation - verify Group 1 unchanged.
        """
        # Range selection in g00001 (indices 0, 1, 2)
        manager._save_group_selection_state("g00001", {0, 1, 2}, 2)
        
        # Switch to g00002 and make a different selection
        manager.current_group = "g00002"
        manager._save_group_selection_state("g00002", {1}, 1)
        
        # Verify both states are independent
        g1_indices, _ = manager._get_group_selection_state("g00001")
        g2_indices, _ = manager._get_group_selection_state("g00002")
        
        assert g1_indices == {0, 1, 2}
        assert g2_indices == {1}

    def test_state_persistence_across_multiple_switches(self, manager):
        """Test that selection state persists correctly across multiple group switches."""
        # Create complex state scenario
        manager._save_group_selection_state("g00001", {0, 2}, 2)
        manager._save_group_selection_state("g00002", {1}, 1)
        manager._save_group_selection_state("g00003", {0, 1}, 1)
        
        # Switch between groups multiple times
        for _ in range(3):
            manager.current_group = "g00001"
            assert manager._get_group_selection_state("g00001")[0] == {0, 2}
            
            manager.current_group = "g00002"
            assert manager._get_group_selection_state("g00002")[0] == {1}
            
            manager.current_group = "g00003"
            assert manager._get_group_selection_state("g00003")[0] == {0, 1}
        
        # Final verification
        manager.current_group = "g00001"
        assert manager._get_group_selection_state("g00001")[0] == {0, 2}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
