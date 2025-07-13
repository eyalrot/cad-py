"""
Vector2D geometry class implementation.

Provides 2D vector operations for CAD applications including mathematical operations,
transformations, and geometric calculations.
"""

import math
from typing import Tuple, Union

import numpy as np

from .point import Point2D


class Vector2D:
    """
    Represents a 2D vector with x, y components.

    Provides methods for vector arithmetic, geometric operations,
    and transformations commonly used in CAD applications.
    """

    def __init__(self, x: float, y: float) -> None:
        """
        Initialize a 2D vector.

        Args:
            x: X component
            y: Y component
        """
        self.x = float(x)
        self.y = float(y)

    def __repr__(self) -> str:
        """String representation of the vector."""
        return f"Vector2D({self.x}, {self.y})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"<{self.x:.3f}, {self.y:.3f}>"

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another vector within tolerance.

        Args:
            other: Another Vector2D object

        Returns:
            True if vectors are equal within tolerance
        """
        if not isinstance(other, Vector2D):
            return NotImplemented

        tolerance = 1e-10
        return abs(self.x - other.x) < tolerance and abs(self.y - other.y) < tolerance

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((round(self.x, 10), round(self.y, 10)))

    def __add__(self, other: "Vector2D") -> "Vector2D":
        """Add two vectors."""
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other: "Vector2D") -> "Vector2D":
        """Subtract two vectors."""
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        """Multiply vector by scalar."""
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2D":
        """Right multiply by scalar."""
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> "Vector2D":
        """Divide vector by scalar."""
        if abs(scalar) < 1e-10:
            raise ValueError("Cannot divide by zero")
        return Vector2D(self.x / scalar, self.y / scalar)

    def __neg__(self) -> "Vector2D":
        """Negate vector."""
        return Vector2D(-self.x, -self.y)

    def magnitude(self) -> float:
        """
        Calculate vector magnitude (length).

        Returns:
            Vector magnitude
        """
        return math.sqrt(self.x * self.x + self.y * self.y)

    def magnitude_squared(self) -> float:
        """
        Calculate squared magnitude (faster than magnitude).

        Returns:
            Squared vector magnitude
        """
        return self.x * self.x + self.y * self.y

    def normalize(self) -> "Vector2D":
        """
        Create unit vector in same direction.

        Returns:
            Normalized vector

        Raises:
            ValueError: If vector is zero-length
        """
        mag = self.magnitude()
        if mag < 1e-10:
            raise ValueError("Cannot normalize zero-length vector")
        return Vector2D(self.x / mag, self.y / mag)

    def dot(self, other: "Vector2D") -> float:
        """
        Calculate dot product with another vector.

        Args:
            other: Other vector

        Returns:
            Dot product value
        """
        return self.x * other.x + self.y * other.y

    def cross(self, other: "Vector2D") -> float:
        """
        Calculate cross product magnitude (2D cross product returns scalar).

        Args:
            other: Other vector

        Returns:
            Cross product magnitude (positive if counter-clockwise)
        """
        return self.x * other.y - self.y * other.x

    def angle(self) -> float:
        """
        Calculate angle of vector from positive x-axis.

        Returns:
            Angle in radians (-π to π)
        """
        return math.atan2(self.y, self.x)

    def angle_to(self, other: "Vector2D") -> float:
        """
        Calculate angle between this vector and another.

        Args:
            other: Other vector

        Returns:
            Angle between vectors in radians (0 to π)
        """
        dot_product = self.dot(other)
        mag_product = self.magnitude() * other.magnitude()

        if mag_product < 1e-10:
            raise ValueError("Cannot calculate angle with zero-length vector")

        cos_angle = dot_product / mag_product
        # Clamp to [-1, 1] to handle floating point errors
        cos_angle = max(-1.0, min(1.0, cos_angle))

        return math.acos(cos_angle)

    def signed_angle_to(self, other: "Vector2D") -> float:
        """
        Calculate signed angle from this vector to another.

        Args:
            other: Other vector

        Returns:
            Signed angle in radians (-π to π, positive = counter-clockwise)
        """
        return math.atan2(self.cross(other), self.dot(other))

    def rotate(self, angle: float) -> "Vector2D":
        """
        Rotate vector by given angle.

        Args:
            angle: Rotation angle in radians

        Returns:
            New rotated vector
        """
        cos_a = math.cos(angle)
        sin_a = math.sin(angle)

        new_x = self.x * cos_a - self.y * sin_a
        new_y = self.x * sin_a + self.y * cos_a

        return Vector2D(new_x, new_y)

    def perpendicular(self) -> "Vector2D":
        """
        Get perpendicular vector (90° counter-clockwise rotation).

        Returns:
            Perpendicular vector
        """
        return Vector2D(-self.y, self.x)

    def perpendicular_cw(self) -> "Vector2D":
        """
        Get perpendicular vector (90° clockwise rotation).

        Returns:
            Perpendicular vector (clockwise)
        """
        return Vector2D(self.y, -self.x)

    def project_onto(self, other: "Vector2D") -> "Vector2D":
        """
        Project this vector onto another vector.

        Args:
            other: Vector to project onto

        Returns:
            Projected vector

        Raises:
            ValueError: If other vector is zero-length
        """
        other_mag_sq = other.magnitude_squared()
        if other_mag_sq < 1e-10:
            raise ValueError("Cannot project onto zero-length vector")

        scalar_proj = self.dot(other) / other_mag_sq
        return other * scalar_proj

    def reject_from(self, other: "Vector2D") -> "Vector2D":
        """
        Calculate vector rejection (component perpendicular to other vector).

        Args:
            other: Vector to reject from

        Returns:
            Rejection vector
        """
        projection = self.project_onto(other)
        return self - projection

    def reflect(self, normal: "Vector2D") -> "Vector2D":
        """
        Reflect vector across a surface with given normal.

        Args:
            normal: Surface normal vector (should be normalized)

        Returns:
            Reflected vector
        """
        # Ensure normal is normalized
        if abs(normal.magnitude() - 1.0) > 1e-10:
            normal = normal.normalize()

        return self - 2 * self.project_onto(normal)

    def lerp(self, other: "Vector2D", t: float) -> "Vector2D":
        """
        Linear interpolation between this and another vector.

        Args:
            other: Target vector
            t: Interpolation parameter (0.0 = this, 1.0 = other)

        Returns:
            Interpolated vector
        """
        return self + (other - self) * t

    def is_parallel_to(self, other: "Vector2D", tolerance: float = 1e-10) -> bool:
        """
        Check if vector is parallel to another vector.

        Args:
            other: Other vector
            tolerance: Comparison tolerance

        Returns:
            True if vectors are parallel
        """
        cross_product = abs(self.cross(other))
        return cross_product < tolerance

    def is_perpendicular_to(self, other: "Vector2D", tolerance: float = 1e-10) -> bool:
        """
        Check if vector is perpendicular to another vector.

        Args:
            other: Other vector
            tolerance: Comparison tolerance

        Returns:
            True if vectors are perpendicular
        """
        dot_product = abs(self.dot(other))
        return dot_product < tolerance

    def is_zero(self, tolerance: float = 1e-10) -> bool:
        """
        Check if vector is zero vector within tolerance.

        Args:
            tolerance: Comparison tolerance

        Returns:
            True if vector is zero
        """
        return self.magnitude() < tolerance

    def is_unit(self, tolerance: float = 1e-10) -> bool:
        """
        Check if vector is unit vector within tolerance.

        Args:
            tolerance: Comparison tolerance

        Returns:
            True if vector is unit length
        """
        return abs(self.magnitude() - 1.0) < tolerance

    def to_point(self) -> Point2D:
        """
        Convert vector to point.

        Returns:
            Point2D with same coordinates
        """
        return Point2D(self.x, self.y)

    def to_tuple(self) -> Tuple[float, float]:
        """
        Convert vector to tuple.

        Returns:
            (x, y) tuple
        """
        return (self.x, self.y)

    def to_array(self) -> np.ndarray:
        """
        Convert vector to numpy array.

        Returns:
            numpy array [x, y]
        """
        return np.array([self.x, self.y])

    @classmethod
    def from_tuple(cls, coords: Tuple[float, float]) -> "Vector2D":
        """
        Create vector from tuple.

        Args:
            coords: (x, y) coordinates

        Returns:
            New Vector2D object
        """
        return cls(coords[0], coords[1])

    @classmethod
    def from_array(cls, array: np.ndarray) -> "Vector2D":
        """
        Create vector from numpy array.

        Args:
            array: numpy array with at least 2 elements

        Returns:
            New Vector2D object
        """
        if len(array) < 2:
            raise ValueError("Array must have at least 2 elements")
        return cls(float(array[0]), float(array[1]))

    @classmethod
    def from_points(cls, start: Point2D, end: Point2D) -> "Vector2D":
        """
        Create vector from two points.

        Args:
            start: Starting point
            end: Ending point

        Returns:
            Vector from start to end
        """
        return cls(end.x - start.x, end.y - start.y)

    @classmethod
    def from_angle(cls, angle: float, magnitude: float = 1.0) -> "Vector2D":
        """
        Create vector from angle and magnitude.

        Args:
            angle: Angle in radians
            magnitude: Vector magnitude

        Returns:
            New Vector2D object
        """
        return cls(magnitude * math.cos(angle), magnitude * math.sin(angle))

    @classmethod
    def zero(cls) -> "Vector2D":
        """
        Create zero vector.

        Returns:
            Zero vector (0, 0)
        """
        return cls(0.0, 0.0)

    @classmethod
    def unit_x(cls) -> "Vector2D":
        """
        Create unit vector in positive x direction.

        Returns:
            Unit vector (1, 0)
        """
        return cls(1.0, 0.0)

    @classmethod
    def unit_y(cls) -> "Vector2D":
        """
        Create unit vector in positive y direction.

        Returns:
            Unit vector (0, 1)
        """
        return cls(0.0, 1.0)
