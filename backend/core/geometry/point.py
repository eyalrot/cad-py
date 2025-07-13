"""
Point2D geometry class implementation.

Provides 2D point operations for CAD applications including distance calculations,
transformations, and coordinate manipulations.
"""

import math
from typing import Tuple, Union
import numpy as np


class Point2D:
    """
    Represents a 2D point with x, y coordinates.
    
    Provides methods for distance calculations, transformations,
    and coordinate manipulations commonly used in CAD applications.
    """
    
    def __init__(self, x: float, y: float) -> None:
        """
        Initialize a 2D point.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.x = float(x)
        self.y = float(y)
    
    def __repr__(self) -> str:
        """String representation of the point."""
        return f"Point2D({self.x}, {self.y})"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"({self.x:.3f}, {self.y:.3f})"
    
    def __eq__(self, other: object) -> bool:
        """
        Check equality with another point within tolerance.
        
        Args:
            other: Another Point2D object
            
        Returns:
            True if points are equal within tolerance
        """
        if not isinstance(other, Point2D):
            return NotImplemented
        
        tolerance = 1e-10
        return (abs(self.x - other.x) < tolerance and 
                abs(self.y - other.y) < tolerance)
    
    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((round(self.x, 10), round(self.y, 10)))
    
    def __add__(self, other: 'Point2D') -> 'Point2D':
        """Add two points (vector addition)."""
        return Point2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point2D') -> 'Point2D':
        """Subtract two points (vector subtraction)."""
        return Point2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point2D':
        """Multiply point by scalar."""
        return Point2D(self.x * scalar, self.y * scalar)
    
    def __rmul__(self, scalar: float) -> 'Point2D':
        """Right multiply by scalar."""
        return self.__mul__(scalar)
    
    def __truediv__(self, scalar: float) -> 'Point2D':
        """Divide point by scalar."""
        if abs(scalar) < 1e-10:
            raise ValueError("Cannot divide by zero")
        return Point2D(self.x / scalar, self.y / scalar)
    
    def distance_to(self, other: 'Point2D') -> float:
        """
        Calculate Euclidean distance to another point.
        
        Args:
            other: Target point
            
        Returns:
            Distance between points
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return math.sqrt(dx * dx + dy * dy)
    
    def distance_squared_to(self, other: 'Point2D') -> float:
        """
        Calculate squared distance to another point (faster than distance_to).
        
        Args:
            other: Target point
            
        Returns:
            Squared distance between points
        """
        dx = self.x - other.x
        dy = self.y - other.y
        return dx * dx + dy * dy
    
    def translate(self, dx: float, dy: float) -> 'Point2D':
        """
        Create a new point translated by given offsets.
        
        Args:
            dx: X offset
            dy: Y offset
            
        Returns:
            New translated point
        """
        return Point2D(self.x + dx, self.y + dy)
    
    def rotate(self, angle: float, center: 'Point2D' = None) -> 'Point2D':
        """
        Rotate point around a center by given angle.
        
        Args:
            angle: Rotation angle in radians
            center: Center of rotation (origin if None)
            
        Returns:
            New rotated point
        """
        if center is None:
            center = Point2D(0, 0)
        
        # Translate to origin
        translated = self - center
        
        # Apply rotation
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)
        
        new_x = translated.x * cos_a - translated.y * sin_a
        new_y = translated.x * sin_a + translated.y * cos_a
        
        # Translate back
        return Point2D(new_x, new_y) + center
    
    def scale(self, sx: float, sy: float = None, center: 'Point2D' = None) -> 'Point2D':
        """
        Scale point relative to a center.
        
        Args:
            sx: X scale factor
            sy: Y scale factor (uses sx if None for uniform scaling)
            center: Center of scaling (origin if None)
            
        Returns:
            New scaled point
        """
        if sy is None:
            sy = sx
        
        if center is None:
            center = Point2D(0, 0)
        
        # Translate to origin, scale, translate back
        translated = self - center
        scaled = Point2D(translated.x * sx, translated.y * sy)
        return scaled + center
    
    def mirror_x(self, axis_y: float = 0) -> 'Point2D':
        """
        Mirror point across horizontal line.
        
        Args:
            axis_y: Y coordinate of mirror axis
            
        Returns:
            New mirrored point
        """
        return Point2D(self.x, 2 * axis_y - self.y)
    
    def mirror_y(self, axis_x: float = 0) -> 'Point2D':
        """
        Mirror point across vertical line.
        
        Args:
            axis_x: X coordinate of mirror axis
            
        Returns:
            New mirrored point
        """
        return Point2D(2 * axis_x - self.x, self.y)
    
    def midpoint(self, other: 'Point2D') -> 'Point2D':
        """
        Calculate midpoint between this and another point.
        
        Args:
            other: Other point
            
        Returns:
            Midpoint between the two points
        """
        return Point2D((self.x + other.x) / 2, (self.y + other.y) / 2)
    
    def angle_to(self, other: 'Point2D') -> float:
        """
        Calculate angle from this point to another point.
        
        Args:
            other: Target point
            
        Returns:
            Angle in radians (-π to π)
        """
        return math.atan2(other.y - self.y, other.x - self.x)
    
    def polar_offset(self, distance: float, angle: float) -> 'Point2D':
        """
        Create new point at polar offset from this point.
        
        Args:
            distance: Distance from this point
            angle: Angle in radians
            
        Returns:
            New point at polar offset
        """
        return Point2D(
            self.x + distance * math.cos(angle),
            self.y + distance * math.sin(angle)
        )
    
    def to_tuple(self) -> Tuple[float, float]:
        """
        Convert point to tuple.
        
        Returns:
            (x, y) tuple
        """
        return (self.x, self.y)
    
    def to_array(self) -> np.ndarray:
        """
        Convert point to numpy array.
        
        Returns:
            numpy array [x, y]
        """
        return np.array([self.x, self.y])
    
    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> 'Point2D':
        """
        Create point from tuple.
        
        Args:
            coords: (x, y) coordinates
            
        Returns:
            New Point2D object
        """
        return cls(coords[0], coords[1])
    
    @classmethod
    def from_array(cls, array: np.ndarray) -> 'Point2D':
        """
        Create point from numpy array.
        
        Args:
            array: numpy array with at least 2 elements
            
        Returns:
            New Point2D object
        """
        if len(array) < 2:
            raise ValueError("Array must have at least 2 elements")
        return cls(float(array[0]), float(array[1]))
    
    @classmethod
    def origin(cls) -> 'Point2D':
        """
        Create point at origin (0, 0).
        
        Returns:
            Point at origin
        """
        return cls(0.0, 0.0)
    
    def is_origin(self, tolerance: float = 1e-10) -> bool:
        """
        Check if point is at origin within tolerance.
        
        Args:
            tolerance: Comparison tolerance
            
        Returns:
            True if point is at origin
        """
        return abs(self.x) < tolerance and abs(self.y) < tolerance
    
    def magnitude(self) -> float:
        """
        Calculate magnitude (distance from origin).
        
        Returns:
            Distance from origin
        """
        return math.sqrt(self.x * self.x + self.y * self.y)
    
    def normalize(self) -> 'Point2D':
        """
        Create unit vector pointing in same direction.
        
        Returns:
            Normalized point (unit vector)
            
        Raises:
            ValueError: If point is at origin
        """
        mag = self.magnitude()
        if mag < 1e-10:
            raise ValueError("Cannot normalize zero-length vector")
        return Point2D(self.x / mag, self.y / mag)