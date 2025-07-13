"""
Line geometry class implementation.

Provides 2D line operations for CAD applications including intersection calculations,
distance measurements, and geometric transformations.
"""

import math
from typing import List, Optional, Tuple, Union

import numpy as np

from .point import Point2D
from .vector import Vector2D


class Line:
    """
    Represents a 2D line segment defined by two endpoints.

    Provides methods for line-line intersections, distance calculations,
    and geometric operations commonly used in CAD applications.
    """

    def __init__(self, start: Point2D, end: Point2D) -> None:
        """
        Initialize a line segment.

        Args:
            start: Starting point of the line
            end: Ending point of the line

        Raises:
            ValueError: If start and end points are the same
        """
        if start == end:
            raise ValueError("Line start and end points cannot be the same")

        self.start = start
        self.end = end

    def __repr__(self) -> str:
        """String representation of the line."""
        return f"Line({self.start!r}, {self.end!r})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Line[{self.start} → {self.end}]"

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another line within tolerance.

        Args:
            other: Another Line object

        Returns:
            True if lines are equal (same endpoints in any order)
        """
        if not isinstance(other, Line):
            return NotImplemented

        return (self.start == other.start and self.end == other.end) or (
            self.start == other.end and self.end == other.start
        )

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        # Sort endpoints to ensure consistent hash regardless of direction
        p1, p2 = sorted([self.start, self.end], key=lambda p: (p.x, p.y))
        return hash((p1, p2))

    def length(self) -> float:
        """
        Calculate line length.

        Returns:
            Length of the line segment
        """
        return self.start.distance_to(self.end)

    def length_squared(self) -> float:
        """
        Calculate squared line length (faster than length).

        Returns:
            Squared length of the line segment
        """
        return self.start.distance_squared_to(self.end)

    def midpoint(self) -> Point2D:
        """
        Calculate midpoint of the line.

        Returns:
            Midpoint of the line segment
        """
        return self.start.midpoint(self.end)

    def direction_vector(self) -> Vector2D:
        """
        Get direction vector from start to end.

        Returns:
            Direction vector (not normalized)
        """
        return Vector2D.from_points(self.start, self.end)

    def unit_vector(self) -> Vector2D:
        """
        Get unit direction vector from start to end.

        Returns:
            Normalized direction vector
        """
        return self.direction_vector().normalize()

    def normal_vector(self) -> Vector2D:
        """
        Get normal vector perpendicular to the line.

        Returns:
            Normal vector (90° counter-clockwise from direction)
        """
        return self.direction_vector().perpendicular().normalize()

    def angle(self) -> float:
        """
        Get angle of line from positive x-axis.

        Returns:
            Angle in radians (-π to π)
        """
        return self.direction_vector().angle()

    def slope(self) -> Optional[float]:
        """
        Calculate slope of the line.

        Returns:
            Slope (dy/dx) or None if line is vertical
        """
        dx = self.end.x - self.start.x
        if abs(dx) < 1e-10:
            return None  # Vertical line
        return (self.end.y - self.start.y) / dx

    def y_intercept(self) -> Optional[float]:
        """
        Calculate y-intercept of the line.

        Returns:
            Y-intercept or None if line is vertical
        """
        slope = self.slope()
        if slope is None:
            return None  # Vertical line has no y-intercept
        return self.start.y - slope * self.start.x

    def point_at_parameter(self, t: float) -> Point2D:
        """
        Get point on line at parameter t.

        Args:
            t: Parameter (0.0 = start, 1.0 = end)

        Returns:
            Point on line at parameter t
        """
        return Point2D(
            self.start.x + t * (self.end.x - self.start.x),
            self.start.y + t * (self.end.y - self.start.y),
        )

    def closest_point_to(self, point: Point2D) -> Point2D:
        """
        Find closest point on line to given point.

        Args:
            point: Reference point

        Returns:
            Closest point on line segment
        """
        line_vec = self.direction_vector()
        point_vec = Vector2D.from_points(self.start, point)

        # Project point vector onto line vector
        line_length_sq = line_vec.magnitude_squared()
        if line_length_sq < 1e-10:
            return self.start  # Degenerate line

        t = point_vec.dot(line_vec) / line_length_sq

        # Clamp t to [0, 1] to stay within line segment
        t = max(0.0, min(1.0, t))

        return self.point_at_parameter(t)

    def distance_to_point(self, point: Point2D) -> float:
        """
        Calculate shortest distance from point to line segment.

        Args:
            point: Reference point

        Returns:
            Shortest distance to line segment
        """
        closest = self.closest_point_to(point)
        return point.distance_to(closest)

    def distance_to_point_infinite(self, point: Point2D) -> float:
        """
        Calculate distance from point to infinite line (not just segment).

        Args:
            point: Reference point

        Returns:
            Perpendicular distance to infinite line
        """
        # Use the formula: |ax + by + c| / sqrt(a² + b²)
        # where line equation is ax + by + c = 0

        # Convert to general form ax + by + c = 0
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y

        a = dy
        b = -dx
        c = dx * self.start.y - dy * self.start.x

        numerator = abs(a * point.x + b * point.y + c)
        denominator = math.sqrt(a * a + b * b)

        return numerator / denominator

    def contains_point(self, point: Point2D, tolerance: float = 1e-10) -> bool:
        """
        Check if point lies on the line segment.

        Args:
            point: Point to check
            tolerance: Distance tolerance

        Returns:
            True if point is on line segment
        """
        return self.distance_to_point(point) < tolerance

    def intersection(self, other: "Line") -> Optional[Point2D]:
        """
        Find intersection point with another line segment.

        Args:
            other: Other line segment

        Returns:
            Intersection point or None if no intersection
        """
        # Get direction vectors
        d1 = self.direction_vector()
        d2 = other.direction_vector()

        # Check if lines are parallel
        denominator = d1.cross(d2)
        if abs(denominator) < 1e-10:
            return None  # Parallel or collinear lines

        # Calculate parameters
        start_diff = Vector2D.from_points(self.start, other.start)
        t1 = start_diff.cross(d2) / denominator
        t2 = start_diff.cross(d1) / denominator

        # Check if intersection point is within both line segments
        if 0.0 <= t1 <= 1.0 and 0.0 <= t2 <= 1.0:
            return self.point_at_parameter(t1)

        return None

    def intersection_infinite(self, other: "Line") -> Optional[Point2D]:
        """
        Find intersection point with another line (treating both as infinite).

        Args:
            other: Other line

        Returns:
            Intersection point or None if lines are parallel
        """
        # Get direction vectors
        d1 = self.direction_vector()
        d2 = other.direction_vector()

        # Check if lines are parallel
        denominator = d1.cross(d2)
        if abs(denominator) < 1e-10:
            return None  # Parallel lines

        # Calculate parameter for this line
        start_diff = Vector2D.from_points(self.start, other.start)
        t1 = start_diff.cross(d2) / denominator

        return self.point_at_parameter(t1)

    def intersections_with_circle(
        self, center: Point2D, radius: float
    ) -> List[Point2D]:
        """
        Find intersection points with a circle.

        Args:
            center: Circle center
            radius: Circle radius

        Returns:
            List of intersection points (0, 1, or 2 points)
        """
        # Transform to coordinate system where line starts at origin
        line_vec = self.direction_vector()
        to_center = Vector2D.from_points(self.start, center)

        # Project center onto line direction
        line_length = line_vec.magnitude()
        if line_length < 1e-10:
            return []  # Degenerate line

        unit_line = line_vec / line_length
        proj_dist = to_center.dot(unit_line)

        # Find perpendicular distance from center to line
        closest_on_line = self.start + unit_line.to_point() * proj_dist
        perp_dist = center.distance_to(closest_on_line)

        # Check if circle intersects line
        if perp_dist > radius + 1e-10:
            return []  # No intersection

        # Calculate intersection parameters
        if abs(perp_dist - radius) < 1e-10:
            # Tangent - one intersection
            t = proj_dist / line_length
            if 0.0 <= t <= 1.0:
                return [closest_on_line]
            return []

        # Two intersections
        chord_half = math.sqrt(radius * radius - perp_dist * perp_dist)
        t1 = (proj_dist - chord_half) / line_length
        t2 = (proj_dist + chord_half) / line_length

        intersections = []
        if 0.0 <= t1 <= 1.0:
            intersections.append(self.point_at_parameter(t1))
        if 0.0 <= t2 <= 1.0:
            intersections.append(self.point_at_parameter(t2))

        return intersections

    def is_parallel_to(self, other: "Line", tolerance: float = 1e-10) -> bool:
        """
        Check if line is parallel to another line.

        Args:
            other: Other line
            tolerance: Angle tolerance

        Returns:
            True if lines are parallel
        """
        d1 = self.direction_vector()
        d2 = other.direction_vector()
        return d1.is_parallel_to(d2, tolerance)

    def is_perpendicular_to(self, other: "Line", tolerance: float = 1e-10) -> bool:
        """
        Check if line is perpendicular to another line.

        Args:
            other: Other line
            tolerance: Angle tolerance

        Returns:
            True if lines are perpendicular
        """
        d1 = self.direction_vector()
        d2 = other.direction_vector()
        return d1.is_perpendicular_to(d2, tolerance)

    def reverse(self) -> "Line":
        """
        Create line with reversed direction.

        Returns:
            New line with start and end swapped
        """
        return Line(self.end, self.start)

    def extend_start(self, distance: float) -> "Line":
        """
        Extend line at start by given distance.

        Args:
            distance: Extension distance

        Returns:
            New extended line
        """
        direction = self.unit_vector()
        new_start = self.start - direction.to_point() * distance
        return Line(new_start, self.end)

    def extend_end(self, distance: float) -> "Line":
        """
        Extend line at end by given distance.

        Args:
            distance: Extension distance

        Returns:
            New extended line
        """
        direction = self.unit_vector()
        new_end = self.end + direction.to_point() * distance
        return Line(self.start, new_end)

    def extend_both(self, distance: float) -> "Line":
        """
        Extend line at both ends by given distance.

        Args:
            distance: Extension distance

        Returns:
            New extended line
        """
        direction = self.unit_vector()
        new_start = self.start - direction.to_point() * distance
        new_end = self.end + direction.to_point() * distance
        return Line(new_start, new_end)

    def offset(self, distance: float) -> "Line":
        """
        Create parallel line offset by given distance.

        Args:
            distance: Offset distance (positive = left side, negative = right side)

        Returns:
            New offset line
        """
        normal = self.normal_vector()
        offset_vec = normal * distance

        new_start = self.start + offset_vec.to_point()
        new_end = self.end + offset_vec.to_point()

        return Line(new_start, new_end)

    def translate(self, dx: float, dy: float) -> "Line":
        """
        Translate line by given offsets.

        Args:
            dx: X offset
            dy: Y offset

        Returns:
            New translated line
        """
        new_start = self.start.translate(dx, dy)
        new_end = self.end.translate(dx, dy)
        return Line(new_start, new_end)

    def rotate(self, angle: float, center: Point2D = None) -> "Line":
        """
        Rotate line around a center point.

        Args:
            angle: Rotation angle in radians
            center: Center of rotation (midpoint if None)

        Returns:
            New rotated line
        """
        if center is None:
            center = self.midpoint()

        new_start = self.start.rotate(angle, center)
        new_end = self.end.rotate(angle, center)
        return Line(new_start, new_end)

    def scale(self, sx: float, sy: float = None, center: Point2D = None) -> "Line":
        """
        Scale line relative to a center point.

        Args:
            sx: X scale factor
            sy: Y scale factor (uses sx if None)
            center: Center of scaling (midpoint if None)

        Returns:
            New scaled line
        """
        if sy is None:
            sy = sx
        if center is None:
            center = self.midpoint()

        new_start = self.start.scale(sx, sy, center)
        new_end = self.end.scale(sx, sy, center)
        return Line(new_start, new_end)

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        """
        Calculate axis-aligned bounding box.

        Returns:
            Tuple of (min_point, max_point)
        """
        min_x = min(self.start.x, self.end.x)
        min_y = min(self.start.y, self.end.y)
        max_x = max(self.start.x, self.end.x)
        max_y = max(self.start.y, self.end.y)

        return (Point2D(min_x, min_y), Point2D(max_x, max_y))

    def to_tuple(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Convert line to tuple representation.

        Returns:
            ((start_x, start_y), (end_x, end_y))
        """
        return (self.start.to_tuple(), self.end.to_tuple())

    @classmethod
    def from_tuple(
        cls, coords: Tuple[Tuple[float, float], Tuple[float, float]]
    ) -> "Line":
        """
        Create line from tuple representation.

        Args:
            coords: ((start_x, start_y), (end_x, end_y))

        Returns:
            New Line object
        """
        start = Point2D.from_tuple(coords[0])
        end = Point2D.from_tuple(coords[1])
        return cls(start, end)

    @classmethod
    def from_point_and_vector(
        cls, point: Point2D, vector: Vector2D, length: float = None
    ) -> "Line":
        """
        Create line from point and direction vector.

        Args:
            point: Starting point
            vector: Direction vector
            length: Line length (uses vector magnitude if None)

        Returns:
            New Line object
        """
        if length is not None:
            vector = vector.normalize() * length

        end_point = point + vector.to_point()
        return cls(point, end_point)

    @classmethod
    def from_point_and_angle(
        cls, point: Point2D, angle: float, length: float
    ) -> "Line":
        """
        Create line from point, angle, and length.

        Args:
            point: Starting point
            angle: Direction angle in radians
            length: Line length

        Returns:
            New Line object
        """
        direction = Vector2D.from_angle(angle, length)
        end_point = point + direction.to_point()
        return cls(point, end_point)
