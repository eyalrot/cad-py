"""
Arc geometry class implementation.

Provides 2D arc operations for CAD applications including angle calculations,
arc length measurements, and geometric transformations.
"""

import math
from typing import List, Optional, Tuple, Union

import numpy as np

from .circle import Circle
from .point import Point2D
from .vector import Vector2D


class Arc:
    """
    Represents a 2D circular arc defined by center, radius, start angle, and end angle.

    Provides methods for arc calculations, point operations, intersections,
    and geometric transformations commonly used in CAD applications.
    """

    def __init__(
        self,
        center: Point2D,
        radius: float,
        start_angle: float,
        end_angle: float,
        counterclockwise: bool = True,
    ) -> None:
        """
        Initialize an arc.

        Args:
            center: Center point of the arc
            radius: Radius of the arc
            start_angle: Starting angle in radians
            end_angle: Ending angle in radians
            counterclockwise: True for counter-clockwise direction, False for clockwise

        Raises:
            ValueError: If radius is negative or zero
        """
        if radius <= 0:
            raise ValueError("Arc radius must be positive")

        self.center = center
        self.radius = float(radius)
        self.start_angle = float(start_angle)
        self.end_angle = float(end_angle)
        self.counterclockwise = bool(counterclockwise)

        # Normalize angles to [0, 2π]
        self._normalize_angles()

    def _normalize_angles(self) -> None:
        """Normalize angles to [0, 2π] range."""
        self.start_angle = self.start_angle % (2 * math.pi)
        self.end_angle = self.end_angle % (2 * math.pi)

    def __repr__(self) -> str:
        """String representation of the arc."""
        return f"Arc({self.center!r}, {self.radius}, {self.start_angle:.3f}, {self.end_angle:.3f}, {self.counterclockwise})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        direction = "CCW" if self.counterclockwise else "CW"
        return f"Arc[center={self.center}, r={self.radius:.3f}, {math.degrees(self.start_angle):.1f}°→{math.degrees(self.end_angle):.1f}° {direction}]"

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another arc within tolerance.

        Args:
            other: Another Arc object

        Returns:
            True if arcs are equal within tolerance
        """
        if not isinstance(other, Arc):
            return NotImplemented

        tolerance = 1e-10
        return (
            self.center == other.center
            and abs(self.radius - other.radius) < tolerance
            and abs(self.start_angle - other.start_angle) < tolerance
            and abs(self.end_angle - other.end_angle) < tolerance
            and self.counterclockwise == other.counterclockwise
        )

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash(
            (
                self.center,
                round(self.radius, 10),
                round(self.start_angle, 10),
                round(self.end_angle, 10),
                self.counterclockwise,
            )
        )

    def angular_span(self) -> float:
        """
        Calculate the angular span of the arc.

        Returns:
            Angular span in radians (always positive)
        """
        if self.counterclockwise:
            if self.end_angle >= self.start_angle:
                return self.end_angle - self.start_angle
            else:
                return (2 * math.pi) - (self.start_angle - self.end_angle)
        else:
            if self.start_angle >= self.end_angle:
                return self.start_angle - self.end_angle
            else:
                return (2 * math.pi) - (self.end_angle - self.start_angle)

    def arc_length(self) -> float:
        """
        Calculate arc length.

        Returns:
            Arc length (radius * angular_span)
        """
        return self.radius * self.angular_span()

    def chord_length(self) -> float:
        """
        Calculate chord length (straight line distance between endpoints).

        Returns:
            Chord length
        """
        start_point = self.start_point()
        end_point = self.end_point()
        return start_point.distance_to(end_point)

    def sagitta(self) -> float:
        """
        Calculate sagitta (maximum distance from arc to chord).

        Returns:
            Sagitta distance
        """
        span = self.angular_span()
        return self.radius * (1 - math.cos(span / 2))

    def start_point(self) -> Point2D:
        """
        Get the starting point of the arc.

        Returns:
            Starting point on the arc
        """
        x = self.center.x + self.radius * math.cos(self.start_angle)
        y = self.center.y + self.radius * math.sin(self.start_angle)
        return Point2D(x, y)

    def end_point(self) -> Point2D:
        """
        Get the ending point of the arc.

        Returns:
            Ending point on the arc
        """
        x = self.center.x + self.radius * math.cos(self.end_angle)
        y = self.center.y + self.radius * math.sin(self.end_angle)
        return Point2D(x, y)

    def midpoint(self) -> Point2D:
        """
        Get the midpoint of the arc.

        Returns:
            Midpoint on the arc
        """
        mid_angle = self.angle_at_parameter(0.5)
        x = self.center.x + self.radius * math.cos(mid_angle)
        y = self.center.y + self.radius * math.sin(mid_angle)
        return Point2D(x, y)

    def point_at_angle(self, angle: float) -> Point2D:
        """
        Get point on arc at specific angle.

        Args:
            angle: Angle in radians

        Returns:
            Point on arc at given angle

        Raises:
            ValueError: If angle is not within arc range
        """
        if not self.contains_angle(angle):
            raise ValueError("Angle is not within arc range")

        x = self.center.x + self.radius * math.cos(angle)
        y = self.center.y + self.radius * math.sin(angle)
        return Point2D(x, y)

    def point_at_parameter(self, t: float) -> Point2D:
        """
        Get point on arc at parameter t.

        Args:
            t: Parameter (0.0 = start, 1.0 = end)

        Returns:
            Point on arc at parameter t
        """
        angle = self.angle_at_parameter(t)
        x = self.center.x + self.radius * math.cos(angle)
        y = self.center.y + self.radius * math.sin(angle)
        return Point2D(x, y)

    def angle_at_parameter(self, t: float) -> float:
        """
        Get angle at parameter t.

        Args:
            t: Parameter (0.0 = start, 1.0 = end)

        Returns:
            Angle in radians at parameter t
        """
        t = max(0.0, min(1.0, t))  # Clamp to [0, 1]

        if self.counterclockwise:
            if self.end_angle >= self.start_angle:
                return self.start_angle + t * (self.end_angle - self.start_angle)
            else:
                span = (2 * math.pi) - (self.start_angle - self.end_angle)
                angle = self.start_angle + t * span
                return angle % (2 * math.pi)
        else:
            if self.start_angle >= self.end_angle:
                return self.start_angle - t * (self.start_angle - self.end_angle)
            else:
                span = (2 * math.pi) - (self.end_angle - self.start_angle)
                angle = self.start_angle - t * span
                return angle % (2 * math.pi)

    def contains_angle(self, angle: float) -> bool:
        """
        Check if angle is within the arc range.

        Args:
            angle: Angle in radians

        Returns:
            True if angle is within arc range
        """
        angle = angle % (2 * math.pi)

        if self.counterclockwise:
            if self.end_angle >= self.start_angle:
                return self.start_angle <= angle <= self.end_angle
            else:
                return angle >= self.start_angle or angle <= self.end_angle
        else:
            if self.start_angle >= self.end_angle:
                return self.end_angle <= angle <= self.start_angle
            else:
                return angle <= self.start_angle or angle >= self.end_angle

    def contains_point(self, point: Point2D, tolerance: float = 1e-10) -> bool:
        """
        Check if point is on the arc.

        Args:
            point: Point to check
            tolerance: Distance tolerance

        Returns:
            True if point is on arc
        """
        # Check if point is on the circle
        distance = self.center.distance_to(point)
        if abs(distance - self.radius) > tolerance:
            return False

        # Check if point is within arc angle range
        angle = self.center.angle_to(point)
        return self.contains_angle(angle)

    def distance_to_point(self, point: Point2D) -> float:
        """
        Calculate shortest distance from point to arc.

        Args:
            point: Reference point

        Returns:
            Shortest distance to arc
        """
        # Distance to the circle
        center_distance = self.center.distance_to(point)
        circle_distance = abs(center_distance - self.radius)

        # If point projects onto the arc, return circle distance
        angle = self.center.angle_to(point)
        if self.contains_angle(angle):
            return circle_distance

        # Otherwise, return distance to nearest endpoint
        start_dist = point.distance_to(self.start_point())
        end_dist = point.distance_to(self.end_point())
        return min(start_dist, end_dist)

    def closest_point_to(self, point: Point2D) -> Point2D:
        """
        Find closest point on arc to given point.

        Args:
            point: Reference point

        Returns:
            Closest point on arc
        """
        # Check if point projects onto the arc
        angle = self.center.angle_to(point)
        if self.contains_angle(angle):
            # Project onto circle
            if point == self.center:
                return self.start_point()  # Arbitrary choice
            direction = Vector2D.from_points(self.center, point).normalize()
            return self.center + (direction * self.radius).to_point()

        # Return nearest endpoint
        start_point = self.start_point()
        end_point = self.end_point()
        start_dist = point.distance_to(start_point)
        end_dist = point.distance_to(end_point)

        return start_point if start_dist < end_dist else end_point

    def tangent_at_point(self, point: Point2D) -> Vector2D:
        """
        Get tangent vector at point on arc.

        Args:
            point: Point on arc

        Returns:
            Unit tangent vector

        Raises:
            ValueError: If point is not on arc
        """
        if not self.contains_point(point):
            raise ValueError("Point is not on arc")

        # Tangent is perpendicular to radius
        radius_vec = Vector2D.from_points(self.center, point)
        tangent = (
            radius_vec.perpendicular()
            if self.counterclockwise
            else radius_vec.perpendicular_cw()
        )
        return tangent.normalize()

    def tangent_at_angle(self, angle: float) -> Vector2D:
        """
        Get tangent vector at specific angle.

        Args:
            angle: Angle in radians

        Returns:
            Unit tangent vector

        Raises:
            ValueError: If angle is not within arc range
        """
        if not self.contains_angle(angle):
            raise ValueError("Angle is not within arc range")

        if self.counterclockwise:
            return Vector2D(-math.sin(angle), math.cos(angle))
        else:
            return Vector2D(math.sin(angle), -math.cos(angle))

    def normal_at_point(self, point: Point2D) -> Vector2D:
        """
        Get outward normal vector at point on arc.

        Args:
            point: Point on arc

        Returns:
            Unit normal vector (pointing outward)

        Raises:
            ValueError: If point is not on arc
        """
        if not self.contains_point(point):
            raise ValueError("Point is not on arc")

        return Vector2D.from_points(self.center, point).normalize()

    def reverse(self) -> "Arc":
        """
        Create arc with reversed direction.

        Returns:
            New arc with start/end swapped and direction reversed
        """
        return Arc(
            self.center,
            self.radius,
            self.end_angle,
            self.start_angle,
            not self.counterclockwise,
        )

    def to_circle(self) -> Circle:
        """
        Convert arc to full circle.

        Returns:
            Circle with same center and radius
        """
        return Circle(self.center, self.radius)

    def is_full_circle(self, tolerance: float = 1e-10) -> bool:
        """
        Check if arc represents a full circle.

        Args:
            tolerance: Angle tolerance

        Returns:
            True if arc spans full circle
        """
        span = self.angular_span()
        return abs(span - 2 * math.pi) < tolerance

    def translate(self, dx: float, dy: float) -> "Arc":
        """
        Translate arc by given offsets.

        Args:
            dx: X offset
            dy: Y offset

        Returns:
            New translated arc
        """
        new_center = self.center.translate(dx, dy)
        return Arc(
            new_center,
            self.radius,
            self.start_angle,
            self.end_angle,
            self.counterclockwise,
        )

    def rotate(self, angle: float, center: Point2D = None) -> "Arc":
        """
        Rotate arc around a center point.

        Args:
            angle: Rotation angle in radians
            center: Center of rotation (arc center if None)

        Returns:
            New rotated arc
        """
        if center is None:
            center = self.center

        new_center = self.center.rotate(angle, center)
        new_start_angle = (self.start_angle + angle) % (2 * math.pi)
        new_end_angle = (self.end_angle + angle) % (2 * math.pi)

        return Arc(
            new_center,
            self.radius,
            new_start_angle,
            new_end_angle,
            self.counterclockwise,
        )

    def scale(self, factor: float, center: Point2D = None) -> "Arc":
        """
        Scale arc by given factor.

        Args:
            factor: Scale factor
            center: Center of scaling (arc center if None)

        Returns:
            New scaled arc

        Raises:
            ValueError: If scale factor is negative or zero
        """
        if factor <= 0:
            raise ValueError("Scale factor must be positive")

        if center is None:
            center = self.center

        new_center = self.center.scale(factor, factor, center)
        new_radius = self.radius * factor

        return Arc(
            new_center,
            new_radius,
            self.start_angle,
            self.end_angle,
            self.counterclockwise,
        )

    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        """
        Calculate axis-aligned bounding box.

        Returns:
            Tuple of (min_point, max_point)
        """
        # Start with endpoints
        start = self.start_point()
        end = self.end_point()

        min_x = min(start.x, end.x)
        max_x = max(start.x, end.x)
        min_y = min(start.y, end.y)
        max_y = max(start.y, end.y)

        # Check extrema points (0°, 90°, 180°, 270°)
        extrema_angles = [0, math.pi / 2, math.pi, 3 * math.pi / 2]

        for angle in extrema_angles:
            if self.contains_angle(angle):
                x = self.center.x + self.radius * math.cos(angle)
                y = self.center.y + self.radius * math.sin(angle)
                min_x = min(min_x, x)
                max_x = max(max_x, x)
                min_y = min(min_y, y)
                max_y = max(max_y, y)

        return (Point2D(min_x, min_y), Point2D(max_x, max_y))

    def split_at_angle(self, angle: float) -> Tuple["Arc", "Arc"]:
        """
        Split arc at given angle into two arcs.

        Args:
            angle: Split angle in radians

        Returns:
            Tuple of (first_arc, second_arc)

        Raises:
            ValueError: If angle is not within arc range
        """
        if not self.contains_angle(angle):
            raise ValueError("Split angle is not within arc range")

        arc1 = Arc(
            self.center, self.radius, self.start_angle, angle, self.counterclockwise
        )
        arc2 = Arc(
            self.center, self.radius, angle, self.end_angle, self.counterclockwise
        )

        return (arc1, arc2)

    def to_tuple(self) -> Tuple[Tuple[float, float], float, float, float, bool]:
        """
        Convert arc to tuple representation.

        Returns:
            ((center_x, center_y), radius, start_angle, end_angle, counterclockwise)
        """
        return (
            self.center.to_tuple(),
            self.radius,
            self.start_angle,
            self.end_angle,
            self.counterclockwise,
        )

    @classmethod
    def from_tuple(
        cls, data: Tuple[Tuple[float, float], float, float, float, bool]
    ) -> "Arc":
        """
        Create arc from tuple representation.

        Args:
            data: ((center_x, center_y), radius, start_angle, end_angle, counterclockwise)

        Returns:
            New Arc object
        """
        center = Point2D.from_tuple(data[0])
        return cls(center, data[1], data[2], data[3], data[4])

    @classmethod
    def from_three_points(cls, p1: Point2D, p2: Point2D, p3: Point2D) -> "Arc":
        """
        Create arc passing through three points.

        Args:
            p1: First point (start)
            p2: Second point (on arc)
            p3: Third point (end)

        Returns:
            Arc passing through all three points

        Raises:
            ValueError: If points are collinear
        """
        # Create circle through three points
        circle = Circle.from_three_points(p1, p2, p3)

        # Calculate angles
        start_angle = circle.center.angle_to(p1)
        end_angle = circle.center.angle_to(p3)
        mid_angle = circle.center.angle_to(p2)

        # Determine direction by checking if middle point is between start and end
        # when going counter-clockwise
        def angle_between_ccw(start: float, end: float, test: float) -> bool:
            start = start % (2 * math.pi)
            end = end % (2 * math.pi)
            test = test % (2 * math.pi)

            if end >= start:
                return start <= test <= end
            else:
                return test >= start or test <= end

        counterclockwise = angle_between_ccw(start_angle, end_angle, mid_angle)

        return cls(
            circle.center, circle.radius, start_angle, end_angle, counterclockwise
        )

    @classmethod
    def from_center_start_end(
        cls,
        center: Point2D,
        start: Point2D,
        end: Point2D,
        counterclockwise: bool = True,
    ) -> "Arc":
        """
        Create arc from center and two points.

        Args:
            center: Arc center
            start: Start point
            end: End point
            counterclockwise: Direction of arc

        Returns:
            New Arc object
        """
        radius = center.distance_to(start)
        start_angle = center.angle_to(start)
        end_angle = center.angle_to(end)

        return cls(center, radius, start_angle, end_angle, counterclockwise)
