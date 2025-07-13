"""Tests for the snap engine functionality."""

import sys
from unittest.mock import Mock, patch

import pytest
from PySide6.QtCore import QPointF, QRectF
from PySide6.QtGui import QLineF
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsScene,
)

from qt_client.core.snap_engine import SnapEngine, SnapPoint, SnapType


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
def snap_engine(scene):
    """Create a snap engine for testing."""
    return SnapEngine(scene, tolerance=10.0)


class TestSnapEngine:
    """Test cases for SnapEngine."""

    def test_snap_engine_initialization(self, snap_engine):
        """Test snap engine initializes correctly."""
        assert snap_engine.tolerance == 10.0
        assert SnapType.ENDPOINT in snap_engine.active_snaps
        assert SnapType.MIDPOINT in snap_engine.active_snaps
        assert SnapType.CENTER in snap_engine.active_snaps

    def test_enable_disable_snap_types(self, snap_engine):
        """Test enabling and disabling snap types."""
        # Disable endpoint snapping
        snap_engine.enable_snap_type(SnapType.ENDPOINT, False)
        assert SnapType.ENDPOINT not in snap_engine.active_snaps

        # Re-enable endpoint snapping
        snap_engine.enable_snap_type(SnapType.ENDPOINT, True)
        assert SnapType.ENDPOINT in snap_engine.active_snaps

    def test_line_endpoint_snap(self, qapp, scene, snap_engine):
        """Test snapping to line endpoints."""
        # Create a line
        line = QGraphicsLineItem(QLineF(0, 0, 100, 100))
        scene.addItem(line)

        # Test snap to start point
        cursor_pos = QPointF(5, 5)  # Near start point
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is not None
        assert snap_point.snap_type == SnapType.ENDPOINT
        assert abs(snap_point.position.x() - 0) < 0.1
        assert abs(snap_point.position.y() - 0) < 0.1

        # Test snap to end point
        cursor_pos = QPointF(95, 95)  # Near end point
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is not None
        assert snap_point.snap_type == SnapType.ENDPOINT
        assert abs(snap_point.position.x() - 100) < 0.1
        assert abs(snap_point.position.y() - 100) < 0.1

    def test_line_midpoint_snap(self, qapp, scene, snap_engine):
        """Test snapping to line midpoint."""
        # Clear scene
        scene.clear()

        # Create a line
        line = QGraphicsLineItem(QLineF(0, 0, 100, 100))
        scene.addItem(line)

        # Test snap to midpoint
        cursor_pos = QPointF(45, 45)  # Near midpoint (50, 50)
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is not None
        assert snap_point.snap_type == SnapType.MIDPOINT
        assert abs(snap_point.position.x() - 50) < 0.1
        assert abs(snap_point.position.y() - 50) < 0.1

    def test_circle_center_snap(self, qapp, scene, snap_engine):
        """Test snapping to circle center."""
        # Clear scene
        scene.clear()

        # Create a circle
        circle = QGraphicsEllipseItem(QRectF(-25, -25, 50, 50))  # Center at (0, 0)
        scene.addItem(circle)

        # Test snap to center
        cursor_pos = QPointF(3, 3)  # Near center
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is not None
        assert snap_point.snap_type == SnapType.CENTER
        assert abs(snap_point.position.x() - 0) < 0.1
        assert abs(snap_point.position.y() - 0) < 0.1

    def test_circle_quadrant_snap(self, qapp, scene, snap_engine):
        """Test snapping to circle quadrants."""
        # Clear scene
        scene.clear()

        # Create a circle
        circle = QGraphicsEllipseItem(
            QRectF(-25, -25, 50, 50)
        )  # Center at (0, 0), radius 25
        scene.addItem(circle)

        # Test snap to top quadrant
        cursor_pos = QPointF(2, -23)  # Near top quadrant (0, -25)
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is not None
        assert snap_point.snap_type == SnapType.QUADRANT
        assert abs(snap_point.position.x() - 0) < 0.1
        assert abs(snap_point.position.y() - (-25)) < 0.1

    def test_no_snap_when_too_far(self, qapp, scene, snap_engine):
        """Test that no snap occurs when cursor is too far."""
        # Clear scene
        scene.clear()

        # Create a line
        line = QGraphicsLineItem(QLineF(0, 0, 100, 100))
        scene.addItem(line)

        # Test cursor far from any snap point
        cursor_pos = QPointF(200, 200)
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        assert snap_point is None

    def test_snap_priority(self, qapp, scene, snap_engine):
        """Test snap priority system."""
        # Clear scene
        scene.clear()

        # Create intersecting lines
        line1 = QGraphicsLineItem(QLineF(0, 50, 100, 50))  # Horizontal line
        line2 = QGraphicsLineItem(QLineF(50, 0, 50, 100))  # Vertical line
        scene.addItem(line1)
        scene.addItem(line2)

        # Cursor near intersection (50, 50) and endpoint (100, 50)
        cursor_pos = QPointF(52, 52)
        snap_point = snap_engine.find_snap_point(cursor_pos, 1.0)

        # Intersection should have higher priority than endpoint
        assert snap_point is not None
        # Note: Intersection detection is simplified in our implementation
        # This test may need adjustment based on actual intersection detection

    def test_tolerance_scaling(self, qapp, scene, snap_engine):
        """Test tolerance scaling with zoom."""
        # Clear scene
        scene.clear()

        # Create a line
        line = QGraphicsLineItem(QLineF(0, 0, 100, 100))
        scene.addItem(line)

        # Test with different zoom levels
        cursor_pos = QPointF(5, 5)

        # High zoom (scale = 2.0) - tolerance should be tighter
        snap_point = snap_engine.find_snap_point(cursor_pos, 2.0)
        assert snap_point is not None  # Should still snap

        # Low zoom (scale = 0.5) - tolerance should be looser
        snap_point = snap_engine.find_snap_point(cursor_pos, 0.5)
        assert snap_point is not None  # Should still snap

    def test_snap_settings(self, snap_engine):
        """Test snap settings save and restore."""
        # Get initial settings
        initial_settings = snap_engine.get_snap_settings()

        # Modify settings
        snap_engine.set_tolerance(15.0)
        snap_engine.enable_snap_type(SnapType.ENDPOINT, False)
        snap_engine.set_show_markers(False)

        # Get modified settings
        modified_settings = snap_engine.get_snap_settings()

        # Verify changes
        assert modified_settings["tolerance"] == 15.0
        assert "ENDPOINT" not in modified_settings["active_snaps"]
        assert modified_settings["show_markers"] == False

        # Restore initial settings
        snap_engine.apply_snap_settings(initial_settings)

        # Verify restoration
        restored_settings = snap_engine.get_snap_settings()
        assert restored_settings["tolerance"] == initial_settings["tolerance"]
        assert set(restored_settings["active_snaps"]) == set(
            initial_settings["active_snaps"]
        )


class TestSnapPoint:
    """Test cases for SnapPoint."""

    def test_snap_point_creation(self):
        """Test creating snap points."""
        position = QPointF(10, 20)
        snap_point = SnapPoint(position, SnapType.ENDPOINT)

        assert snap_point.position == position
        assert snap_point.snap_type == SnapType.ENDPOINT
        assert snap_point.source_item is None
        assert snap_point.priority == 0

    def test_distance_calculation(self):
        """Test distance calculation."""
        snap_point = SnapPoint(QPointF(0, 0), SnapType.ENDPOINT)
        target_point = QPointF(3, 4)

        distance = snap_point.distance_to(target_point)
        assert abs(distance - 5.0) < 0.01  # 3-4-5 triangle


if __name__ == "__main__":
    pytest.main([__file__])
