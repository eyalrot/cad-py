"""
Unit tests for Point2D class.
"""

import math
import pytest
import numpy as np
import sys
import os

# Add the backend directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from core.geometry.point import Point2D


class TestPoint2D:
    """Test cases for Point2D class."""
    
    def test_init(self):
        """Test point initialization."""
        p = Point2D(1.0, 2.0)
        assert p.x == 1.0
        assert p.y == 2.0
    
    def test_repr(self):
        """Test string representation."""
        p = Point2D(1.5, 2.5)
        assert repr(p) == "Point2D(1.5, 2.5)"
    
    def test_str(self):
        """Test human-readable string."""
        p = Point2D(1.5, 2.5)
        assert str(p) == "(1.500, 2.500)"
    
    def test_equality(self):
        """Test equality comparison."""
        p1 = Point2D(1.0, 2.0)
        p2 = Point2D(1.0, 2.0)
        p3 = Point2D(1.1, 2.0)
        
        assert p1 == p2
        assert p1 != p3
        assert p1 != "not a point"
    
    def test_hash(self):
        """Test hash function."""
        p1 = Point2D(1.0, 2.0)
        p2 = Point2D(1.0, 2.0)
        p3 = Point2D(1.1, 2.0)
        
        assert hash(p1) == hash(p2)
        assert hash(p1) != hash(p3)
        
        # Test in set
        point_set = {p1, p2, p3}
        assert len(point_set) == 2
    
    def test_addition(self):
        """Test point addition."""
        p1 = Point2D(1.0, 2.0)
        p2 = Point2D(3.0, 4.0)
        result = p1 + p2
        
        assert result.x == 4.0
        assert result.y == 6.0
    
    def test_subtraction(self):
        """Test point subtraction."""
        p1 = Point2D(5.0, 7.0)
        p2 = Point2D(2.0, 3.0)
        result = p1 - p2
        
        assert result.x == 3.0
        assert result.y == 4.0
    
    def test_scalar_multiplication(self):
        """Test scalar multiplication."""
        p = Point2D(2.0, 3.0)
        result1 = p * 2.5
        result2 = 2.5 * p
        
        assert result1.x == 5.0
        assert result1.y == 7.5
        assert result2.x == 5.0
        assert result2.y == 7.5
    
    def test_scalar_division(self):
        """Test scalar division."""
        p = Point2D(6.0, 9.0)
        result = p / 3.0
        
        assert result.x == 2.0
        assert result.y == 3.0
        
        # Test division by zero
        with pytest.raises(ValueError):
            p / 0.0
    
    def test_distance_to(self):
        """Test distance calculation."""
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(3.0, 4.0)
        
        distance = p1.distance_to(p2)
        assert abs(distance - 5.0) < 1e-10
        
        # Test distance to self
        assert p1.distance_to(p1) == 0.0
    
    def test_distance_squared_to(self):
        """Test squared distance calculation."""
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(3.0, 4.0)
        
        dist_sq = p1.distance_squared_to(p2)
        assert dist_sq == 25.0
    
    def test_translate(self):
        """Test translation."""
        p = Point2D(1.0, 2.0)
        translated = p.translate(3.0, 4.0)
        
        assert translated.x == 4.0
        assert translated.y == 6.0
        # Original point unchanged
        assert p.x == 1.0
        assert p.y == 2.0
    
    def test_rotate(self):
        """Test rotation."""
        p = Point2D(1.0, 0.0)
        
        # Rotate 90 degrees around origin
        rotated = p.rotate(math.pi / 2)
        assert abs(rotated.x) < 1e-10
        assert abs(rotated.y - 1.0) < 1e-10
        
        # Rotate around custom center
        center = Point2D(1.0, 1.0)
        rotated2 = p.rotate(math.pi / 2, center)
        assert abs(rotated2.x - 2.0) < 1e-10
        assert abs(rotated2.y - 1.0) < 1e-10
    
    def test_scale(self):
        """Test scaling."""
        p = Point2D(2.0, 3.0)
        
        # Uniform scaling
        scaled1 = p.scale(2.0)
        assert scaled1.x == 4.0
        assert scaled1.y == 6.0
        
        # Non-uniform scaling
        scaled2 = p.scale(2.0, 3.0)
        assert scaled2.x == 4.0
        assert scaled2.y == 9.0
        
        # Scaling around custom center
        center = Point2D(1.0, 1.0)
        scaled3 = p.scale(2.0, 2.0, center)
        assert scaled3.x == 3.0
        assert scaled3.y == 5.0
    
    def test_mirror(self):
        """Test mirroring operations."""
        p = Point2D(2.0, 3.0)
        
        # Mirror across x-axis (y=0)
        mirrored_x = p.mirror_x()
        assert mirrored_x.x == 2.0
        assert mirrored_x.y == -3.0
        
        # Mirror across y-axis (x=0)
        mirrored_y = p.mirror_y()
        assert mirrored_y.x == -2.0
        assert mirrored_y.y == 3.0
        
        # Mirror across custom axes
        mirrored_x2 = p.mirror_x(1.0)
        assert mirrored_x2.x == 2.0
        assert mirrored_x2.y == -1.0
    
    def test_midpoint(self):
        """Test midpoint calculation."""
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(4.0, 6.0)
        
        mid = p1.midpoint(p2)
        assert mid.x == 2.0
        assert mid.y == 3.0
    
    def test_angle_to(self):
        """Test angle calculation."""
        p1 = Point2D(0.0, 0.0)
        p2 = Point2D(1.0, 0.0)  # East
        p3 = Point2D(0.0, 1.0)  # North
        
        angle1 = p1.angle_to(p2)
        assert abs(angle1) < 1e-10
        
        angle2 = p1.angle_to(p3)
        assert abs(angle2 - math.pi / 2) < 1e-10
    
    def test_polar_offset(self):
        """Test polar offset."""
        p = Point2D(0.0, 0.0)
        
        # Move 5 units at 0 degrees (east)
        offset1 = p.polar_offset(5.0, 0.0)
        assert abs(offset1.x - 5.0) < 1e-10
        assert abs(offset1.y) < 1e-10
        
        # Move 5 units at 90 degrees (north)
        offset2 = p.polar_offset(5.0, math.pi / 2)
        assert abs(offset2.x) < 1e-10
        assert abs(offset2.y - 5.0) < 1e-10
    
    def test_tuple_conversion(self):
        """Test tuple conversion."""
        p = Point2D(1.5, 2.5)
        
        # To tuple
        tup = p.to_tuple()
        assert tup == (1.5, 2.5)
        
        # From tuple
        p2 = Point2D.from_tuple(tup)
        assert p == p2
    
    def test_array_conversion(self):
        """Test numpy array conversion."""
        p = Point2D(1.5, 2.5)
        
        # To array
        arr = p.to_array()
        assert np.array_equal(arr, np.array([1.5, 2.5]))
        
        # From array
        p2 = Point2D.from_array(arr)
        assert p == p2
        
        # From array with more than 2 elements
        arr_long = np.array([1.5, 2.5, 3.5])
        p3 = Point2D.from_array(arr_long)
        assert p == p3
        
        # From array with too few elements
        with pytest.raises(ValueError):
            Point2D.from_array(np.array([1.5]))
    
    def test_origin(self):
        """Test origin creation."""
        origin = Point2D.origin()
        assert origin.x == 0.0
        assert origin.y == 0.0
        
        assert origin.is_origin()
        
        p = Point2D(1.0, 1.0)
        assert not p.is_origin()
    
    def test_magnitude(self):
        """Test magnitude calculation."""
        p1 = Point2D(3.0, 4.0)
        assert abs(p1.magnitude() - 5.0) < 1e-10
        
        p2 = Point2D(0.0, 0.0)
        assert p2.magnitude() == 0.0
    
    def test_normalize(self):
        """Test normalization."""
        p1 = Point2D(3.0, 4.0)
        normalized = p1.normalize()
        
        assert abs(normalized.magnitude() - 1.0) < 1e-10
        assert abs(normalized.x - 0.6) < 1e-10
        assert abs(normalized.y - 0.8) < 1e-10
        
        # Test zero vector normalization
        zero = Point2D(0.0, 0.0)
        with pytest.raises(ValueError):
            zero.normalize()
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        p = Point2D(1.0, 2.0)
        
        # Very small numbers
        tiny = Point2D(1e-15, 1e-15)
        assert tiny.is_origin()
        
        # Large numbers
        large = Point2D(1e10, 1e10)
        assert large.magnitude() == math.sqrt(2e20)