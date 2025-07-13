"""Layer model for CAD system."""

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional, Tuple


class LineType(Enum):
    """Standard CAD line types."""
    
    CONTINUOUS = "continuous"
    DASHED = "dashed"  
    DOTTED = "dotted"
    DASH_DOT = "dash_dot"
    DASH_DOT_DOT = "dash_dot_dot"
    CENTER = "center"
    PHANTOM = "phantom"
    HIDDEN = "hidden"


@dataclass(frozen=True)
class Color:
    """RGB Color representation."""
    
    red: int
    green: int
    blue: int
    alpha: int = 255
    
    def __post_init__(self) -> None:
        """Validate color values."""
        for component in [self.red, self.green, self.blue, self.alpha]:
            if not 0 <= component <= 255:
                raise ValueError(f"Color component must be 0-255, got {component}")
    
    @classmethod
    def from_hex(cls, hex_color: str) -> 'Color':
        """Create color from hex string (#RRGGBB or #RRGGBBAA)."""
        hex_color = hex_color.lstrip('#')
        
        if len(hex_color) == 6:
            return cls(
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16)
            )
        elif len(hex_color) == 8:
            return cls(
                int(hex_color[0:2], 16),
                int(hex_color[2:4], 16),
                int(hex_color[4:6], 16),
                int(hex_color[6:8], 16)
            )
        else:
            raise ValueError(f"Invalid hex color format: {hex_color}")
    
    def to_hex(self, include_alpha: bool = False) -> str:
        """Convert to hex string."""
        if include_alpha:
            return f"#{self.red:02x}{self.green:02x}{self.blue:02x}{self.alpha:02x}"
        return f"#{self.red:02x}{self.green:02x}{self.blue:02x}"
    
    def to_tuple(self) -> Tuple[int, int, int, int]:
        """Convert to RGBA tuple."""
        return (self.red, self.green, self.blue, self.alpha)
    
    @property
    def rgb(self) -> Tuple[int, int, int]:
        """Get RGB tuple without alpha."""
        return (self.red, self.green, self.blue)


class Layer:
    """CAD layer with properties."""
    
    # Standard CAD colors
    BLACK = Color(0, 0, 0)
    WHITE = Color(255, 255, 255)
    RED = Color(255, 0, 0)
    GREEN = Color(0, 255, 0)
    BLUE = Color(0, 0, 255)
    CYAN = Color(0, 255, 255)
    MAGENTA = Color(255, 0, 255)
    YELLOW = Color(255, 255, 0)
    
    def __init__(
        self,
        name: str,
        color: Color = BLACK,
        line_type: LineType = LineType.CONTINUOUS,
        line_weight: float = 0.25
    ) -> None:
        """Initialize layer.
        
        Args:
            name: Layer name (must be unique within document)
            color: Layer color
            line_type: Default line type for entities on this layer
            line_weight: Line weight in mm
        """
        if not name or not isinstance(name, str):
            raise ValueError("Layer name must be a non-empty string")
        
        if line_weight < 0:
            raise ValueError("Line weight must be non-negative")
        
        self.id: str = str(uuid.uuid4())
        self.name: str = name
        self.color: Color = color
        self.line_type: LineType = line_type
        self.line_weight: float = line_weight
        self.visible: bool = True
        self.locked: bool = False
        self.printable: bool = True
        self.frozen: bool = False
        self.created_at: datetime = datetime.utcnow()
        self.modified_at: datetime = datetime.utcnow()
        self.description: str = ""
        self.properties: Dict[str, Any] = {}
    
    def set_color(self, color: Color) -> None:
        """Set layer color."""
        self.color = color
        self.modified_at = datetime.utcnow()
    
    def set_line_type(self, line_type: LineType) -> None:
        """Set layer line type."""
        self.line_type = line_type
        self.modified_at = datetime.utcnow()
    
    def set_line_weight(self, weight: float) -> None:
        """Set layer line weight."""
        if weight < 0:
            raise ValueError("Line weight must be non-negative")
        self.line_weight = weight
        self.modified_at = datetime.utcnow()
    
    def set_visible(self, visible: bool) -> None:
        """Set layer visibility."""
        self.visible = visible
        self.modified_at = datetime.utcnow()
    
    def set_locked(self, locked: bool) -> None:
        """Set layer lock state."""
        self.locked = locked
        self.modified_at = datetime.utcnow()
    
    def set_printable(self, printable: bool) -> None:
        """Set layer printable state."""
        self.printable = printable
        self.modified_at = datetime.utcnow()
    
    def set_frozen(self, frozen: bool) -> None:
        """Set layer frozen state."""
        self.frozen = frozen
        self.modified_at = datetime.utcnow()
    
    def rename(self, new_name: str) -> None:
        """Rename the layer."""
        if not new_name or not isinstance(new_name, str):
            raise ValueError("Layer name must be a non-empty string")
        self.name = new_name
        self.modified_at = datetime.utcnow()
    
    def set_description(self, description: str) -> None:
        """Set layer description."""
        self.description = description
        self.modified_at = datetime.utcnow()
    
    def update_properties(self, **kwargs: Any) -> None:
        """Update layer custom properties."""
        self.properties.update(kwargs)
        self.modified_at = datetime.utcnow()
    
    def is_editable(self) -> bool:
        """Check if layer allows editing."""
        return not (self.locked or self.frozen)
    
    def serialize(self) -> Dict[str, Any]:
        """Serialize layer to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'color': {
                'red': self.color.red,
                'green': self.color.green,
                'blue': self.color.blue,
                'alpha': self.color.alpha
            },
            'line_type': self.line_type.value,
            'line_weight': self.line_weight,
            'visible': self.visible,
            'locked': self.locked,
            'printable': self.printable,
            'frozen': self.frozen,
            'description': self.description,
            'properties': self.properties,
            'created_at': self.created_at.isoformat(),
            'modified_at': self.modified_at.isoformat()
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'Layer':
        """Deserialize layer from dictionary."""
        color_data = data['color']
        color = Color(
            color_data['red'],
            color_data['green'],
            color_data['blue'],
            color_data.get('alpha', 255)
        )
        
        layer = cls(
            name=data['name'],
            color=color,
            line_type=LineType(data['line_type']),
            line_weight=data['line_weight']
        )
        
        layer.id = data['id']
        layer.visible = data.get('visible', True)
        layer.locked = data.get('locked', False)
        layer.printable = data.get('printable', True)
        layer.frozen = data.get('frozen', False)
        layer.description = data.get('description', '')
        layer.properties = data.get('properties', {})
        layer.created_at = datetime.fromisoformat(data['created_at'])
        layer.modified_at = datetime.fromisoformat(data['modified_at'])
        
        return layer
    
    def copy(self, new_name: Optional[str] = None) -> 'Layer':
        """Create a copy of the layer."""
        copy_name = new_name or f"{self.name}_copy"
        layer_copy = Layer(
            name=copy_name,
            color=self.color,
            line_type=self.line_type,
            line_weight=self.line_weight
        )
        
        layer_copy.visible = self.visible
        layer_copy.locked = self.locked
        layer_copy.printable = self.printable
        layer_copy.frozen = self.frozen
        layer_copy.description = self.description
        layer_copy.properties = self.properties.copy()
        
        return layer_copy
    
    def __eq__(self, other: object) -> bool:
        """Check equality based on layer ID."""
        if not isinstance(other, Layer):
            return False
        return self.id == other.id
    
    def __hash__(self) -> int:
        """Hash based on layer ID."""
        return hash(self.id)
    
    def __repr__(self) -> str:
        """String representation of layer."""
        return f"Layer(name='{self.name}', color={self.color.to_hex()}, visible={self.visible})"