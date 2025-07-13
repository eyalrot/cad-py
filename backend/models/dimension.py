"""Dimension model for CAD system."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

from .layer import Color


class DimensionType(Enum):
    """Types of dimensions."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"
    ALIGNED = "aligned"
    ANGULAR = "angular"
    RADIUS = "radius"
    DIAMETER = "diameter"
    ARC_LENGTH = "arc_length"
    CONTINUOUS = "continuous"


class UnitFormat(Enum):
    """Unit format for dimension display."""

    DECIMAL = "decimal"
    ARCHITECTURAL = "architectural"
    ENGINEERING = "engineering"
    FRACTIONAL = "fractional"
    SCIENTIFIC = "scientific"


class ArrowType(Enum):
    """Arrow types for dimension lines."""

    CLOSED_FILLED = "closed_filled"
    CLOSED_BLANK = "closed_blank"
    CLOSED_SMALL = "closed_small"
    DOT = "dot"
    TICK = "tick"
    NONE = "none"


@dataclass(frozen=True)
class DimensionPoint:
    """A point used in dimension definition."""

    x: float
    y: float
    z: float = 0.0

    def to_tuple(self) -> Tuple[float, float, float]:
        """Convert to tuple."""
        return (self.x, self.y, self.z)

    def distance_to(self, other: "DimensionPoint") -> float:
        """Calculate distance to another point."""
        dx = self.x - other.x
        dy = self.y - other.y
        dz = self.z - other.z
        return (dx * dx + dy * dy + dz * dz) ** 0.5


class DimensionStyle:
    """Style settings for dimensions."""

    def __init__(self, name: str = "Standard"):
        self.id: str = str(uuid.uuid4())
        self.name: str = name

        # Text properties
        self.text_height: float = 2.5
        self.text_color: Color = Color.BLACK
        self.text_font: str = "Arial"
        self.text_offset: float = 0.625  # Distance from dimension line to text

        # Arrow properties
        self.arrow_type: ArrowType = ArrowType.CLOSED_FILLED
        self.arrow_size: float = 2.5

        # Line properties
        self.line_color: Color = Color.BLACK
        self.line_weight: float = 0.25
        self.extension_line_offset: float = 1.25  # Gap from entity to extension line
        self.extension_line_extension: float = 1.25  # Extension beyond dimension line
        self.dimension_line_gap: float = 0.625  # Gap in dimension line for text

        # Precision and units
        self.precision: int = 4  # Decimal places
        self.unit_format: UnitFormat = UnitFormat.DECIMAL
        self.unit_suffix: str = ""  # e.g., "mm", "in"
        self.scale_factor: float = 1.0
        self.suppress_zeros: bool = True

        # Tolerances
        self.show_tolerances: bool = False
        self.tolerance_upper: float = 0.0
        self.tolerance_lower: float = 0.0

        # Created/modified timestamps
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()

    def format_measurement(self, value: float) -> str:
        """Format a measurement value according to style settings."""
        # Apply scale factor
        scaled_value = value * self.scale_factor

        if self.unit_format == UnitFormat.DECIMAL:
            formatted = f"{scaled_value:.{self.precision}f}"
            if self.suppress_zeros:
                formatted = formatted.rstrip("0").rstrip(".")
        elif self.unit_format == UnitFormat.FRACTIONAL:
            # Convert to fractional representation
            formatted = self._to_fraction(scaled_value)
        elif self.unit_format == UnitFormat.ARCHITECTURAL:
            # Format as feet and inches
            formatted = self._to_architectural(scaled_value)
        elif self.unit_format == UnitFormat.ENGINEERING:
            # Format in engineering notation
            formatted = f"{scaled_value:.{self.precision}e}"
        else:  # SCIENTIFIC
            formatted = f"{scaled_value:.{self.precision}E}"

        # Add unit suffix
        if self.unit_suffix:
            formatted += self.unit_suffix

        return formatted

    def _to_fraction(self, value: float) -> str:
        """Convert decimal to fraction (simplified implementation)."""
        if value == 0:
            return "0"

        # Find the best fraction approximation
        denominator = 2**self.precision  # Use power of 2 for CAD compatibility
        numerator = round(value * denominator)

        # Simplify fraction
        def gcd(a, b):
            while b:
                a, b = b, a % b
            return a

        if numerator != 0:
            common_divisor = gcd(abs(numerator), denominator)
            numerator //= common_divisor
            denominator //= common_divisor

        if denominator == 1:
            return str(numerator)
        else:
            return f"{numerator}/{denominator}"

    def _to_architectural(self, value: float) -> str:
        """Convert to architectural format (feet-inches)."""
        feet = int(value // 12)
        inches = value % 12

        if feet == 0:
            return f'{inches:.{self.precision}f}"'
        elif inches == 0:
            return f"{feet}'"
        else:
            return f"{feet}'-{inches:.{self.precision}f}\""

    def serialize(self) -> Dict[str, Any]:
        """Serialize dimension style to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "text_height": self.text_height,
            "text_color": {
                "red": self.text_color.red,
                "green": self.text_color.green,
                "blue": self.text_color.blue,
                "alpha": self.text_color.alpha,
            },
            "text_font": self.text_font,
            "text_offset": self.text_offset,
            "arrow_type": self.arrow_type.value,
            "arrow_size": self.arrow_size,
            "line_color": {
                "red": self.line_color.red,
                "green": self.line_color.green,
                "blue": self.line_color.blue,
                "alpha": self.line_color.alpha,
            },
            "line_weight": self.line_weight,
            "extension_line_offset": self.extension_line_offset,
            "extension_line_extension": self.extension_line_extension,
            "dimension_line_gap": self.dimension_line_gap,
            "precision": self.precision,
            "unit_format": self.unit_format.value,
            "unit_suffix": self.unit_suffix,
            "scale_factor": self.scale_factor,
            "suppress_zeros": self.suppress_zeros,
            "show_tolerances": self.show_tolerances,
            "tolerance_upper": self.tolerance_upper,
            "tolerance_lower": self.tolerance_lower,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }


class Dimension:
    """Base dimension entity."""

    def __init__(
        self,
        dimension_type: DimensionType,
        points: List[DimensionPoint],
        layer_id: str,
        style: Optional[DimensionStyle] = None,
    ):
        """Initialize dimension.

        Args:
            dimension_type: Type of dimension
            points: Points defining the dimension
            layer_id: ID of layer this dimension belongs to
            style: Dimension style (uses default if None)
        """
        self.id: str = str(uuid.uuid4())
        self.dimension_type: DimensionType = dimension_type
        self.points: List[DimensionPoint] = points.copy()
        self.layer_id: str = layer_id
        self.style: DimensionStyle = style or DimensionStyle()

        # Dimension properties
        self.measurement_value: Optional[float] = None  # Calculated measurement
        self.text_override: Optional[str] = None  # Custom text override
        self.text_position: Optional[DimensionPoint] = None  # Custom text position

        # Entity properties
        self.visible: bool = True
        self.locked: bool = False
        self.selected: bool = False

        # Timestamps
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()

        # Custom properties
        self.properties: Dict[str, Any] = {}

        # Calculate measurement
        self._calculate_measurement()

    def _calculate_measurement(self):
        """Calculate the measurement value based on dimension type and points."""
        if len(self.points) < 2:
            self.measurement_value = 0.0
            return

        if self.dimension_type == DimensionType.HORIZONTAL:
            self.measurement_value = abs(self.points[1].x - self.points[0].x)
        elif self.dimension_type == DimensionType.VERTICAL:
            self.measurement_value = abs(self.points[1].y - self.points[0].y)
        elif self.dimension_type == DimensionType.ALIGNED:
            self.measurement_value = self.points[0].distance_to(self.points[1])
        elif self.dimension_type == DimensionType.RADIUS:
            # For radius, points[0] is center, points[1] is on circumference
            self.measurement_value = self.points[0].distance_to(self.points[1])
        elif self.dimension_type == DimensionType.DIAMETER:
            # For diameter, measurement is twice the radius
            radius = self.points[0].distance_to(self.points[1])
            self.measurement_value = radius * 2.0
        else:
            # For other types, use distance between first two points
            self.measurement_value = self.points[0].distance_to(self.points[1])

    def get_formatted_text(self) -> str:
        """Get the formatted dimension text."""
        if self.text_override:
            return self.text_override

        if self.measurement_value is None:
            return "?"

        return self.style.format_measurement(self.measurement_value)

    def set_text_override(self, text: Optional[str]):
        """Set custom text override."""
        self.text_override = text
        self.modified_at = datetime.utcnow()

    def update_points(self, points: List[DimensionPoint]):
        """Update dimension points and recalculate measurement."""
        self.points = points.copy()
        self._calculate_measurement()
        self.modified_at = datetime.utcnow()

    def set_style(self, style: DimensionStyle):
        """Set dimension style."""
        self.style = style
        self.modified_at = datetime.utcnow()

    def move(self, delta_x: float, delta_y: float, delta_z: float = 0.0):
        """Move dimension by specified offset."""
        new_points = []
        for point in self.points:
            new_points.append(
                DimensionPoint(point.x + delta_x, point.y + delta_y, point.z + delta_z)
            )

        self.points = new_points

        if self.text_position:
            self.text_position = DimensionPoint(
                self.text_position.x + delta_x,
                self.text_position.y + delta_y,
                self.text_position.z + delta_z,
            )

        self.modified_at = datetime.utcnow()

    def get_bounding_box(self) -> Tuple[float, float, float, float]:
        """Get bounding box of dimension (min_x, min_y, max_x, max_y)."""
        if not self.points:
            return (0.0, 0.0, 0.0, 0.0)

        min_x = min(point.x for point in self.points)
        max_x = max(point.x for point in self.points)
        min_y = min(point.y for point in self.points)
        max_y = max(point.y for point in self.points)

        # Expand for text and arrows
        margin = max(self.style.text_height, self.style.arrow_size) * 2

        return (min_x - margin, min_y - margin, max_x + margin, max_y + margin)

    def serialize(self) -> Dict[str, Any]:
        """Serialize dimension to dictionary."""
        return {
            "id": self.id,
            "dimension_type": self.dimension_type.value,
            "points": [point.to_tuple() for point in self.points],
            "layer_id": self.layer_id,
            "style": self.style.serialize(),
            "measurement_value": self.measurement_value,
            "text_override": self.text_override,
            "text_position": self.text_position.to_tuple()
            if self.text_position
            else None,
            "visible": self.visible,
            "locked": self.locked,
            "selected": self.selected,
            "properties": self.properties,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat(),
        }

    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> "Dimension":
        """Deserialize dimension from dictionary."""
        # Reconstruct points
        points = [DimensionPoint(*point_data) for point_data in data["points"]]

        # Reconstruct style
        style_data = data["style"]
        style = DimensionStyle(style_data["name"])
        # Load style properties from style_data...

        # Create dimension
        dimension = cls(
            DimensionType(data["dimension_type"]), points, data["layer_id"], style
        )

        # Set additional properties
        dimension.id = data["id"]
        dimension.measurement_value = data.get("measurement_value")
        dimension.text_override = data.get("text_override")

        if data.get("text_position"):
            dimension.text_position = DimensionPoint(*data["text_position"])

        dimension.visible = data.get("visible", True)
        dimension.locked = data.get("locked", False)
        dimension.selected = data.get("selected", False)
        dimension.properties = data.get("properties", {})
        dimension.created_at = datetime.fromisoformat(data["created_at"])
        dimension.modified_at = datetime.fromisoformat(data["modified_at"])

        return dimension

    def copy(self) -> "Dimension":
        """Create a copy of this dimension."""
        dimension_copy = Dimension(
            self.dimension_type, self.points.copy(), self.layer_id, self.style
        )

        dimension_copy.text_override = self.text_override
        dimension_copy.text_position = self.text_position
        dimension_copy.visible = self.visible
        dimension_copy.locked = self.locked
        dimension_copy.properties = self.properties.copy()

        return dimension_copy

    def __eq__(self, other: object) -> bool:
        """Check equality based on dimension ID."""
        if not isinstance(other, Dimension):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on dimension ID."""
        return hash(self.id)

    def __repr__(self) -> str:
        """String representation of dimension."""
        return f"Dimension(type={self.dimension_type.value}, value={self.measurement_value}, points={len(self.points)})"
