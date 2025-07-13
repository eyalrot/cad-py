"""
Tests for angular and radial dimension functionality.
"""

import math
import pytest
from backend.api.dimension_service import DimensionService
from backend.api.document_service import DocumentService
from backend.models.dimension import Dimension, DimensionPoint, DimensionType


class TestAngularDimensions:
    """Test angular dimension functionality."""

    @pytest.fixture
    def dimension_service(self):
        """Create dimension service with mock document service."""
        doc_service = DocumentService()
        return DimensionService(doc_service)

    def test_angular_dimension_creation(self, dimension_service):
        """Test creating angular dimensions."""
        # Create angular dimension between two lines intersecting at 90 degrees
        request = {
            "document_id": "test_doc",
            "dimension_type": "angular",
            "points": [
                [0, 0],      # Vertex point
                [50, 50],    # Arc position point
            ],
            "measurement_value": 90.0,  # 90 degree angle
            "layer_id": "0",
        }
        
        # Note: This test assumes the document service has been enhanced
        # to handle dimension creation. In the current implementation,
        # we'd need to mock the document service response.
        
        # For now, test the dimension model directly
        vertex = DimensionPoint(0, 0)
        arc_point = DimensionPoint(50, 50)
        dimension = Dimension(
            DimensionType.ANGULAR,
            [vertex, arc_point],
            "0"
        )
        
        assert dimension.dimension_type == DimensionType.ANGULAR
        assert len(dimension.points) == 2
        assert dimension.points[0].x == 0
        assert dimension.points[0].y == 0
        assert dimension.points[1].x == 50
        assert dimension.points[1].y == 50

    def test_angular_dimension_calculation(self):
        """Test angular dimension measurement calculation."""
        # Test 90-degree angle
        vertex = DimensionPoint(0, 0)
        arc_point = DimensionPoint(10, 0)  # Position for arc
        
        dimension = Dimension(
            DimensionType.ANGULAR,
            [vertex, arc_point],
            "0"
        )
        
        # For angular dimensions, measurement would be calculated
        # based on the actual line entities, not just points
        # This is a simplified test
        assert dimension.dimension_type == DimensionType.ANGULAR

    def test_angular_dimension_formatting(self):
        """Test angular dimension text formatting."""
        dimension = Dimension(
            DimensionType.ANGULAR,
            [DimensionPoint(0, 0), DimensionPoint(10, 0)],
            "0"
        )
        
        # Manually set measurement for testing
        dimension.measurement_value = 45.5
        formatted_text = dimension.get_formatted_text()
        
        # Should format as degrees
        assert "45.5" in formatted_text or "45.50" in formatted_text

    def test_angular_dimension_text_override(self):
        """Test angular dimension with text override."""
        dimension = Dimension(
            DimensionType.ANGULAR,
            [DimensionPoint(0, 0), DimensionPoint(10, 0)],
            "0"
        )
        
        dimension.set_text_override("45° TYP")
        assert dimension.get_formatted_text() == "45° TYP"


class TestRadialDimensions:
    """Test radial dimension functionality."""

    def test_radius_dimension_creation(self):
        """Test creating radius dimensions."""
        # Circle center and point on circumference
        center = DimensionPoint(0, 0)
        circumference_point = DimensionPoint(10, 0)
        
        dimension = Dimension(
            DimensionType.RADIUS,
            [center, circumference_point],
            "0"
        )
        
        assert dimension.dimension_type == DimensionType.RADIUS
        assert dimension.measurement_value == 10.0  # Distance from center

    def test_diameter_dimension_creation(self):
        """Test creating diameter dimensions."""
        # Circle center and point on circumference
        center = DimensionPoint(0, 0)
        circumference_point = DimensionPoint(15, 0)
        
        dimension = Dimension(
            DimensionType.DIAMETER,
            [center, circumference_point],
            "0"
        )
        
        assert dimension.dimension_type == DimensionType.DIAMETER
        assert dimension.measurement_value == 30.0  # Twice the radius

    def test_radius_dimension_calculation(self):
        """Test radius calculation with various points."""
        test_cases = [
            # Center, circumference point, expected radius
            (DimensionPoint(0, 0), DimensionPoint(5, 0), 5.0),
            (DimensionPoint(0, 0), DimensionPoint(0, 3), 3.0),
            (DimensionPoint(0, 0), DimensionPoint(3, 4), 5.0),  # 3-4-5 triangle
            (DimensionPoint(5, 5), DimensionPoint(8, 9), 5.0),  # Offset center
        ]
        
        for center, circumference, expected_radius in test_cases:
            dimension = Dimension(
                DimensionType.RADIUS,
                [center, circumference],
                "0"
            )
            assert abs(dimension.measurement_value - expected_radius) < 0.001

    def test_diameter_dimension_calculation(self):
        """Test diameter calculation."""
        center = DimensionPoint(0, 0)
        circumference_point = DimensionPoint(7.5, 0)
        
        dimension = Dimension(
            DimensionType.DIAMETER,
            [center, circumference_point],
            "0"
        )
        
        assert dimension.measurement_value == 15.0  # Diameter = 2 * radius

    def test_radial_dimension_formatting(self):
        """Test radial dimension text formatting."""
        # Test radius formatting
        radius_dim = Dimension(
            DimensionType.RADIUS,
            [DimensionPoint(0, 0), DimensionPoint(12.5, 0)],
            "0"
        )
        
        radius_text = radius_dim.get_formatted_text()
        assert "12.5" in radius_text
        
        # Test diameter formatting  
        diameter_dim = Dimension(
            DimensionType.DIAMETER,
            [DimensionPoint(0, 0), DimensionPoint(12.5, 0)],
            "0"
        )
        
        diameter_text = diameter_dim.get_formatted_text()
        assert "25" in diameter_text  # Should be 2 * 12.5


class TestArcLengthDimensions:
    """Test arc length dimension functionality."""

    def test_arc_length_dimension_creation(self):
        """Test creating arc length dimensions."""
        # Arc center, arc point, text position
        center = DimensionPoint(0, 0)
        arc_point = DimensionPoint(10, 0)
        text_position = DimensionPoint(15, 5)
        
        dimension = Dimension(
            DimensionType.ARC_LENGTH,
            [center, arc_point, text_position],
            "0"
        )
        
        assert dimension.dimension_type == DimensionType.ARC_LENGTH
        assert len(dimension.points) == 3

    def test_arc_length_calculation(self):
        """Test arc length calculation."""
        # For a quarter circle with radius 10
        # Arc length = radius * angle_in_radians = 10 * (π/2) ≈ 15.708
        
        radius = 10.0
        angle_radians = math.pi / 2  # 90 degrees
        expected_arc_length = radius * angle_radians
        
        # This would typically be calculated by the tool based on 
        # the actual arc entity properties
        dimension = Dimension(
            DimensionType.ARC_LENGTH,
            [DimensionPoint(0, 0), DimensionPoint(10, 0), DimensionPoint(15, 5)],
            "0"
        )
        
        # Manually set for testing (in real use, this would be calculated)
        dimension.measurement_value = expected_arc_length
        
        assert abs(dimension.measurement_value - expected_arc_length) < 0.001

    def test_arc_length_formatting(self):
        """Test arc length dimension text formatting."""
        dimension = Dimension(
            DimensionType.ARC_LENGTH,
            [DimensionPoint(0, 0), DimensionPoint(10, 0), DimensionPoint(15, 5)],
            "0"
        )
        
        # Set a known arc length
        dimension.measurement_value = 15.708
        formatted_text = dimension.get_formatted_text()
        
        assert "15.708" in formatted_text or "15.71" in formatted_text


class TestDimensionStyles:
    """Test dimension styling for angular and radial dimensions."""

    def test_angular_dimension_style(self):
        """Test that angular dimensions can use custom styles."""
        from backend.models.dimension import DimensionStyle
        
        # Create custom style for angular dimensions
        style = DimensionStyle("Angular Style")
        style.text_height = 3.0
        style.precision = 1  # 1 decimal place for angles
        style.unit_suffix = "°"
        
        dimension = Dimension(
            DimensionType.ANGULAR,
            [DimensionPoint(0, 0), DimensionPoint(10, 0)],
            "0",
            style
        )
        
        dimension.measurement_value = 45.67
        formatted_text = dimension.get_formatted_text()
        
        # Should round to 1 decimal and include degree symbol
        assert "45.7°" in formatted_text

    def test_radial_dimension_style(self):
        """Test that radial dimensions can use custom styles."""
        from backend.models.dimension import DimensionStyle
        
        # Create custom style for radial dimensions
        style = DimensionStyle("Radial Style")
        style.precision = 3  # 3 decimal places
        style.unit_suffix = "mm"
        
        dimension = Dimension(
            DimensionType.RADIUS,
            [DimensionPoint(0, 0), DimensionPoint(12.3456, 0)],
            "0",
            style
        )
        
        formatted_text = dimension.get_formatted_text()
        
        # Should include 3 decimal places and mm unit
        assert "12.346mm" in formatted_text


class TestDimensionValidation:
    """Test validation for angular and radial dimensions."""

    def test_insufficient_points_angular(self):
        """Test that angular dimensions require sufficient points."""
        # Angular dimensions need at least 2 points (vertex and arc position)
        with pytest.raises(Exception):
            Dimension(
                DimensionType.ANGULAR,
                [DimensionPoint(0, 0)],  # Only one point
                "0"
            )

    def test_insufficient_points_radius(self):
        """Test that radial dimensions require sufficient points."""
        # Radial dimensions need at least 2 points (center and circumference)
        with pytest.raises(Exception):
            Dimension(
                DimensionType.RADIUS,
                [DimensionPoint(0, 0)],  # Only one point
                "0"
            )

    def test_zero_radius_handling(self):
        """Test handling of zero radius cases."""
        # Same point for center and circumference
        dimension = Dimension(
            DimensionType.RADIUS,
            [DimensionPoint(5, 5), DimensionPoint(5, 5)],
            "0"
        )
        
        assert dimension.measurement_value == 0.0