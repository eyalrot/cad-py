"""
Unit tests for Vector2D class.
"""

import math
import pytest
import numpy as np
import sys
import os

# Add the backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.geometry.vector import Vector2D
from core.geometry.point import Point2D


class TestVector2D:
    """Test cases for Vector2D class."""
    
    def test_init(self):
        """Test vector initialization."""
        v = Vector2D(1.0, 2.0)
        assert v.x == 1.0
        assert v.y == 2.0
    
    def test_repr(self):
        """Test string representation."""
        v = Vector2D(1.5, 2.5)
        assert repr(v) == "Vector2D(1.5, 2.5)"
    
    def test_str(self):
        """Test human-readable string."""
        v = Vector2D(1.5, 2.5)
        assert str(v) == "<1.500, 2.500>"
    
    def test_equality(self):
        """Test equality comparison."""
        v1 = Vector2D(1.0, 2.0)
        v2 = Vector2D(1.0, 2.0)
        v3 = Vector2D(1.1, 2.0)
        
        assert v1 == v2
        assert v1 != v3
        assert v1 != "not a vector"
    
    def test_arithmetic_operations(self):
        """Test vector arithmetic."""
        v1 = Vector2D(1.0, 2.0)
        v2 = Vector2D(3.0, 4.0)
        
        # Addition
        add_result = v1 + v2
        assert add_result.x == 4.0
        assert add_result.y == 6.0
        
        # Subtraction
        sub_result = v2 - v1
        assert sub_result.x == 2.0
        assert sub_result.y == 2.0
        
        # Scalar multiplication
        mul_result1 = v1 * 2.0
        mul_result2 = 2.0 * v1
        assert mul_result1.x == 2.0
        assert mul_result1.y == 4.0
        assert mul_result2 == mul_result1
        
        # Scalar division
        div_result = v2 / 2.0
        assert div_result.x == 1.5
        assert div_result.y == 2.0
        
        # Division by zero
        with pytest.raises(ValueError):
            v1 / 0.0
        
        # Negation
        neg_result = -v1
        assert neg_result.x == -1.0
        assert neg_result.y == -2.0
    
    def test_magnitude(self):
        """Test magnitude calculations."""
        v1 = Vector2D(3.0, 4.0)
        assert abs(v1.magnitude() - 5.0) < 1e-10
        assert v1.magnitude_squared() == 25.0
        
        v2 = Vector2D(0.0, 0.0)
        assert v2.magnitude() == 0.0
        assert v2.magnitude_squared() == 0.0
    
    def test_normalize(self):
        """Test normalization."""
        v1 = Vector2D(3.0, 4.0)
        normalized = v1.normalize()
        
        assert abs(normalized.magnitude() - 1.0) < 1e-10
        assert abs(normalized.x - 0.6) < 1e-10
        assert abs(normalized.y - 0.8) < 1e-10
        
        # Test zero vector normalization
        zero = Vector2D(0.0, 0.0)
        with pytest.raises(ValueError):
            zero.normalize()
    
    def test_dot_product(self):
        """Test dot product."""
        v1 = Vector2D(1.0, 2.0)
        v2 = Vector2D(3.0, 4.0)
        
        dot = v1.dot(v2)
        assert dot == 11.0  # 1*3 + 2*4
        
        # Orthogonal vectors
        v3 = Vector2D(1.0, 0.0)
        v4 = Vector2D(0.0, 1.0)
        assert v3.dot(v4) == 0.0
    
    def test_cross_product(self):
        """Test cross product (2D returns scalar)."""
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(0.0, 1.0)
        
        cross = v1.cross(v2)
        assert cross == 1.0
        
        # Parallel vectors
        v3 = Vector2D(2.0, 0.0)
        assert v1.cross(v3) == 0.0
    
    def test_angle_operations(self):
        """Test angle-related operations."""
        v1 = Vector2D(1.0, 0.0)  # East
        v2 = Vector2D(0.0, 1.0)  # North
        v3 = Vector2D(-1.0, 0.0)  # West
        
        # Angle from x-axis
        assert abs(v1.angle()) < 1e-10
        assert abs(v2.angle() - math.pi / 2) < 1e-10
        assert abs(v3.angle() - math.pi) < 1e-10
        
        # Angle between vectors
        angle = v1.angle_to(v2)
        assert abs(angle - math.pi / 2) < 1e-10
        
        # Signed angle
        signed_angle = v1.signed_angle_to(v2)
        assert abs(signed_angle - math.pi / 2) < 1e-10
        
        signed_angle2 = v2.signed_angle_to(v1)
        assert abs(signed_angle2 + math.pi / 2) < 1e-10
        
        # Test with zero vectors
        zero = Vector2D(0.0, 0.0)
        with pytest.raises(ValueError):
            v1.angle_to(zero)
    
    def test_rotation(self):
        """Test vector rotation."""
        v = Vector2D(1.0, 0.0)
        
        # Rotate 90 degrees
        rotated = v.rotate(math.pi / 2)
        assert abs(rotated.x) < 1e-10
        assert abs(rotated.y - 1.0) < 1e-10
        
        # Rotate 180 degrees
        rotated2 = v.rotate(math.pi)
        assert abs(rotated2.x + 1.0) < 1e-10
        assert abs(rotated2.y) < 1e-10
    
    def test_perpendicular(self):
        """Test perpendicular vectors."""
        v = Vector2D(1.0, 2.0)
        
        # Counter-clockwise perpendicular
        perp_ccw = v.perpendicular()
        assert perp_ccw.x == -2.0
        assert perp_ccw.y == 1.0
        assert v.dot(perp_ccw) == 0.0  # Should be orthogonal
        
        # Clockwise perpendicular
        perp_cw = v.perpendicular_cw()
        assert perp_cw.x == 2.0
        assert perp_cw.y == -1.0
        assert v.dot(perp_cw) == 0.0  # Should be orthogonal
    
    def test_projection(self):
        """Test vector projection."""
        v1 = Vector2D(3.0, 4.0)
        v2 = Vector2D(1.0, 0.0)  # Unit vector along x-axis
        
        proj = v1.project_onto(v2)
        assert proj.x == 3.0
        assert proj.y == 0.0
        
        # Test projection onto zero vector
        zero = Vector2D(0.0, 0.0)
        with pytest.raises(ValueError):
            v1.project_onto(zero)
    
    def test_rejection(self):
        """Test vector rejection."""
        v1 = Vector2D(3.0, 4.0)
        v2 = Vector2D(1.0, 0.0)  # Unit vector along x-axis
        
        rejection = v1.reject_from(v2)
        assert rejection.x == 0.0
        assert rejection.y == 4.0
        
        # Projection + rejection should equal original
        projection = v1.project_onto(v2)
        assert (projection + rejection) == v1
    
    def test_reflection(self):
        """Test vector reflection."""
        v = Vector2D(1.0, 1.0)
        normal = Vector2D(0.0, 1.0)  # Vertical normal
        
        reflected = v.reflect(normal)
        assert reflected.x == 1.0
        assert reflected.y == -1.0
        
        # Test with non-normalized normal
        normal2 = Vector2D(0.0, 2.0)
        reflected2 = v.reflect(normal2)
        assert abs(reflected2.x - 1.0) < 1e-10
        assert abs(reflected2.y + 1.0) < 1e-10
    
    def test_interpolation(self):
        """Test linear interpolation."""
        v1 = Vector2D(0.0, 0.0)
        v2 = Vector2D(4.0, 6.0)
        
        # At t=0, should get v1
        lerp0 = v1.lerp(v2, 0.0)
        assert lerp0 == v1
        
        # At t=1, should get v2
        lerp1 = v1.lerp(v2, 1.0)
        assert lerp1 == v2
        
        # At t=0.5, should get midpoint
        lerp_mid = v1.lerp(v2, 0.5)
        assert lerp_mid.x == 2.0
        assert lerp_mid.y == 3.0
    
    def test_parallel_perpendicular_checks(self):
        """Test parallel and perpendicular checks."""
        v1 = Vector2D(1.0, 0.0)
        v2 = Vector2D(2.0, 0.0)  # Parallel
        v3 = Vector2D(0.0, 1.0)  # Perpendicular
        v4 = Vector2D(1.0, 1.0)  # Neither
        
        # Parallel check
        assert v1.is_parallel_to(v2)
        assert not v1.is_parallel_to(v3)
        assert not v1.is_parallel_to(v4)
        
        # Perpendicular check
        assert v1.is_perpendicular_to(v3)
        assert not v1.is_perpendicular_to(v2)
        assert not v1.is_perpendicular_to(v4)
    
    def test_vector_properties(self):
        """Test vector property checks."""
        zero = Vector2D(0.0, 0.0)
        unit = Vector2D(1.0, 0.0)
        normal = Vector2D(3.0, 4.0)
        
        # Zero vector check
        assert zero.is_zero()
        assert not unit.is_zero()
        assert not normal.is_zero()
        
        # Unit vector check
        assert unit.is_unit()
        assert not zero.is_unit()
        assert not normal.is_unit()
        
        # Check normalized vector is unit
        assert normal.normalize().is_unit()
    
    def test_conversions(self):
        """Test conversions to other types."""
        v = Vector2D(1.5, 2.5)
        
        # To point
        p = v.to_point()
        assert isinstance(p, Point2D)
        assert p.x == 1.5
        assert p.y == 2.5
        
        # To tuple
        tup = v.to_tuple()
        assert tup == (1.5, 2.5)
        
        # To array
        arr = v.to_array()
        assert np.array_equal(arr, np.array([1.5, 2.5]))
    
    def test_factory_methods(self):
        """Test factory methods."""
        # From tuple
        v1 = Vector2D.from_tuple((1.5, 2.5))
        assert v1.x == 1.5
        assert v1.y == 2.5
        
        # From array
        arr = np.array([1.5, 2.5])
        v2 = Vector2D.from_array(arr)
        assert v2.x == 1.5
        assert v2.y == 2.5
        
        # From array with too few elements
        with pytest.raises(ValueError):
            Vector2D.from_array(np.array([1.5]))
        
        # From points
        p1 = Point2D(1.0, 2.0)
        p2 = Point2D(4.0, 6.0)
        v3 = Vector2D.from_points(p1, p2)
        assert v3.x == 3.0
        assert v3.y == 4.0
        
        # From angle
        v4 = Vector2D.from_angle(math.pi / 2, 5.0)
        assert abs(v4.x) < 1e-10
        assert abs(v4.y - 5.0) < 1e-10
        
        # Unit vectors
        unit_x = Vector2D.unit_x()
        assert unit_x.x == 1.0
        assert unit_x.y == 0.0
        assert unit_x.is_unit()
        
        unit_y = Vector2D.unit_y()
        assert unit_y.x == 0.0
        assert unit_y.y == 1.0
        assert unit_y.is_unit()
        
        # Zero vector
        zero = Vector2D.zero()
        assert zero.x == 0.0
        assert zero.y == 0.0
        assert zero.is_zero()
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Very small vectors
        tiny = Vector2D(1e-15, 1e-15)
        assert tiny.is_zero()
        
        # Large vectors
        large = Vector2D(1e10, 1e10)
        normalized_large = large.normalize()
        assert normalized_large.is_unit()