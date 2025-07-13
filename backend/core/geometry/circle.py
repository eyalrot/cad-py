"""
Circle geometry class implementation.

Provides 2D circle operations for CAD applications including area calculations,
intersection detection, and geometric transformations.
"""

import math
from typing import List, Optional, Tuple, Union
import numpy as np
from .point import Point2D
from .vector import Vector2D


class Circle:
    """
    Represents a 2D circle defined by center point and radius.
    
    Provides methods for area/circumference calculations, point containment tests,
    intersections, and geometric operations commonly used in CAD applications.
    """
    
    def __init__(self, center: Point2D, radius: float) -> None:
        """
        Initialize a circle.
        
        Args:
            center: Center point of the circle
            radius: Radius of the circle
            
        Raises:
            ValueError: If radius is negative or zero
        """
        if radius <= 0:
            raise ValueError("Circle radius must be positive")
        
        self.center = center
        self.radius = float(radius)
    
    def __repr__(self) -> str:
        """String representation of the circle."""
        return f"Circle({self.center!r}, {self.radius})"
    
    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"Circle[center={self.center}, radius={self.radius:.3f}]"
    
    def __eq__(self, other: object) -> bool:
        """
        Check equality with another circle within tolerance.
        
        Args:
            other: Another Circle object
            
        Returns:
            True if circles are equal within tolerance
        """
        if not isinstance(other, Circle):
            return NotImplemented
        
        tolerance = 1e-10
        return (self.center == other.center and 
                abs(self.radius - other.radius) < tolerance)
    
    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((self.center, round(self.radius, 10)))
    
    def area(self) -> float:
        """
        Calculate circle area.
        
        Returns:
            Circle area (π * r²)
        """
        return math.pi * self.radius * self.radius
    
    def circumference(self) -> float:
        """
        Calculate circle circumference.
        
        Returns:
            Circle circumference (2 * π * r)
        """
        return 2 * math.pi * self.radius
    
    def diameter(self) -> float:
        """
        Get circle diameter.
        
        Returns:
            Circle diameter (2 * r)
        """
        return 2 * self.radius
    
    def contains_point(self, point: Point2D, tolerance: float = 1e-10) -> bool:
        """
        Check if point is inside the circle.
        
        Args:
            point: Point to check
            tolerance: Distance tolerance for boundary
            
        Returns:
            True if point is inside or on circle boundary
        """
        distance = self.center.distance_to(point)
        return distance <= self.radius + tolerance
    
    def point_on_circle(self, point: Point2D, tolerance: float = 1e-10) -> bool:
        """
        Check if point is on the circle circumference.
        
        Args:
            point: Point to check
            tolerance: Distance tolerance
            
        Returns:
            True if point is on circle circumference
        """
        distance = self.center.distance_to(point)
        return abs(distance - self.radius) < tolerance
    
    def distance_to_point(self, point: Point2D) -> float:
        """
        Calculate shortest distance from point to circle.
        
        Args:
            point: Reference point
            
        Returns:
            Distance to circle (negative if inside, 0 if on circumference)
        """
        center_distance = self.center.distance_to(point)
        return center_distance - self.radius
    
    def closest_point_to(self, point: Point2D) -> Point2D:
        """
        Find closest point on circle to given point.
        
        Args:
            point: Reference point
            
        Returns:
            Closest point on circle circumference
        """
        if point == self.center:
            # Point is at center, return arbitrary point on circle
            return Point2D(self.center.x + self.radius, self.center.y)
        
        # Direction from center to point
        direction = Vector2D.from_points(self.center, point).normalize()
        
        # Point on circle in that direction
        return self.center + (direction * self.radius).to_point()
    
    def point_at_angle(self, angle: float) -> Point2D:
        """
        Get point on circle at given angle from positive x-axis.
        
        Args:
            angle: Angle in radians
            
        Returns:
            Point on circle circumference
        """
        x = self.center.x + self.radius * math.cos(angle)
        y = self.center.y + self.radius * math.sin(angle)
        return Point2D(x, y)
    
    def angle_of_point(self, point: Point2D) -> float:
        """
        Get angle of point on circle from positive x-axis.
        
        Args:
            point: Point on circle
            
        Returns:
            Angle in radians (-π to π)
            
        Raises:
            ValueError: If point is not on circle
        """
        if not self.point_on_circle(point):
            raise ValueError("Point is not on circle")
        
        return self.center.angle_to(point)
    
    def tangent_at_point(self, point: Point2D) -> Vector2D:
        """
        Get tangent vector at point on circle.
        
        Args:
            point: Point on circle
            
        Returns:
            Unit tangent vector (counter-clockwise direction)
            
        Raises:
            ValueError: If point is not on circle
        """
        if not self.point_on_circle(point):
            raise ValueError("Point is not on circle")
        
        # Tangent is perpendicular to radius
        radius_vec = Vector2D.from_points(self.center, point)
        return radius_vec.perpendicular().normalize()
    
    def normal_at_point(self, point: Point2D) -> Vector2D:
        """
        Get outward normal vector at point on circle.
        
        Args:
            point: Point on circle
            
        Returns:
            Unit normal vector (pointing outward)
            
        Raises:
            ValueError: If point is not on circle
        """
        if not self.point_on_circle(point):
            raise ValueError("Point is not on circle")
        
        return Vector2D.from_points(self.center, point).normalize()
    
    def intersection_with_line(self, line) -> List[Point2D]:
        """
        Find intersection points with a line segment.
        
        Args:
            line: Line object to intersect with
            
        Returns:
            List of intersection points (0, 1, or 2 points)
        """
        # This uses the line's intersection method
        return line.intersections_with_circle(self.center, self.radius)
    
    def intersection_with_circle(self, other: 'Circle') -> List[Point2D]:
        """
        Find intersection points with another circle.
        
        Args:
            other: Other circle to intersect with
            
        Returns:
            List of intersection points (0, 1, or 2 points)
        """
        # Distance between centers
        d = self.center.distance_to(other.center)
        
        # Check for no intersection cases
        if d > self.radius + other.radius + 1e-10:
            return []  # Circles too far apart
        
        if d < abs(self.radius - other.radius) - 1e-10:
            return []  # One circle inside the other
        
        if d < 1e-10 and abs(self.radius - other.radius) < 1e-10:
            return []  # Identical circles (infinite intersections)
        
        # Check for single intersection (tangent circles)
        if abs(d - (self.radius + other.radius)) < 1e-10 or \
           abs(d - abs(self.radius - other.radius)) < 1e-10:
            # Single intersection point
            ratio = self.radius / d
            direction = Vector2D.from_points(self.center, other.center).normalize()
            intersection = self.center + (direction * self.radius).to_point()
            return [intersection]
        
        # Two intersection points
        # Using the formula for circle-circle intersection
        a = (self.radius * self.radius - other.radius * other.radius + d * d) / (2 * d)
        h = math.sqrt(self.radius * self.radius - a * a)
        
        # Point on line between centers
        direction = Vector2D.from_points(self.center, other.center).normalize()
        p = self.center + (direction * a).to_point()
        
        # Perpendicular direction
        perp = direction.perpendicular()
        
        # Two intersection points
        p1 = p + (perp * h).to_point()
        p2 = p - (perp * h).to_point()
        
        return [p1, p2]
    
    def is_tangent_to_circle(self, other: 'Circle', tolerance: float = 1e-10) -> bool:
        """
        Check if this circle is tangent to another circle.
        
        Args:
            other: Other circle
            tolerance: Distance tolerance
            
        Returns:
            True if circles are tangent
        """
        d = self.center.distance_to(other.center)
        
        # External tangency
        external_tangent = abs(d - (self.radius + other.radius)) < tolerance
        
        # Internal tangency
        internal_tangent = abs(d - abs(self.radius - other.radius)) < tolerance
        
        return external_tangent or internal_tangent
    
    def is_concentric_with(self, other: 'Circle', tolerance: float = 1e-10) -> bool:
        """
        Check if this circle is concentric with another circle.
        
        Args:
            other: Other circle
            tolerance: Distance tolerance
            
        Returns:
            True if circles have same center
        """
        return self.center.distance_to(other.center) < tolerance
    
    def translate(self, dx: float, dy: float) -> 'Circle':
        """
        Translate circle by given offsets.
        
        Args:
            dx: X offset
            dy: Y offset
            
        Returns:
            New translated circle
        """
        new_center = self.center.translate(dx, dy)
        return Circle(new_center, self.radius)
    
    def scale(self, factor: float, center: Point2D = None) -> 'Circle':
        """
        Scale circle by given factor.
        
        Args:
            factor: Scale factor
            center: Center of scaling (circle center if None)
            
        Returns:
            New scaled circle
            
        Raises:
            ValueError: If scale factor is negative or zero
        """
        if factor <= 0:
            raise ValueError("Scale factor must be positive")
        
        if center is None:
            center = self.center
        
        new_center = self.center.scale(factor, factor, center)
        new_radius = self.radius * factor
        
        return Circle(new_center, new_radius)
    
    def expand(self, amount: float) -> 'Circle':
        """
        Expand or contract circle radius by given amount.
        
        Args:
            amount: Amount to add to radius (negative to contract)
            
        Returns:
            New circle with modified radius
            
        Raises:
            ValueError: If resulting radius would be negative or zero
        """
        new_radius = self.radius + amount
        if new_radius <= 0:
            raise ValueError("Expanded radius must be positive")
        
        return Circle(self.center, new_radius)
    
    def arc_length(self, start_angle: float, end_angle: float) -> float:
        """
        Calculate arc length between two angles.
        
        Args:
            start_angle: Starting angle in radians
            end_angle: Ending angle in radians
            
        Returns:
            Arc length
        """
        # Normalize angle difference to [0, 2π]
        angle_diff = end_angle - start_angle
        while angle_diff < 0:
            angle_diff += 2 * math.pi
        while angle_diff > 2 * math.pi:
            angle_diff -= 2 * math.pi
        
        return self.radius * angle_diff
    
    def chord_length(self, start_angle: float, end_angle: float) -> float:
        """
        Calculate chord length between two angles.
        
        Args:
            start_angle: Starting angle in radians
            end_angle: Ending angle in radians
            
        Returns:
            Chord length
        """
        p1 = self.point_at_angle(start_angle)
        p2 = self.point_at_angle(end_angle)
        return p1.distance_to(p2)
    
    def sector_area(self, start_angle: float, end_angle: float) -> float:
        """
        Calculate sector area between two angles.
        
        Args:
            start_angle: Starting angle in radians
            end_angle: Ending angle in radians
            
        Returns:
            Sector area
        """
        # Normalize angle difference to [0, 2π]
        angle_diff = end_angle - start_angle
        while angle_diff < 0:
            angle_diff += 2 * math.pi
        while angle_diff > 2 * math.pi:
            angle_diff -= 2 * math.pi
        
        return 0.5 * self.radius * self.radius * angle_diff
    
    def bounding_box(self) -> Tuple[Point2D, Point2D]:
        """
        Calculate axis-aligned bounding box.
        
        Returns:
            Tuple of (min_point, max_point)
        """
        min_point = Point2D(
            self.center.x - self.radius,
            self.center.y - self.radius
        )
        max_point = Point2D(
            self.center.x + self.radius,
            self.center.y + self.radius
        )
        return (min_point, max_point)
    
    def to_tuple(self) -> Tuple[Tuple[float, float], float]:
        """
        Convert circle to tuple representation.
        
        Returns:
            ((center_x, center_y), radius)
        """
        return (self.center.to_tuple(), self.radius)
    
    @classmethod
    def from_tuple(cls, data: Tuple[Tuple[float, float], float]) -> 'Circle':
        """
        Create circle from tuple representation.
        
        Args:
            data: ((center_x, center_y), radius)
            
        Returns:
            New Circle object
        """
        center = Point2D.from_tuple(data[0])
        radius = data[1]
        return cls(center, radius)
    
    @classmethod
    def from_three_points(cls, p1: Point2D, p2: Point2D, p3: Point2D) -> 'Circle':
        """
        Create circle passing through three points.
        
        Args:
            p1: First point
            p2: Second point
            p3: Third point
            
        Returns:
            Circle passing through all three points
            
        Raises:
            ValueError: If points are collinear
        """
        # Check if points are collinear
        v1 = Vector2D.from_points(p1, p2)
        v2 = Vector2D.from_points(p1, p3)
        
        if abs(v1.cross(v2)) < 1e-10:
            raise ValueError("Cannot create circle from collinear points")
        
        # Calculate circumcenter using perpendicular bisectors
        # Midpoints of two chords
        mid12 = p1.midpoint(p2)
        mid13 = p1.midpoint(p3)
        
        # Perpendicular directions
        perp12 = Vector2D.from_points(p1, p2).perpendicular()
        perp13 = Vector2D.from_points(p1, p3).perpendicular()
        
        # Create lines for perpendicular bisectors
        from .line import Line  # Import here to avoid circular import
        
        # Find intersection of perpendicular bisectors
        line12 = Line.from_point_and_vector(mid12, perp12, 1.0)
        line13 = Line.from_point_and_vector(mid13, perp13, 1.0)
        
        center = line12.intersection_infinite(line13)
        if center is None:
            raise ValueError("Cannot find circle center (perpendicular bisectors are parallel)")
        
        radius = center.distance_to(p1)
        return cls(center, radius)
    
    @classmethod
    def from_center_and_point(cls, center: Point2D, point: Point2D) -> 'Circle':
        """
        Create circle with given center passing through a point.
        
        Args:
            center: Circle center
            point: Point on circle
            
        Returns:
            New Circle object
        """
        radius = center.distance_to(point)
        return cls(center, radius)
    
    @classmethod
    def from_diameter(cls, p1: Point2D, p2: Point2D) -> 'Circle':
        """
        Create circle with given diameter endpoints.
        
        Args:
            p1: First diameter endpoint
            p2: Second diameter endpoint
            
        Returns:
            New Circle object
        """
        center = p1.midpoint(p2)
        radius = p1.distance_to(p2) / 2
        return cls(center, radius)