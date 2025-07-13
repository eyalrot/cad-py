"""
Advanced geometry operations for CAD modifications.

This module provides comprehensive geometric calculations and operations
for advanced modification tools like trim, extend, offset, fillet, and chamfer.
"""

import logging
import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Tuple, Union

from ..core.entities.arc import Arc
from ..core.entities.base_entity import BaseEntity
from ..core.entities.circle import Circle
from ..core.entities.line import Line
from ..core.geometry.point import Point2D
from ..core.geometry.vector import Vector2D

logger = logging.getLogger(__name__)


class OperationResult(Enum):
    """Results of geometry operations."""

    SUCCESS = auto()
    NO_INTERSECTION = auto()
    INVALID_PARAMETERS = auto()
    UNSUPPORTED_ENTITY = auto()
    GEOMETRY_ERROR = auto()


@dataclass
class IntersectionPoint:
    """Represents an intersection point between two entities."""

    point: Point2D
    parameter1: float  # Parameter on first entity [0, 1]
    parameter2: float  # Parameter on second entity [0, 1]
    tangent: bool = False  # Whether intersection is tangent


@dataclass
class TrimResult:
    """Result of a trim operation."""

    result: OperationResult
    trimmed_entities: List[BaseEntity]
    message: str = ""


@dataclass
class OffsetResult:
    """Result of an offset operation."""

    result: OperationResult
    offset_entity: Optional[BaseEntity]
    message: str = ""


@dataclass
class FilletResult:
    """Result of a fillet operation."""

    result: OperationResult
    fillet_arc: Optional[Arc]
    trimmed_entities: List[BaseEntity]
    message: str = ""


class GeometryOperations:
    """
    Advanced geometry operations for CAD modifications.

    Provides static methods for:
    - Trimming entities to boundaries
    - Extending entities to boundaries
    - Creating offset curves
    - Creating fillets between entities
    - Creating chamfers between entities
    """

    @staticmethod
    def find_intersections(
        entity1: BaseEntity, entity2: BaseEntity
    ) -> List[IntersectionPoint]:
        """
        Find intersection points between two entities.

        Args:
            entity1: First entity
            entity2: Second entity

        Returns:
            List of intersection points with parameters
        """
        intersections = []

        try:
            if isinstance(entity1, Line) and isinstance(entity2, Line):
                intersections = GeometryOperations._line_line_intersection(
                    entity1, entity2
                )
            elif isinstance(entity1, Line) and isinstance(entity2, (Arc, Circle)):
                intersections = GeometryOperations._line_arc_intersection(
                    entity1, entity2
                )
            elif isinstance(entity1, (Arc, Circle)) and isinstance(entity2, Line):
                intersections = GeometryOperations._line_arc_intersection(
                    entity2, entity1
                )
                # Swap parameters for correct order
                for intersection in intersections:
                    intersection.parameter1, intersection.parameter2 = (
                        intersection.parameter2,
                        intersection.parameter1,
                    )
            elif isinstance(entity1, (Arc, Circle)) and isinstance(
                entity2, (Arc, Circle)
            ):
                intersections = GeometryOperations._arc_arc_intersection(
                    entity1, entity2
                )

        except Exception as e:
            logger.error(f"Error finding intersections: {e}")

        return intersections

    @staticmethod
    def _line_line_intersection(line1: Line, line2: Line) -> List[IntersectionPoint]:
        """Find intersection between two lines."""
        p1 = line1.start_point
        p2 = line1.end_point
        p3 = line2.start_point
        p4 = line2.end_point

        # Direction vectors
        d1 = Vector2D(p2.x - p1.x, p2.y - p1.y)
        d2 = Vector2D(p4.x - p3.x, p4.y - p3.y)

        # Calculate determinant
        det = d1.x * d2.y - d1.y * d2.x

        if abs(det) < 1e-10:  # Lines are parallel
            return []

        # Calculate parameters
        dp = Vector2D(p3.x - p1.x, p3.y - p1.y)
        t1 = (dp.x * d2.y - dp.y * d2.x) / det
        t2 = (dp.x * d1.y - dp.y * d1.x) / det

        # Check if intersection is within both line segments
        if 0 <= t1 <= 1 and 0 <= t2 <= 1:
            intersection_point = Point2D(p1.x + t1 * d1.x, p1.y + t1 * d1.y)
            return [IntersectionPoint(intersection_point, t1, t2)]

        return []

    @staticmethod
    def _line_arc_intersection(
        line: Line, arc: Union[Arc, Circle]
    ) -> List[IntersectionPoint]:
        """Find intersections between line and arc/circle."""
        intersections = []

        # Line parameters
        start = line.start_point
        end = line.end_point
        dx = end.x - start.x
        dy = end.y - start.y

        # Arc/circle parameters
        center = arc.center_point
        radius = arc.radius

        # Translate line to circle origin
        fx = start.x - center.x
        fy = start.y - center.y

        # Quadratic equation coefficients: at² + bt + c = 0
        a = dx * dx + dy * dy
        b = 2 * (fx * dx + fy * dy)
        c = fx * fx + fy * fy - radius * radius

        discriminant = b * b - 4 * a * c

        if discriminant < 0:
            return []  # No intersection

        sqrt_discriminant = math.sqrt(discriminant)

        # Find intersection parameters
        t1 = (-b - sqrt_discriminant) / (2 * a)
        t2 = (-b + sqrt_discriminant) / (2 * a)

        for t in [t1, t2]:
            if 0 <= t <= 1:  # Within line segment
                point = Point2D(start.x + t * dx, start.y + t * dy)

                # Check if point is within arc bounds (for arcs, not circles)
                if isinstance(arc, Arc):
                    angle = math.atan2(point.y - center.y, point.x - center.x)
                    angle = GeometryOperations._normalize_angle(angle)

                    start_angle = GeometryOperations._normalize_angle(arc.start_angle)
                    end_angle = GeometryOperations._normalize_angle(arc.end_angle)

                    if not GeometryOperations._angle_in_arc_range(
                        angle, start_angle, end_angle
                    ):
                        continue

                # Calculate parameter on arc (0 = start, 1 = end)
                if isinstance(arc, Circle):
                    arc_param = 0.0  # Circles don't have a natural parameter
                else:
                    arc_param = GeometryOperations._point_to_arc_parameter(point, arc)

                intersections.append(IntersectionPoint(point, t, arc_param))

        return intersections

    @staticmethod
    def _arc_arc_intersection(
        arc1: Union[Arc, Circle], arc2: Union[Arc, Circle]
    ) -> List[IntersectionPoint]:
        """Find intersections between two arcs/circles."""
        center1 = arc1.center_point
        center2 = arc2.center_point
        r1 = arc1.radius
        r2 = arc2.radius

        # Distance between centers
        d = math.sqrt((center2.x - center1.x) ** 2 + (center2.y - center1.y) ** 2)

        # No intersection cases
        if d > r1 + r2:  # Too far apart
            return []
        if d < abs(r1 - r2):  # One circle inside the other
            return []
        if d == 0 and r1 == r2:  # Same circle
            return []

        # Calculate intersection points
        a = (r1 * r1 - r2 * r2 + d * d) / (2 * d)
        h = math.sqrt(r1 * r1 - a * a)

        # Point on line between centers
        px = center1.x + a * (center2.x - center1.x) / d
        py = center1.y + a * (center2.y - center1.y) / d

        # Intersection points
        intersections = []

        if h == 0:  # Single intersection (tangent)
            point = Point2D(px, py)
            param1 = (
                GeometryOperations._point_to_arc_parameter(point, arc1)
                if isinstance(arc1, Arc)
                else 0.0
            )
            param2 = (
                GeometryOperations._point_to_arc_parameter(point, arc2)
                if isinstance(arc2, Arc)
                else 0.0
            )
            intersections.append(IntersectionPoint(point, param1, param2, tangent=True))
        else:  # Two intersections
            # First intersection
            point1 = Point2D(
                px + h * (center2.y - center1.y) / d,
                py - h * (center2.x - center1.x) / d,
            )

            # Second intersection
            point2 = Point2D(
                px - h * (center2.y - center1.y) / d,
                py + h * (center2.x - center1.x) / d,
            )

            for point in [point1, point2]:
                # Check if points are within arc bounds
                valid1 = isinstance(arc1, Circle) or GeometryOperations._point_on_arc(
                    point, arc1
                )
                valid2 = isinstance(arc2, Circle) or GeometryOperations._point_on_arc(
                    point, arc2
                )

                if valid1 and valid2:
                    param1 = (
                        GeometryOperations._point_to_arc_parameter(point, arc1)
                        if isinstance(arc1, Arc)
                        else 0.0
                    )
                    param2 = (
                        GeometryOperations._point_to_arc_parameter(point, arc2)
                        if isinstance(arc2, Arc)
                        else 0.0
                    )
                    intersections.append(IntersectionPoint(point, param1, param2))

        return intersections

    @staticmethod
    def trim_entity(
        entity: BaseEntity, boundary: BaseEntity, pick_point: Point2D
    ) -> TrimResult:
        """
        Trim entity to boundary at the side indicated by pick point.

        Args:
            entity: Entity to trim
            boundary: Boundary entity to trim to
            pick_point: Point indicating which portion to keep

        Returns:
            TrimResult with trimmed entities
        """
        try:
            intersections = GeometryOperations.find_intersections(entity, boundary)

            if not intersections:
                return TrimResult(
                    OperationResult.NO_INTERSECTION, [], "No intersection found"
                )

            # Find closest intersection to pick point
            closest_intersection = min(
                intersections,
                key=lambda i: GeometryOperations._point_distance(i.point, pick_point),
            )

            # Determine which portion to keep based on pick point
            if isinstance(entity, Line):
                trimmed = GeometryOperations._trim_line(
                    entity, closest_intersection, pick_point
                )
            elif isinstance(entity, Arc):
                trimmed = GeometryOperations._trim_arc(
                    entity, closest_intersection, pick_point
                )
            else:
                return TrimResult(
                    OperationResult.UNSUPPORTED_ENTITY,
                    [],
                    f"Trimming not supported for {type(entity).__name__}",
                )

            if trimmed:
                return TrimResult(
                    OperationResult.SUCCESS, [trimmed], "Entity trimmed successfully"
                )
            else:
                return TrimResult(
                    OperationResult.GEOMETRY_ERROR, [], "Failed to trim entity"
                )

        except Exception as e:
            logger.error(f"Error trimming entity: {e}")
            return TrimResult(OperationResult.GEOMETRY_ERROR, [], str(e))

    @staticmethod
    def extend_entity(entity: BaseEntity, boundary: BaseEntity) -> TrimResult:
        """
        Extend entity to meet boundary.

        Args:
            entity: Entity to extend
            boundary: Boundary to extend to

        Returns:
            TrimResult with extended entity
        """
        try:
            if isinstance(entity, Line):
                extended = GeometryOperations._extend_line(entity, boundary)
            else:
                return TrimResult(
                    OperationResult.UNSUPPORTED_ENTITY,
                    [],
                    f"Extension not supported for {type(entity).__name__}",
                )

            if extended:
                return TrimResult(
                    OperationResult.SUCCESS, [extended], "Entity extended successfully"
                )
            else:
                return TrimResult(
                    OperationResult.NO_INTERSECTION, [], "No valid extension found"
                )

        except Exception as e:
            logger.error(f"Error extending entity: {e}")
            return TrimResult(OperationResult.GEOMETRY_ERROR, [], str(e))

    @staticmethod
    def offset_curve(
        entity: BaseEntity, distance: float, side_point: Point2D
    ) -> OffsetResult:
        """
        Create parallel curve at specified distance.

        Args:
            entity: Entity to offset
            distance: Offset distance
            side_point: Point indicating which side to offset

        Returns:
            OffsetResult with offset entity
        """
        try:
            if isinstance(entity, Line):
                offset_entity = GeometryOperations._offset_line(
                    entity, distance, side_point
                )
            elif isinstance(entity, Arc):
                offset_entity = GeometryOperations._offset_arc(
                    entity, distance, side_point
                )
            elif isinstance(entity, Circle):
                offset_entity = GeometryOperations._offset_circle(
                    entity, distance, side_point
                )
            else:
                return OffsetResult(
                    OperationResult.UNSUPPORTED_ENTITY,
                    None,
                    f"Offset not supported for {type(entity).__name__}",
                )

            if offset_entity:
                return OffsetResult(
                    OperationResult.SUCCESS, offset_entity, "Entity offset successfully"
                )
            else:
                return OffsetResult(
                    OperationResult.INVALID_PARAMETERS,
                    None,
                    "Invalid offset parameters",
                )

        except Exception as e:
            logger.error(f"Error offsetting entity: {e}")
            return OffsetResult(OperationResult.GEOMETRY_ERROR, None, str(e))

    @staticmethod
    def create_fillet(
        entity1: BaseEntity, entity2: BaseEntity, radius: float
    ) -> FilletResult:
        """
        Create fillet arc between two entities.

        Args:
            entity1: First entity
            entity2: Second entity
            radius: Fillet radius

        Returns:
            FilletResult with fillet arc and trimmed entities
        """
        try:
            if not isinstance(entity1, Line) or not isinstance(entity2, Line):
                return FilletResult(
                    OperationResult.UNSUPPORTED_ENTITY,
                    None,
                    [],
                    "Fillet only supported between lines",
                )

            # Find intersection point
            intersections = GeometryOperations.find_intersections(entity1, entity2)
            if not intersections:
                return FilletResult(
                    OperationResult.NO_INTERSECTION, None, [], "Lines do not intersect"
                )

            intersection = intersections[0]

            # Calculate fillet
            fillet_result = GeometryOperations._calculate_line_fillet(
                entity1, entity2, intersection.point, radius
            )

            if fillet_result:
                fillet_arc, trimmed_line1, trimmed_line2 = fillet_result
                return FilletResult(
                    OperationResult.SUCCESS,
                    fillet_arc,
                    [trimmed_line1, trimmed_line2],
                    "Fillet created successfully",
                )
            else:
                return FilletResult(
                    OperationResult.INVALID_PARAMETERS,
                    None,
                    [],
                    "Invalid fillet parameters",
                )

        except Exception as e:
            logger.error(f"Error creating fillet: {e}")
            return FilletResult(OperationResult.GEOMETRY_ERROR, None, [], str(e))

    @staticmethod
    def create_chamfer(
        entity1: BaseEntity, entity2: BaseEntity, distance1: float, distance2: float
    ) -> TrimResult:
        """
        Create chamfer between two entities.

        Args:
            entity1: First entity
            entity2: Second entity
            distance1: Chamfer distance on first entity
            distance2: Chamfer distance on second entity

        Returns:
            TrimResult with chamfer line and trimmed entities
        """
        try:
            if not isinstance(entity1, Line) or not isinstance(entity2, Line):
                return TrimResult(
                    OperationResult.UNSUPPORTED_ENTITY,
                    [],
                    "Chamfer only supported between lines",
                )

            # Find intersection point
            intersections = GeometryOperations.find_intersections(entity1, entity2)
            if not intersections:
                return TrimResult(
                    OperationResult.NO_INTERSECTION, [], "Lines do not intersect"
                )

            intersection = intersections[0]

            # Calculate chamfer
            chamfer_result = GeometryOperations._calculate_line_chamfer(
                entity1, entity2, intersection.point, distance1, distance2
            )

            if chamfer_result:
                chamfer_line, trimmed_line1, trimmed_line2 = chamfer_result
                return TrimResult(
                    OperationResult.SUCCESS,
                    [chamfer_line, trimmed_line1, trimmed_line2],
                    "Chamfer created successfully",
                )
            else:
                return TrimResult(
                    OperationResult.INVALID_PARAMETERS, [], "Invalid chamfer parameters"
                )

        except Exception as e:
            logger.error(f"Error creating chamfer: {e}")
            return TrimResult(OperationResult.GEOMETRY_ERROR, [], str(e))

    # Helper methods
    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """Normalize angle to [0, 2π) range."""
        while angle < 0:
            angle += 2 * math.pi
        while angle >= 2 * math.pi:
            angle -= 2 * math.pi
        return angle

    @staticmethod
    def _angle_in_arc_range(angle: float, start_angle: float, end_angle: float) -> bool:
        """Check if angle is within arc range."""
        angle = GeometryOperations._normalize_angle(angle)
        start_angle = GeometryOperations._normalize_angle(start_angle)
        end_angle = GeometryOperations._normalize_angle(end_angle)

        if start_angle <= end_angle:
            return start_angle <= angle <= end_angle
        else:  # Arc crosses 0 degrees
            return angle >= start_angle or angle <= end_angle

    @staticmethod
    def _point_to_arc_parameter(point: Point2D, arc: Arc) -> float:
        """Convert point on arc to parameter [0, 1]."""
        angle = math.atan2(point.y - arc.center_point.y, point.x - arc.center_point.x)
        angle = GeometryOperations._normalize_angle(angle)

        start_angle = GeometryOperations._normalize_angle(arc.start_angle)
        end_angle = GeometryOperations._normalize_angle(arc.end_angle)

        if start_angle <= end_angle:
            arc_span = end_angle - start_angle
            param = (angle - start_angle) / arc_span if arc_span > 0 else 0
        else:  # Arc crosses 0 degrees
            if angle >= start_angle:
                param = (angle - start_angle) / (2 * math.pi - start_angle + end_angle)
            else:
                param = (2 * math.pi - start_angle + angle) / (
                    2 * math.pi - start_angle + end_angle
                )

        return max(0, min(1, param))

    @staticmethod
    def _point_on_arc(point: Point2D, arc: Arc) -> bool:
        """Check if point is on arc."""
        # Check distance from center
        distance = math.sqrt(
            (point.x - arc.center_point.x) ** 2 + (point.y - arc.center_point.y) ** 2
        )
        if abs(distance - arc.radius) > 1e-6:
            return False

        # Check angle range
        angle = math.atan2(point.y - arc.center_point.y, point.x - arc.center_point.x)
        return GeometryOperations._angle_in_arc_range(
            angle, arc.start_angle, arc.end_angle
        )

    @staticmethod
    def _point_distance(p1: Point2D, p2: Point2D) -> float:
        """Calculate distance between two points."""
        return math.sqrt((p1.x - p2.x) ** 2 + (p1.y - p2.y) ** 2)

    @staticmethod
    def _trim_line(
        line: Line, intersection: IntersectionPoint, pick_point: Point2D
    ) -> Optional[Line]:
        """Trim line at intersection point."""
        # Determine which portion to keep based on pick point
        start_distance = GeometryOperations._point_distance(
            pick_point, line.start_point
        )
        end_distance = GeometryOperations._point_distance(pick_point, line.end_point)

        if start_distance < end_distance:
            # Keep start portion
            return Line(line.start_point, intersection.point)
        else:
            # Keep end portion
            return Line(intersection.point, line.end_point)

    @staticmethod
    def _trim_arc(
        arc: Arc, intersection: IntersectionPoint, pick_point: Point2D
    ) -> Optional[Arc]:
        """Trim arc at intersection point."""
        # Calculate angle of intersection point
        intersection_angle = math.atan2(
            intersection.point.y - arc.center_point.y,
            intersection.point.x - arc.center_point.x,
        )

        # Determine which portion to keep based on pick point
        pick_angle = math.atan2(
            pick_point.y - arc.center_point.y, pick_point.x - arc.center_point.x
        )

        # Create new arc with appropriate start/end angles
        if GeometryOperations._angle_in_arc_range(
            pick_angle, arc.start_angle, intersection_angle
        ):
            # Keep start portion
            return Arc(
                arc.center_point, arc.radius, arc.start_angle, intersection_angle
            )
        else:
            # Keep end portion
            return Arc(arc.center_point, arc.radius, intersection_angle, arc.end_angle)

    @staticmethod
    def _extend_line(line: Line, boundary: BaseEntity) -> Optional[Line]:
        """Extend line to meet boundary."""
        # Create infinite line for intersection testing
        direction = Vector2D(
            line.end_point.x - line.start_point.x, line.end_point.y - line.start_point.y
        )
        direction = direction.normalize()

        # Extend line in both directions and find intersections
        extended_start = Point2D(
            line.start_point.x - direction.x * 10000,
            line.start_point.y - direction.y * 10000,
        )
        extended_end = Point2D(
            line.end_point.x + direction.x * 10000,
            line.end_point.y + direction.y * 10000,
        )

        extended_line = Line(extended_start, extended_end)
        intersections = GeometryOperations.find_intersections(extended_line, boundary)

        if not intersections:
            return None

        # Find the closest intersection beyond the current line endpoints
        valid_intersections = []
        for intersection in intersections:
            # Check if intersection is beyond line endpoints
            param = intersection.parameter1
            extended_length = GeometryOperations._point_distance(
                extended_start, extended_end
            )
            line_length = GeometryOperations._point_distance(
                line.start_point, line.end_point
            )

            # Calculate where original line endpoints are on extended line
            start_param = 10000 / extended_length
            end_param = (10000 + line_length) / extended_length

            if param > end_param:  # Beyond end point
                valid_intersections.append((intersection, "end"))
            elif param < start_param:  # Beyond start point
                valid_intersections.append((intersection, "start"))

        if not valid_intersections:
            return None

        # Use the closest valid intersection
        closest_intersection, extend_direction = min(
            valid_intersections,
            key=lambda x: abs(
                x[0].parameter1 - (0.5 if extend_direction == "end" else 0)
            ),
        )

        # Create extended line
        if extend_direction == "end":
            return Line(line.start_point, closest_intersection[0].point)
        else:
            return Line(closest_intersection[0].point, line.end_point)

    @staticmethod
    def _offset_line(
        line: Line, distance: float, side_point: Point2D
    ) -> Optional[Line]:
        """Create offset line."""
        # Calculate perpendicular vector
        direction = Vector2D(
            line.end_point.x - line.start_point.x, line.end_point.y - line.start_point.y
        )
        perpendicular = Vector2D(-direction.y, direction.x).normalize()

        # Determine side based on pick point
        line_point = Point2D(
            (line.start_point.x + line.end_point.x) / 2,
            (line.start_point.y + line.end_point.y) / 2,
        )

        to_pick = Vector2D(side_point.x - line_point.x, side_point.y - line_point.y)
        side_factor = 1 if perpendicular.dot(to_pick) > 0 else -1

        # Create offset points
        offset_vector = perpendicular * (distance * side_factor)

        offset_start = Point2D(
            line.start_point.x + offset_vector.x, line.start_point.y + offset_vector.y
        )
        offset_end = Point2D(
            line.end_point.x + offset_vector.x, line.end_point.y + offset_vector.y
        )

        return Line(offset_start, offset_end)

    @staticmethod
    def _offset_arc(arc: Arc, distance: float, side_point: Point2D) -> Optional[Arc]:
        """Create offset arc."""
        # Determine if offset should be inward or outward
        mid_angle = (arc.start_angle + arc.end_angle) / 2
        mid_point = Point2D(
            arc.center_point.x + arc.radius * math.cos(mid_angle),
            arc.center_point.y + arc.radius * math.sin(mid_angle),
        )

        # Vector from arc midpoint to pick point
        to_pick = Vector2D(side_point.x - mid_point.x, side_point.y - mid_point.y)
        # Vector from center to arc midpoint
        to_mid = Vector2D(
            mid_point.x - arc.center_point.x, mid_point.y - arc.center_point.y
        ).normalize()

        # Determine side
        outward = to_pick.dot(to_mid) > 0
        new_radius = arc.radius + distance if outward else arc.radius - distance

        if new_radius <= 0:
            return None

        return Arc(arc.center_point, new_radius, arc.start_angle, arc.end_angle)

    @staticmethod
    def _offset_circle(
        circle: Circle, distance: float, side_point: Point2D
    ) -> Optional[Circle]:
        """Create offset circle."""
        # Determine if offset should be inward or outward based on distance from center
        center_distance = GeometryOperations._point_distance(
            side_point, circle.center_point
        )
        outward = center_distance > circle.radius

        new_radius = circle.radius + distance if outward else circle.radius - distance

        if new_radius <= 0:
            return None

        return Circle(circle.center_point, new_radius)

    @staticmethod
    def _calculate_line_fillet(
        line1: Line, line2: Line, intersection: Point2D, radius: float
    ) -> Optional[Tuple[Arc, Line, Line]]:
        """Calculate fillet arc between two lines."""
        # Calculate direction vectors
        dir1 = Vector2D(
            line1.end_point.x - line1.start_point.x,
            line1.end_point.y - line1.start_point.y,
        ).normalize()

        dir2 = Vector2D(
            line2.end_point.x - line2.start_point.x,
            line2.end_point.y - line2.start_point.y,
        ).normalize()

        # Calculate angle between lines
        dot_product = dir1.dot(dir2)
        angle = math.acos(max(-1, min(1, dot_product)))

        if angle < 1e-6 or angle > math.pi - 1e-6:  # Lines are parallel
            return None

        # Calculate fillet center
        half_angle = angle / 2
        center_distance = radius / math.sin(half_angle)

        # Bisector direction
        bisector = (dir1 + dir2).normalize()

        fillet_center = Point2D(
            intersection.x + bisector.x * center_distance,
            intersection.y + bisector.y * center_distance,
        )

        # Calculate tangent points
        tangent_distance = radius / math.tan(half_angle)

        tangent1 = Point2D(
            intersection.x - dir1.x * tangent_distance,
            intersection.y - dir1.y * tangent_distance,
        )

        tangent2 = Point2D(
            intersection.x - dir2.x * tangent_distance,
            intersection.y - dir2.y * tangent_distance,
        )

        # Calculate fillet arc angles
        start_angle = math.atan2(
            tangent1.y - fillet_center.y, tangent1.x - fillet_center.x
        )
        end_angle = math.atan2(
            tangent2.y - fillet_center.y, tangent2.x - fillet_center.x
        )

        # Create fillet arc
        fillet_arc = Arc(fillet_center, radius, start_angle, end_angle)

        # Create trimmed lines
        trimmed_line1 = Line(line1.start_point, tangent1)
        trimmed_line2 = Line(line2.start_point, tangent2)

        return fillet_arc, trimmed_line1, trimmed_line2

    @staticmethod
    def _calculate_line_chamfer(
        line1: Line,
        line2: Line,
        intersection: Point2D,
        distance1: float,
        distance2: float,
    ) -> Optional[Tuple[Line, Line, Line]]:
        """Calculate chamfer line between two lines."""
        # Calculate direction vectors
        dir1 = Vector2D(
            line1.end_point.x - line1.start_point.x,
            line1.end_point.y - line1.start_point.y,
        ).normalize()

        dir2 = Vector2D(
            line2.end_point.x - line2.start_point.x,
            line2.end_point.y - line2.start_point.y,
        ).normalize()

        # Calculate chamfer points
        chamfer_point1 = Point2D(
            intersection.x - dir1.x * distance1, intersection.y - dir1.y * distance1
        )

        chamfer_point2 = Point2D(
            intersection.x - dir2.x * distance2, intersection.y - dir2.y * distance2
        )

        # Create chamfer line
        chamfer_line = Line(chamfer_point1, chamfer_point2)

        # Create trimmed lines
        trimmed_line1 = Line(line1.start_point, chamfer_point1)
        trimmed_line2 = Line(line2.start_point, chamfer_point2)

        return chamfer_line, trimmed_line1, trimmed_line2
