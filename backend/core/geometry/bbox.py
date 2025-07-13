"""
BoundingBox geometry class implementation.

Provides 2D axis-aligned bounding box operations for CAD applications including
containment tests, intersection detection, and geometric operations.
"""

from typing import List, Optional, Tuple, Union

from .point import Point2D


class BoundingBox:
    """
    Represents an axis-aligned 2D bounding box.

    Provides methods for containment tests, intersection detection,
    and geometric operations commonly used in CAD applications.
    """

    def __init__(self, min_point: Point2D, max_point: Point2D) -> None:
        """
        Initialize a bounding box.

        Args:
            min_point: Point with minimum x and y coordinates
            max_point: Point with maximum x and y coordinates

        Raises:
            ValueError: If min_point is not less than max_point in both dimensions
        """
        if min_point.x > max_point.x or min_point.y > max_point.y:
            raise ValueError("min_point must be less than max_point in both dimensions")

        self.min_point = min_point
        self.max_point = max_point

    def __repr__(self) -> str:
        """String representation of the bounding box."""
        return f"BoundingBox({self.min_point!r}, {self.max_point!r})"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"BBox[{self.min_point} → {self.max_point}]"

    def __eq__(self, other: object) -> bool:
        """
        Check equality with another bounding box within tolerance.

        Args:
            other: Another BoundingBox object

        Returns:
            True if bounding boxes are equal within tolerance
        """
        if not isinstance(other, BoundingBox):
            return NotImplemented

        return self.min_point == other.min_point and self.max_point == other.max_point

    def __hash__(self) -> int:
        """Hash function for use in sets and dictionaries."""
        return hash((self.min_point, self.max_point))

    @property
    def width(self) -> float:
        """Get width of bounding box."""
        return self.max_point.x - self.min_point.x

    @property
    def height(self) -> float:
        """Get height of bounding box."""
        return self.max_point.y - self.min_point.y

    @property
    def area(self) -> float:
        """Get area of bounding box."""
        return self.width * self.height

    @property
    def perimeter(self) -> float:
        """Get perimeter of bounding box."""
        return 2 * (self.width + self.height)

    @property
    def center(self) -> Point2D:
        """Get center point of bounding box."""
        return Point2D(
            (self.min_point.x + self.max_point.x) / 2,
            (self.min_point.y + self.max_point.y) / 2,
        )

    @property
    def corners(self) -> List[Point2D]:
        """
        Get all four corner points of bounding box.

        Returns:
            List of corner points [bottom-left, bottom-right, top-right, top-left]
        """
        return [
            Point2D(self.min_point.x, self.min_point.y),  # Bottom-left
            Point2D(self.max_point.x, self.min_point.y),  # Bottom-right
            Point2D(self.max_point.x, self.max_point.y),  # Top-right
            Point2D(self.min_point.x, self.max_point.y),  # Top-left
        ]

    def contains_point(self, point: Point2D, inclusive: bool = True) -> bool:
        """
        Check if point is inside the bounding box.

        Args:
            point: Point to check
            inclusive: Include boundary in containment test

        Returns:
            True if point is inside bounding box
        """
        if inclusive:
            return (
                self.min_point.x <= point.x <= self.max_point.x
                and self.min_point.y <= point.y <= self.max_point.y
            )
        else:
            return (
                self.min_point.x < point.x < self.max_point.x
                and self.min_point.y < point.y < self.max_point.y
            )

    def contains_bbox(self, other: "BoundingBox", inclusive: bool = True) -> bool:
        """
        Check if another bounding box is completely inside this one.

        Args:
            other: Other bounding box
            inclusive: Include boundary in containment test

        Returns:
            True if other bounding box is inside this one
        """
        return self.contains_point(other.min_point, inclusive) and self.contains_point(
            other.max_point, inclusive
        )

    def intersects(self, other: "BoundingBox") -> bool:
        """
        Check if this bounding box intersects with another.

        Args:
            other: Other bounding box

        Returns:
            True if bounding boxes intersect
        """
        return not (
            self.max_point.x < other.min_point.x
            or other.max_point.x < self.min_point.x
            or self.max_point.y < other.min_point.y
            or other.max_point.y < self.min_point.y
        )

    def intersection(self, other: "BoundingBox") -> Optional["BoundingBox"]:
        """
        Calculate intersection with another bounding box.

        Args:
            other: Other bounding box

        Returns:
            Intersection bounding box or None if no intersection
        """
        if not self.intersects(other):
            return None

        min_x = max(self.min_point.x, other.min_point.x)
        min_y = max(self.min_point.y, other.min_point.y)
        max_x = min(self.max_point.x, other.max_point.x)
        max_y = min(self.max_point.y, other.max_point.y)

        return BoundingBox(Point2D(min_x, min_y), Point2D(max_x, max_y))

    def union(self, other: "BoundingBox") -> "BoundingBox":
        """
        Calculate union with another bounding box.

        Args:
            other: Other bounding box

        Returns:
            Union bounding box that contains both boxes
        """
        min_x = min(self.min_point.x, other.min_point.x)
        min_y = min(self.min_point.y, other.min_point.y)
        max_x = max(self.max_point.x, other.max_point.x)
        max_y = max(self.max_point.y, other.max_point.y)

        return BoundingBox(Point2D(min_x, min_y), Point2D(max_x, max_y))

    def expand(self, amount: float) -> "BoundingBox":
        """
        Expand bounding box by given amount in all directions.

        Args:
            amount: Amount to expand (negative to contract)

        Returns:
            New expanded bounding box

        Raises:
            ValueError: If contraction would result in invalid box
        """
        new_min = Point2D(self.min_point.x - amount, self.min_point.y - amount)
        new_max = Point2D(self.max_point.x + amount, self.max_point.y + amount)

        if new_min.x > new_max.x or new_min.y > new_max.y:
            raise ValueError("Contraction amount too large")

        return BoundingBox(new_min, new_max)

    def expand_to_point(self, point: Point2D) -> "BoundingBox":
        """
        Expand bounding box to include a point.

        Args:
            point: Point to include

        Returns:
            New bounding box that includes the point
        """
        min_x = min(self.min_point.x, point.x)
        min_y = min(self.min_point.y, point.y)
        max_x = max(self.max_point.x, point.x)
        max_y = max(self.max_point.y, point.y)

        return BoundingBox(Point2D(min_x, min_y), Point2D(max_x, max_y))

    def expand_to_bbox(self, other: "BoundingBox") -> "BoundingBox":
        """
        Expand bounding box to include another bounding box.

        Args:
            other: Other bounding box to include

        Returns:
            New bounding box that includes both boxes
        """
        return self.union(other)

    def translate(self, dx: float, dy: float) -> "BoundingBox":
        """
        Translate bounding box by given offsets.

        Args:
            dx: X offset
            dy: Y offset

        Returns:
            New translated bounding box
        """
        new_min = self.min_point.translate(dx, dy)
        new_max = self.max_point.translate(dx, dy)
        return BoundingBox(new_min, new_max)

    def scale(
        self, sx: float, sy: float = None, center: Point2D = None
    ) -> "BoundingBox":
        """
        Scale bounding box relative to a center point.

        Args:
            sx: X scale factor
            sy: Y scale factor (uses sx if None)
            center: Center of scaling (bbox center if None)

        Returns:
            New scaled bounding box

        Raises:
            ValueError: If scale factors are negative or zero
        """
        if sx <= 0 or (sy is not None and sy <= 0):
            raise ValueError("Scale factors must be positive")

        if sy is None:
            sy = sx
        if center is None:
            center = self.center

        new_min = self.min_point.scale(sx, sy, center)
        new_max = self.max_point.scale(sx, sy, center)

        # Ensure min/max order is correct after scaling
        min_x = min(new_min.x, new_max.x)
        max_x = max(new_min.x, new_max.x)
        min_y = min(new_min.y, new_max.y)
        max_y = max(new_min.y, new_max.y)

        return BoundingBox(Point2D(min_x, min_y), Point2D(max_x, max_y))

    def distance_to_point(self, point: Point2D) -> float:
        """
        Calculate shortest distance from point to bounding box.

        Args:
            point: Reference point

        Returns:
            Distance to bounding box (0 if point is inside)
        """
        if self.contains_point(point):
            return 0.0

        # Calculate distance to each edge
        dx = 0.0
        dy = 0.0

        if point.x < self.min_point.x:
            dx = self.min_point.x - point.x
        elif point.x > self.max_point.x:
            dx = point.x - self.max_point.x

        if point.y < self.min_point.y:
            dy = self.min_point.y - point.y
        elif point.y > self.max_point.y:
            dy = point.y - self.max_point.y

        return (dx * dx + dy * dy) ** 0.5

    def closest_point_to(self, point: Point2D) -> Point2D:
        """
        Find closest point on or in bounding box to given point.

        Args:
            point: Reference point

        Returns:
            Closest point on/in bounding box
        """
        x = max(self.min_point.x, min(point.x, self.max_point.x))
        y = max(self.min_point.y, min(point.y, self.max_point.y))
        return Point2D(x, y)

    def is_empty(self) -> bool:
        """
        Check if bounding box has zero area.

        Returns:
            True if bounding box is empty (zero width or height)
        """
        return self.width == 0 or self.height == 0

    def is_point(self) -> bool:
        """
        Check if bounding box represents a single point.

        Returns:
            True if min_point equals max_point
        """
        return self.min_point == self.max_point

    def aspect_ratio(self) -> float:
        """
        Calculate aspect ratio (width / height).

        Returns:
            Aspect ratio

        Raises:
            ValueError: If height is zero
        """
        if self.height == 0:
            raise ValueError("Cannot calculate aspect ratio for zero height")
        return self.width / self.height

    def to_tuple(self) -> Tuple[Tuple[float, float], Tuple[float, float]]:
        """
        Convert bounding box to tuple representation.

        Returns:
            ((min_x, min_y), (max_x, max_y))
        """
        return (self.min_point.to_tuple(), self.max_point.to_tuple())

    @classmethod
    def from_tuple(
        cls, coords: Tuple[Tuple[float, float], Tuple[float, float]]
    ) -> "BoundingBox":
        """
        Create bounding box from tuple representation.

        Args:
            coords: ((min_x, min_y), (max_x, max_y))

        Returns:
            New BoundingBox object
        """
        min_point = Point2D.from_tuple(coords[0])
        max_point = Point2D.from_tuple(coords[1])
        return cls(min_point, max_point)

    @classmethod
    def from_points(cls, points: List[Point2D]) -> "BoundingBox":
        """
        Create bounding box that contains all given points.

        Args:
            points: List of points to contain

        Returns:
            Bounding box containing all points

        Raises:
            ValueError: If points list is empty
        """
        if not points:
            raise ValueError("Cannot create bounding box from empty point list")

        min_x = min(point.x for point in points)
        min_y = min(point.y for point in points)
        max_x = max(point.x for point in points)
        max_y = max(point.y for point in points)

        return cls(Point2D(min_x, min_y), Point2D(max_x, max_y))

    @classmethod
    def from_center_and_size(
        cls, center: Point2D, width: float, height: float
    ) -> "BoundingBox":
        """
        Create bounding box from center point and dimensions.

        Args:
            center: Center point
            width: Box width
            height: Box height

        Returns:
            New BoundingBox object

        Raises:
            ValueError: If width or height is negative
        """
        if width < 0 or height < 0:
            raise ValueError("Width and height must be non-negative")

        half_width = width / 2
        half_height = height / 2

        min_point = Point2D(center.x - half_width, center.y - half_height)
        max_point = Point2D(center.x + half_width, center.y + half_height)

        return cls(min_point, max_point)

    @classmethod
    def empty(cls) -> "BoundingBox":
        """
        Create empty bounding box at origin.

        Returns:
            Empty bounding box
        """
        origin = Point2D.origin()
        return cls(origin, origin)
