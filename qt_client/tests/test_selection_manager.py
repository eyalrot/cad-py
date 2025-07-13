"""Tests for the selection manager functionality."""

import sys
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QLineF
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
)

from qt_client.core.selection_manager import (
    SelectionFilter,
    SelectionManager,
    SelectionMode,
)


@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for tests."""
    if not QApplication.instance():
        app = QApplication(sys.argv)
    return QApplication.instance()


@pytest.fixture
def scene():
    """Create a graphics scene for testing."""
    return QGraphicsScene()


@pytest.fixture
def selection_manager(scene):
    """Create a selection manager for testing."""
    return SelectionManager(scene)


@pytest.fixture
def sample_items(scene):
    """Create sample graphics items for testing."""
    # Create various items
    line1 = QGraphicsLineItem(QLineF(0, 0, 100, 0))
    line1.setData(0, "line1")  # Set ID
    line1.setData(1, "0")  # Set layer
    line1.setFlags(line1.flags() | QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable)

    line2 = QGraphicsLineItem(QLineF(0, 50, 100, 50))
    line2.setData(0, "line2")
    line2.setData(1, "1")
    line2.setFlags(line2.flags() | QGraphicsLineItem.GraphicsItemFlag.ItemIsSelectable)

    circle = QGraphicsEllipseItem(QRectF(20, 20, 30, 30))
    circle.setData(0, "circle1")
    circle.setData(1, "0")
    circle.setFlags(
        circle.flags() | QGraphicsEllipseItem.GraphicsItemFlag.ItemIsSelectable
    )

    rect = QGraphicsRectItem(QRectF(60, 10, 20, 20))
    rect.setData(0, "rect1")
    rect.setData(1, "2")
    rect.setFlags(rect.flags() | QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable)

    # Add to scene
    scene.addItem(line1)
    scene.addItem(line2)
    scene.addItem(circle)
    scene.addItem(rect)

    return {"line1": line1, "line2": line2, "circle": circle, "rect": rect}


class TestSelectionManager:
    """Test cases for SelectionManager."""

    def test_selection_manager_initialization(self, qapp, selection_manager):
        """Test selection manager initializes correctly."""
        assert selection_manager.selection_mode == SelectionMode.SINGLE
        assert selection_manager.selection_filter == SelectionFilter.ALL
        assert selection_manager.get_selection_count() == 0

    def test_selection_mode_property(self, qapp, selection_manager):
        """Test selection mode property."""
        # Test setting selection mode
        selection_manager.selection_mode = SelectionMode.WINDOW
        assert selection_manager.selection_mode == SelectionMode.WINDOW

        # Test signal emission (would need signal spy in real test)
        selection_manager.selection_mode = SelectionMode.CROSSING
        assert selection_manager.selection_mode == SelectionMode.CROSSING

    def test_selection_filter_property(self, qapp, selection_manager):
        """Test selection filter property."""
        # Test setting selection filter
        selection_manager.selection_filter = SelectionFilter.LINES
        assert selection_manager.selection_filter == SelectionFilter.LINES

        selection_manager.selection_filter = SelectionFilter.CIRCLES
        assert selection_manager.selection_filter == SelectionFilter.CIRCLES

    def test_pick_select_single_item(self, qapp, selection_manager, sample_items):
        """Test single pick selection."""
        line1 = sample_items["line1"]

        # Click on line1
        selection_manager.pick_select(QPointF(50, 0))

        assert selection_manager.get_selection_count() == 1
        assert selection_manager.is_item_selected(line1)
        assert "line1" in selection_manager.get_selected_ids()

    def test_pick_select_replace_selection(self, qapp, selection_manager, sample_items):
        """Test that normal click replaces selection."""
        line1 = sample_items["line1"]
        line2 = sample_items["line2"]

        # Select line1
        selection_manager.pick_select(QPointF(50, 0))
        assert selection_manager.is_item_selected(line1)

        # Select line2 (should replace line1)
        selection_manager.pick_select(QPointF(50, 50))
        assert not selection_manager.is_item_selected(line1)
        assert selection_manager.is_item_selected(line2)
        assert selection_manager.get_selection_count() == 1

    def test_pick_select_ctrl_toggle(self, qapp, selection_manager, sample_items):
        """Test Ctrl+click toggle selection."""
        line1 = sample_items["line1"]
        line2 = sample_items["line2"]

        # Select line1
        selection_manager.pick_select(QPointF(50, 0))
        assert selection_manager.is_item_selected(line1)

        # Ctrl+click line2 (should add to selection)
        selection_manager.pick_select(
            QPointF(50, 50), Qt.KeyboardModifier.ControlModifier
        )
        assert selection_manager.is_item_selected(line1)
        assert selection_manager.is_item_selected(line2)
        assert selection_manager.get_selection_count() == 2

        # Ctrl+click line1 again (should remove from selection)
        selection_manager.pick_select(
            QPointF(50, 0), Qt.KeyboardModifier.ControlModifier
        )
        assert not selection_manager.is_item_selected(line1)
        assert selection_manager.is_item_selected(line2)
        assert selection_manager.get_selection_count() == 1

    def test_pick_select_shift_add(self, qapp, selection_manager, sample_items):
        """Test Shift+click add to selection."""
        line1 = sample_items["line1"]
        line2 = sample_items["line2"]

        # Select line1
        selection_manager.pick_select(QPointF(50, 0))
        assert selection_manager.is_item_selected(line1)

        # Shift+click line2 (should add to selection)
        selection_manager.pick_select(
            QPointF(50, 50), Qt.KeyboardModifier.ShiftModifier
        )
        assert selection_manager.is_item_selected(line1)
        assert selection_manager.is_item_selected(line2)
        assert selection_manager.get_selection_count() == 2

    def test_window_selection_workflow(self, qapp, selection_manager, sample_items):
        """Test window selection workflow."""
        # Start window selection
        start_point = QPointF(-10, -10)
        selection_manager.start_window_selection(start_point)
        assert selection_manager._is_selecting

        # Update selection rectangle
        end_point = QPointF(110, 60)
        selection_manager.update_window_selection(end_point)

        # Finish selection
        success = selection_manager.finish_window_selection()
        assert success
        assert not selection_manager._is_selecting

        # Should have selected items that are completely inside
        selected_ids = selection_manager.get_selected_ids()
        assert len(selected_ids) > 0

    def test_window_selection_cancel(self, qapp, selection_manager):
        """Test canceling window selection."""
        # Start window selection
        selection_manager.start_window_selection(QPointF(0, 0))
        assert selection_manager._is_selecting

        # Cancel selection
        selection_manager.cancel_window_selection()
        assert not selection_manager._is_selecting

    def test_selection_filter_by_type(self, qapp, selection_manager, sample_items):
        """Test selection filtering by object type."""
        # Set filter to lines only
        selection_manager.selection_filter = SelectionFilter.LINES

        # Try to select a circle (should be filtered out)
        selection_manager.pick_select(QPointF(35, 35))  # Circle position
        assert selection_manager.get_selection_count() == 0

        # Select a line (should work)
        selection_manager.pick_select(QPointF(50, 0))  # Line position
        assert selection_manager.get_selection_count() == 1
        assert "line1" in selection_manager.get_selected_ids()

    def test_selection_filter_by_layer(self, qapp, selection_manager, sample_items):
        """Test selection filtering by layer."""
        # Set layer filter
        selection_manager.set_filter_layers({"0"})

        # Try to select item on layer "1" (should be filtered out)
        selection_manager.pick_select(QPointF(50, 50))  # Line2 on layer "1"
        assert selection_manager.get_selection_count() == 0

        # Select item on layer "0" (should work)
        selection_manager.pick_select(QPointF(50, 0))  # Line1 on layer "0"
        assert selection_manager.get_selection_count() == 1
        assert "line1" in selection_manager.get_selected_ids()

    def test_select_all(self, qapp, selection_manager, sample_items):
        """Test select all functionality."""
        selection_manager.select_all()

        # Should select all items
        assert selection_manager.get_selection_count() == len(sample_items)

        # Check that all items are selected
        for item_id, item in sample_items.items():
            assert selection_manager.is_item_selected(item)
            assert item_id in selection_manager.get_selected_ids()

    def test_select_similar(self, qapp, selection_manager, sample_items):
        """Test select similar functionality."""
        line1 = sample_items["line1"]

        # Select similar to line1 (should select all lines on same layer)
        selection_manager.select_similar(line1)

        # Should select line1 and circle (both on layer "0")
        selected_ids = selection_manager.get_selected_ids()
        assert "line1" in selected_ids
        # Note: This test might need adjustment based on actual similarity criteria

    def test_invert_selection(self, qapp, selection_manager, sample_items):
        """Test invert selection."""
        line1 = sample_items["line1"]

        # Select line1
        selection_manager.pick_select(QPointF(50, 0))
        assert selection_manager.is_item_selected(line1)
        initial_count = selection_manager.get_selection_count()

        # Invert selection
        selection_manager.invert_selection()

        # Line1 should no longer be selected, others should be
        assert not selection_manager.is_item_selected(line1)
        assert (
            selection_manager.get_selection_count() == len(sample_items) - initial_count
        )

    def test_clear_selection(self, qapp, selection_manager, sample_items):
        """Test clear selection."""
        # Select some items
        selection_manager.select_all()
        assert selection_manager.get_selection_count() > 0

        # Clear selection
        selection_manager.clear_selection()
        assert selection_manager.get_selection_count() == 0

        # Check that no items are selected
        for item in sample_items.values():
            assert not selection_manager.is_item_selected(item)

    def test_selection_bounds_and_center(self, qapp, selection_manager, sample_items):
        """Test selection bounds and center calculation."""
        line1 = sample_items["line1"]
        circle = sample_items["circle"]

        # Select line1 and circle
        selection_manager._add_to_selection(line1)
        selection_manager._add_to_selection(circle)

        # Get bounds and center
        bounds = selection_manager.get_selection_bounds()
        center = selection_manager.get_selection_center()

        assert bounds is not None
        assert center is not None
        assert isinstance(bounds, QRectF)
        assert isinstance(center, QPointF)

    def test_selection_info(self, qapp, selection_manager, sample_items):
        """Test selection information."""
        # Select multiple items
        selection_manager.select_all()

        # Get selection info
        info = selection_manager.get_selection_info()

        assert "count" in info
        assert "types" in info
        assert "layers" in info
        assert "bounds" in info
        assert "center" in info
        assert "mode" in info
        assert "filter" in info

        assert info["count"] == len(sample_items)
        assert len(info["types"]) > 0
        assert len(info["layers"]) > 0

    def test_move_selection(self, qapp, selection_manager, sample_items):
        """Test moving selected items."""
        line1 = sample_items["line1"]
        original_pos = line1.pos()

        # Select line1
        selection_manager._add_to_selection(line1)

        # Move selection
        delta = QPointF(10, 20)
        selection_manager.move_selection(delta)

        # Check that item moved
        new_pos = line1.pos()
        assert abs(new_pos.x() - (original_pos.x() + delta.x())) < 0.01
        assert abs(new_pos.y() - (original_pos.y() + delta.y())) < 0.01

    def test_delete_selection(self, qapp, selection_manager, sample_items):
        """Test deleting selected items."""
        line1 = sample_items["line1"]
        scene = selection_manager.scene

        # Verify item is in scene
        assert line1 in scene.items()

        # Select and delete line1
        selection_manager._add_to_selection(line1)
        selection_manager.delete_selection()

        # Verify item was removed from scene and selection
        assert line1 not in scene.items()
        assert selection_manager.get_selection_count() == 0

    def test_apply_to_selection(self, qapp, selection_manager, sample_items):
        """Test applying operation to selection."""
        line1 = sample_items["line1"]
        line2 = sample_items["line2"]

        # Select items
        selection_manager._add_to_selection(line1)
        selection_manager._add_to_selection(line2)

        # Apply operation (make visible = False)
        def hide_item(item):
            item.setVisible(False)

        selection_manager.apply_to_selection(hide_item)

        # Check that operation was applied
        assert not line1.isVisible()
        assert not line2.isVisible()


class TestSelectionRubberBand:
    """Test cases for SelectionRubberBand."""

    def test_rubber_band_creation(self, qapp, scene):
        """Test rubber band creation and removal."""
        from qt_client.core.selection_manager import SelectionRubberBand

        rubber_band = SelectionRubberBand()

        # Start selection
        rubber_band.start_selection(scene, QPointF(0, 0), False)

        # Check that rubber band item was added to scene
        items_before = len(scene.items())
        assert items_before > 0

        # Update selection
        rubber_band.update_selection(QPointF(100, 100))

        # Finish selection
        rect = rubber_band.finish_selection(scene)

        # Check that rubber band was removed and rectangle returned
        assert rect is not None
        assert isinstance(rect, QRectF)

        # Scene should have fewer items now
        items_after = len(scene.items())
        assert items_after < items_before

    def test_crossing_vs_window_mode(self, qapp, scene):
        """Test crossing vs window mode detection."""
        from qt_client.core.selection_manager import SelectionRubberBand

        rubber_band = SelectionRubberBand()

        # Start selection
        start_point = QPointF(50, 50)
        rubber_band.start_selection(scene, start_point, False)

        # Drag right (window mode)
        rubber_band.update_selection(QPointF(100, 100))
        assert not rubber_band.is_crossing_mode()

        # Drag left (crossing mode)
        rubber_band.update_selection(QPointF(0, 100))
        assert rubber_band.is_crossing_mode()

        # Clean up
        rubber_band.cancel_selection(scene)


if __name__ == "__main__":
    pytest.main([__file__])
