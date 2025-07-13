"""
Tests for angular and radial dimension tools.
"""

import math
import pytest
from unittest.mock import MagicMock, patch
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QGraphicsScene, QGraphicsLineItem

from qt_client.graphics.tools.dimension_tool import (
    AngularDimensionTool,
    RadialDimensionTool,
    DiameterDimensionTool,
    ArcLengthDimensionTool
)


@pytest.fixture
def app():
    """Create QApplication instance for testing."""
    return QApplication.instance() or QApplication([])


@pytest.fixture
def scene():
    """Create QGraphicsScene for testing."""
    return QGraphicsScene()


@pytest.fixture
def mock_services():
    """Create mock services for testing."""
    api_client = MagicMock()
    command_manager = MagicMock()
    snap_engine = MagicMock()
    selection_manager = MagicMock()
    
    # Configure snap engine to return unsnapped points
    snap_engine.snap_point.return_value = MagicMock(snapped=False, point=QPointF(0, 0))
    
    return api_client, command_manager, snap_engine, selection_manager


class TestAngularDimensionTool:
    """Test angular dimension tool functionality."""

    def test_tool_initialization(self, app, scene, mock_services):
        """Test angular dimension tool initialization."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        assert tool.get_tool_name() == "Angular Dimension"
        assert tool.state == "waiting_for_first_line"
        assert tool.first_line is None
        assert tool.second_line is None

    def test_tool_activation(self, app, scene, mock_services):
        """Test angular dimension tool activation."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Mock the view property
        tool.view = MagicMock()
        
        result = tool.activate()
        assert result is True
        assert tool.state == "waiting_for_first_line"

    def test_angle_calculation(self, app, scene, mock_services):
        """Test angle calculation between two lines."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Create two lines forming a 90-degree angle
        line1 = QGraphicsLineItem(0, 0, 10, 0)  # Horizontal line
        line2 = QGraphicsLineItem(0, 0, 0, 10)  # Vertical line
        
        angle = tool._calculate_angle_between_lines(line1, line2)
        
        # Should be 90 degrees (allowing for floating point precision)
        assert abs(angle - 90.0) < 0.001

    def test_intersection_calculation(self, app, scene, mock_services):
        """Test intersection point calculation."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Create two intersecting lines
        line1 = QGraphicsLineItem(0, 0, 10, 0)   # Horizontal line
        line2 = QGraphicsLineItem(5, -5, 5, 5)   # Vertical line through (5,0)
        
        intersection = tool._find_intersection_point(line1, line2)
        
        assert intersection is not None
        assert abs(intersection.x() - 5.0) < 0.001
        assert abs(intersection.y() - 0.0) < 0.001

    def test_parallel_lines_intersection(self, app, scene, mock_services):
        """Test that parallel lines return no intersection."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Create two parallel horizontal lines
        line1 = QGraphicsLineItem(0, 0, 10, 0)
        line2 = QGraphicsLineItem(0, 5, 10, 5)
        
        intersection = tool._find_intersection_point(line1, line2)
        
        assert intersection is None

    def test_status_text_changes(self, app, scene, mock_services):
        """Test that status text changes with tool state."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Initial state
        assert "first line" in tool.get_status_text().lower()
        
        # After selecting first line
        tool.state = "waiting_for_second_line"
        assert "second line" in tool.get_status_text().lower()
        
        # After selecting second line
        tool.state = "waiting_for_arc_point"
        assert "position" in tool.get_status_text().lower()


class TestRadialDimensionTool:
    """Test radial dimension tool functionality."""

    def test_tool_initialization(self, app, scene, mock_services):
        """Test radial dimension tool initialization."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = RadialDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        assert tool.get_tool_name() == "Radius Dimension"
        assert tool.state == "waiting_for_entity"
        assert tool.selected_entity is None

    def test_entity_center_radius_fallback(self, app, scene, mock_services):
        """Test fallback values for entity center and radius."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = RadialDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Test with entity that doesn't have center/radius properties
        mock_entity = MagicMock()
        del mock_entity.center  # Remove center attribute
        del mock_entity.radius  # Remove radius attribute
        
        center, radius = tool._get_entity_center_and_radius(mock_entity)
        
        # Should return fallback values
        assert center == QPointF(0, 0)
        assert radius == 10.0

    def test_entity_center_radius_with_properties(self, app, scene, mock_services):
        """Test getting center and radius from entity with properties."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = RadialDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Create mock entity with center and radius
        mock_entity = MagicMock()
        mock_entity.center = QPointF(5, 10)
        mock_entity.radius = 15.0
        
        center, radius = tool._get_entity_center_and_radius(mock_entity)
        
        assert center == QPointF(5, 10)
        assert radius == 15.0


class TestDiameterDimensionTool:
    """Test diameter dimension tool functionality."""

    def test_tool_initialization(self, app, scene, mock_services):
        """Test diameter dimension tool initialization."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = DiameterDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        assert tool.get_tool_name() == "Diameter Dimension"
        assert tool.state == "waiting_for_entity"

    def test_circle_center_radius_calculation(self, app, scene, mock_services):
        """Test diameter calculation from circle center and radius."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = DiameterDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Mock circle entity
        mock_circle = MagicMock()
        mock_circle.center = QPointF(0, 0)
        mock_circle.radius = 7.5
        
        center, radius = tool._get_circle_center_and_radius(mock_circle)
        
        assert center == QPointF(0, 0)
        assert radius == 7.5
        # Diameter would be 2 * radius = 15.0


class TestArcLengthDimensionTool:
    """Test arc length dimension tool functionality."""

    def test_tool_initialization(self, app, scene, mock_services):
        """Test arc length dimension tool initialization."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = ArcLengthDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        assert tool.get_tool_name() == "Arc Length Dimension"
        assert tool.state == "waiting_for_arc"

    def test_arc_length_calculation(self, app, scene, mock_services):
        """Test arc length calculation."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = ArcLengthDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Test quarter circle: radius=10, angle=90° = π/2 radians
        # Arc length = radius * angle = 10 * π/2 ≈ 15.708
        radius = 10.0
        start_angle = 0.0    # degrees
        end_angle = 90.0     # degrees
        
        arc_length = tool._calculate_arc_length(radius, start_angle, end_angle)
        expected_length = radius * math.pi / 2
        
        assert abs(arc_length - expected_length) < 0.001

    def test_arc_length_wraparound(self, app, scene, mock_services):
        """Test arc length calculation with angle wraparound."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = ArcLengthDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Test arc that wraps around: 350° to 30° = 40° total
        radius = 5.0
        start_angle = 350.0  # degrees
        end_angle = 30.0     # degrees (wraps around)
        
        arc_length = tool._calculate_arc_length(radius, start_angle, end_angle)
        expected_angle_radians = math.radians(40.0)  # 40° total span
        expected_length = radius * expected_angle_radians
        
        # Allow for some tolerance due to wraparound calculation
        assert abs(arc_length - expected_length) < 0.1

    def test_arc_properties_fallback(self, app, scene, mock_services):
        """Test fallback values for arc properties."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = ArcLengthDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Test with entity missing properties
        mock_arc = MagicMock()
        del mock_arc.center
        del mock_arc.radius
        
        center, radius, start_angle, end_angle = tool._get_arc_properties(mock_arc)
        
        # Should return fallback values
        assert center == QPointF(0, 0)
        assert radius == 10.0
        assert start_angle == 0.0
        assert end_angle == 90.0


class TestDimensionToolsIntegration:
    """Test integration between dimension tools."""

    def test_tool_deactivation_cleanup(self, app, scene, mock_services):
        """Test that tools clean up properly when deactivated."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tools = [
            AngularDimensionTool(scene, api_client, command_manager, snap_engine, selection_manager),
            RadialDimensionTool(scene, api_client, command_manager, snap_engine, selection_manager),
            DiameterDimensionTool(scene, api_client, command_manager, snap_engine, selection_manager),
            ArcLengthDimensionTool(scene, api_client, command_manager, snap_engine, selection_manager)
        ]
        
        for tool in tools:
            # Mock the view property
            tool.view = MagicMock()
            
            # Activate and add some preview items
            tool.activate()
            tool.preview_items = [MagicMock(), MagicMock()]
            
            # Deactivate
            tool.deactivate()
            
            # Should have cleared preview items
            assert len(tool.preview_items) == 0

    def test_escape_key_cancellation(self, app, scene, mock_services):
        """Test that Escape key cancels dimension operations."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Mock the view and key event
        tool.view = MagicMock()
        
        # Simulate some progress in dimension creation
        tool.state = "waiting_for_second_line"
        tool.first_line = MagicMock()
        
        # Create escape key event
        key_event = MagicMock()
        key_event.key.return_value = Qt.Key.Key_Escape
        
        # Handle escape key
        result = tool.handle_key_press(key_event)
        
        assert result is True
        assert tool.state == "waiting_for_first_line"
        assert tool.first_line is None

    @patch('asyncio.create_task')
    def test_dimension_creation_async(self, mock_create_task, app, scene, mock_services):
        """Test that dimension creation is handled asynchronously."""
        api_client, command_manager, snap_engine, selection_manager = mock_services
        
        tool = AngularDimensionTool(
            scene, api_client, command_manager, snap_engine, selection_manager
        )
        
        # Set up tool state for dimension creation
        tool.state = "waiting_for_arc_point"
        tool.first_line = QGraphicsLineItem(0, 0, 10, 0)
        tool.second_line = QGraphicsLineItem(0, 0, 0, 10)
        
        # Mock mouse event
        mouse_event = MagicMock()
        tool.scene_pos_from_event = MagicMock(return_value=QPointF(5, 5))
        
        # Handle mouse press (should trigger async dimension creation)
        tool.handle_mouse_press(mouse_event)
        
        # Verify that async task was created
        mock_create_task.assert_called_once()